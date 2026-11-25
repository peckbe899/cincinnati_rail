"""errors census, stage 1 (25 Nov 2026): per pair and tile grid on plate 44, read the existing eval outputs
(train_v2_runs/eval/STEP/runs44/v2__gridG/) and recompute, sample by sample, what bench44.py scores:
  shown lines (44_shown.json minus the sheet outline) sampled each 1 px, distance to Ben's lines (5 px, 20 deg);
  Ben's lines, distance to the shown lines;
  blocks (outlines.json rasterised as bench44 does), COCO PQ with the list of false blocks and merges.
Reads only; writes into this folder (runs/STEP_gG.npz, runs/STEP_gG.json, b44cache/).
    python -B collect.py            (system python: cv2, numpy, scipy, shapely)
"""
import json, os, shutil, sys, time
import numpy as np, cv2

HERE = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/') + '/'
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
TOOLS = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/tools/sanborn/unet/'
EV = SP + 'train_v2_runs/eval/'
STEPS = ['baseline', 'V1S1', 'V2S1', 'V1S2', 'V2S2']
sys.path.insert(0, TOOLS); sys.path.insert(0, TOOLS + '..')
sys.dont_write_bytecode = True
import bench44 as B  # noqa: E402  (read-only use: its sampling, distance and raster code)

# the decided-ground cache: copy it here so bench44 never writes anywhere else
B.RUNS = HERE + 'b44cache/'
os.makedirs(B.RUNS + 'cache', exist_ok=True)
src = EV + 'baseline/runs44/cache/'
for f in os.listdir(src):
    if not os.path.exists(B.RUNS + 'cache/' + f): shutil.copy(src + f, B.RUNS + 'cache/' + f)


def pq_detail(T, pr, npr):
    """bench44.pq (no void), returning the false blocks, merges and matches too"""
    gt, ng = T['gt'], T['ng']; g = gt.astype(np.int64)
    m = (g > 0) | (pr > 0)
    joint = np.bincount(g[m] * (npr + 1) + pr[m], minlength=(ng + 1) * (npr + 1)).reshape(ng + 1, npr + 1)
    ga = joint.sum(1); pa = joint.sum(0)
    cnt = np.bincount(pr.ravel(), minlength=npr + 1)
    tp = {}; best = np.zeros(ng + 1, int)
    for i in range(1, ng + 1):
        if npr == 0: continue
        j = int(np.argmax(joint[i, 1:])) + 1; best[i] = j; inter = joint[i, j]
        iou = inter / max(1, ga[i] + pa[j] - inter)
        if iou > 0.5: tp[i] = (j, float(iou))
    matched_p = {j for j, _ in tp.values()}
    covers = (joint[1:ng + 1, 1:] >= 0.5 * ga[1:ng + 1, None])
    merge_p = (np.nonzero(covers.sum(0) >= 2)[0] + 1).tolist()
    fp_p = [j for j in range(1, npr + 1) if j not in matched_p and cnt[j] > 0]
    sq = float(np.mean([v[1] for v in tp.values()])) if tp else 0.0
    rq = len(tp) / max(1e-9, len(tp) + 0.5 * len(fp_p) + 0.5 * (ng - len(tp)))
    merged_gt = {int(j): [int(i) for i in (np.nonzero(covers[:, j - 1])[0] + 1)] for j in merge_p}
    return dict(PQ=round(sq * rq, 4), matched=len(tp), fp=len(fp_p), merges=len(merge_p), fp_p=fp_p, merge_p=merge_p, merged_gt=merged_gt,
                tp={int(i): [int(j), round(v, 4)] for i, (j, v) in tp.items()}, best=best.tolist(), pa=pa.tolist(), cnt=cnt.tolist(),
                joint_gt_share=[(joint[1:, j].sum() / max(1, pa[j])) for j in range(npr + 1)])


def one(step, g, T, ben):
    run = EV + f'{step}/runs44/v2__grid{g}/'
    out = HERE + f'runs/{step}_g{g}'
    shown_all = json.load(open(run + '44_shown.json', encoding='utf8'))
    shown = [e for e in shown_all if e.get('state') != 'sheet']
    ls = B.LineSet([(e['a'], e['b'], e['state']) for e in shown], 20.0)
    dp = ls.dist_to(ben); db = ben.dist_to(ls)
    polys = json.load(open(run + 'outlines.json', encoding='utf8'))
    rings = [np.array([s['a'] for s in p], float) for p in polys]
    pr = B.raster(rings); npr = len(rings)
    d = pq_detail(T, pr, npr)
    interior = np.isin(ben.lab, ('printed', 'drawn'))
    prec = float((dp <= 5).mean()); rec = float((db[interior] <= 5).mean())
    ref = json.load(open(run + 'bench44.json'))['headline']['all']
    chk = dict(precision=[round(prec, 4), ref['precision']], recall_interior=[round(rec, 4), ref['recall_interior']], PQ=[d['PQ'], ref['PQ']], fp=[d['fp'], ref['fp']],
               merges=[d['merges'], ref['merges']], matched=[d['matched'], ref['matched']])
    np.savez_compressed(out + '.npz', P=ls.P.astype(np.float32), Pd=ls.Pd.astype(np.float32), ix=ls.ix.astype(np.int32), dp=dp.astype(np.float32), db=db.astype(np.float32),
                        state=np.array([e['state'] for e in shown]), a=np.array([e['a'] for e in shown], np.float32), b=np.array([e['b'] for e in shown], np.float32))
    cv2.imwrite(out + '_inst.png', pr.astype(np.uint16))
    json.dump(dict(step=step, grid=g, run=run, check=chk, blocks=d, npolys=npr, hole=[bool(p and p[0].get('hole')) for p in polys]), open(out + '.json', 'w'), indent=0)
    return step, g, chk


def main():
    os.makedirs(HERE + 'runs', exist_ok=True)
    t0 = time.time(); T = B.load_truth(); ben = B.LineSet(T['lines'], 20.0)
    np.savez_compressed(HERE + 'runs/ben.npz', P=ben.P.astype(np.float32), Pd=ben.Pd.astype(np.float32), ix=ben.ix.astype(np.int32), lab=ben.lab)
    cv2.imwrite(HERE + 'runs/gt_half.png', T['gt'].astype(np.uint16)); cv2.imwrite(HERE + 'runs/decided_half.png', T['decided'].astype(np.uint8) * 255)
    print('truth', round(time.time() - t0, 1), 's', flush=True)
    bad = []
    for step in STEPS:
        for g in range(6):
            s, g_, chk = one(step, g, T, ben)
            ok = all(abs(v[0] - v[1]) < 2e-4 for v in chk.values())
            if not ok: bad.append((s, g_, chk))
            print(s, g_, 'ok' if ok else 'MISMATCH', chk, round(time.time() - t0, 1), flush=True)
    print('mismatches:', bad)


if __name__ == '__main__':
    main()
