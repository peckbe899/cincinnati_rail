"""fp_anatomy.py (diag/swap, 25 Nov 2026): what the false blocks and the missed blocks of a plate-44 run are.
Uses bench44.py's own truth, raster and PQ (imported; nothing is written by it). System python, -B.
For every predicted block (stage 2, the straightened outlines, as bench44's headline PQ) that is not matched (IoU > 0.5)
to one of Ben's blocks, by where its area lies:
  void     more than half on paper Ben did not decide (railway corridor, creek land; bench44's decided ground)
  street   more than half on his street ground
  piece    more than half on one of his blocks (a piece of a block: a split, or a block cut short)
  merge    it holds >= 50% of 2 or more of his blocks (bench44's merges)
  mixed    the rest
and for his blocks: matched / lost in a merge / split / missed otherwise (bench44's breakdown), plus the mean IoU of the
matched ones. Writes diag/swap/fp/<name>.json (per grid and the mean) and prints the mean.
    python -B fp_anatomy.py NAME RUNS44_DIR [NAME RUNS44_DIR ...]     (RUNS44_DIR holds v2__grid0..5 or base__grid0..5)
"""
import json, os, sys, glob
import numpy as np
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
TOOLS = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/tools/sanborn/'
D = SP + 'bench_2026-11-25/diag/swap/'
sys.path.insert(0, TOOLS + 'unet'); sys.path.insert(0, TOOLS)
import bench44 as B  # noqa: E402
B.RUNS = D + 'runs_baseline44/'          # the decided-ground cache is read from here (made by bench44 for this street map)
T = B.load_truth()


def anatomy(run):
    polys = json.load(open(run + 'outlines.json', encoding='utf8'))
    rings = [np.array([s['a'] for s in p], float) for p in polys]; pr = B.raster(rings); npr = len(rings)
    res, ious = B.pq(T, pr, npr)
    gt, ng, dec, alpha2 = T['gt'], T['ng'], T['decided'], T['alpha2']
    void = alpha2 & ~dec; street = dec & (gt == 0)
    cnt = np.bincount(pr.ravel(), minlength=npr + 1)
    v = np.bincount(pr.ravel(), void.ravel().astype(float), minlength=npr + 1); s = np.bincount(pr.ravel(), street.ravel().astype(float), minlength=npr + 1)
    m = pr > 0; joint = np.bincount(gt[m].astype(np.int64) * (npr + 1) + pr[m], minlength=(ng + 1) * (npr + 1)).reshape(ng + 1, npr + 1)
    ga = np.bincount(gt.ravel(), minlength=ng + 1)
    matched = set()
    for i in range(1, ng + 1):
        j = int(np.argmax(joint[i, 1:])) + 1 if npr else 0
        if j and joint[i, j] / max(1, ga[i] + cnt[j] - joint[i, j]) > 0.5: matched.add(j)
    covers = joint[1:, 1:] >= 0.5 * ga[1:, None]; merge = set((np.nonzero(covers.sum(0) >= 2)[0] + 1).tolist())
    kinds = dict(void=0, street=0, piece=0, merge=0, mixed=0); area = dict(void=0, street=0, piece=0, merge=0, mixed=0); items = []
    for j in range(1, npr + 1):
        if cnt[j] == 0 or j in matched: continue
        if j in merge: k = 'merge'
        elif v[j] > 0.5 * cnt[j]: k = 'void'
        elif s[j] > 0.5 * cnt[j]: k = 'street'
        elif joint[1:, j].max() > 0.5 * cnt[j]: k = 'piece'
        else: k = 'mixed'
        kinds[k] += 1; area[k] += int(cnt[j])
        ys, xs = np.nonzero(pr == j)
        items.append(dict(j=j, kind=k, area_half_px=int(cnt[j]), centre_full=[int(xs.mean() * 2), int(ys.mean() * 2)], void=round(v[j] / cnt[j], 3), street=round(s[j] / cnt[j], 3)))
    b = res['all']
    return dict(fp_by_kind=kinds, fp_area_by_kind=area, fp_bench44=b['fp'], matched=b['matched'], merges=b['merges'], gt_lost_in_merges=b['gt_lost_in_merges'], gt_split=b['gt_split'], gt_missed_other=b['gt_missed_other'],
                PQ=b['PQ'], SQ=b['SQ'], pred=b['pred'], items=items)


def main():
    a = sys.argv[1:]
    os.makedirs(D + 'fp', exist_ok=True)
    for name, runs in zip(a[::2], a[1::2]):
        runs = runs.rstrip('/') + '/'; per = {}
        for r in sorted(glob.glob(runs + '*__grid?/')):
            r = r.replace('\\', '/'); per[os.path.basename(r.rstrip('/')).split('__')[1]] = anatomy(r)
        keys = ('fp_bench44', 'matched', 'merges', 'gt_lost_in_merges', 'gt_split', 'gt_missed_other', 'PQ', 'SQ', 'pred')
        mean = {k: round(float(np.mean([p[k] for p in per.values()])), 3) for k in keys}
        mean['fp_by_kind'] = {k: round(float(np.mean([p['fp_by_kind'][k] for p in per.values()])), 2) for k in ('void', 'street', 'piece', 'merge', 'mixed')}
        json.dump(dict(name=name, runs=runs, mean=mean, per_grid=per), open(D + f'fp/{name}.json', 'w'), indent=1)
        print(name, json.dumps(mean), flush=True)


if __name__ == '__main__':
    main()
