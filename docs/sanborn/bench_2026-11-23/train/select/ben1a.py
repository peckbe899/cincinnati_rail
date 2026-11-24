"""Selection agent (23 Nov 2026): how good would a pseudo label have been on plate 1A, now that Ben has checked it?

    python -B ben1a.py        (system Python; read-only on the repo)  -> ben1a.json, ben1a.jpg in this folder

1A was never trained on (area_ng1 / lines_ng1 saw 82A, 80, 43, 45), so it is an out-of-sample look at the networks'
own guesses on a 100-ft, heavily tinted plate. Plate 44 is not used here.
Ben's blocks: the faces of his lines as street_map.py makes them (street_map.editor_lines + polygonize, tol 1.5 px,
faces under 400 px dropped), computed in memory; nothing is written to streetmap/.
Compared at half size, on the paper:
- area_ng1's confident pixels (p <= 0.05 street, p >= 0.95 block): share and accuracy against Ben's blocks;
- the merged step's blocks (unet_data/1A_blockmask.png) and instances (picks22_guided/22-1A/outlines.json): pixel
  accuracy and a PQ (IoU > 0.5) against Ben's blocks;
- Ben's street ground that the confident pixels call block (what a pseudo label would teach wrongly: the merges).
Also by the right-hand quarter (x >= 0.75 W, the planned validation area) and the rest.
"""
import json, os, sys
import numpy as np
import cv2
from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union, polygonize_full

REPO = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/'
SP = REPO + 'data/sanborn/'; U = SP + 'unet_data/'
sys.path.insert(0, REPO + 'tools/sanborn/unet'); sys.path.insert(0, REPO + 'tools/sanborn')
import street_map as sm  # noqa: E402  (imports edit_server's functions; starts no server)
OUT = os.path.dirname(os.path.abspath(__file__)); N = '1A'; TOL = 1.5


def ben_blocks():
    B = json.load(open(SP + f'picks22_guided/22-{N}/edges_ben.json', encoding='utf8'))
    im = cv2.imread(SP + f'cufp/22-{N}.jpg'); H, W = im.shape[:2]
    L, SH = sm.editor_lines(N, W, H, json.load(open(U + f'{N}_edges.json', encoding='utf8')), B)
    def ext(l):
        a, b = np.array(l['a'], float), np.array(l['b'], float); d = (b - a) / np.hypot(*(b - a)); return LineString([a - d * TOL, b + d * TOL])
    P = [p for p in polygonize_full(unary_union([ext(l) for l in L]))[0].geoms if p.area >= 400]
    return P, L, W, H, B.get('saved_at'), im


def raster(polys, W, H, s=0.5):
    m = np.zeros((int(H * s), int(W * s)), np.int32)
    for i, p in enumerate(polys, 1):
        cv2.fillPoly(m, [(np.array(p.exterior.coords) * s).round().astype(np.int32)], i)
        for r in p.interiors: cv2.fillPoly(m, [(np.array(r.coords) * s).round().astype(np.int32)], 0)
    return m


def pq(gt, pr):
    g_ids = [i for i in np.unique(gt) if i]; p_ids = [i for i in np.unique(pr) if i]
    tp, ious = 0, []; matched_p = set()
    for g in g_ids:
        gm = gt == g; cand, cnt = np.unique(pr[gm], return_counts=True)
        for c, n in zip(cand, cnt):
            if c == 0: continue
            inter = n; union = gm.sum() + (pr == c).sum() - inter; iou = inter / union
            if iou > 0.5: tp += 1; ious.append(iou); matched_p.add(c); break
    fp = len(p_ids) - len(matched_p); fn = len(g_ids) - tp
    return dict(gt=len(g_ids), pred=len(p_ids), tp=tp, fp=fp, fn=fn, pq=round(sum(ious) / max(1, tp + 0.5 * fp + 0.5 * fn), 3))


def main():
    P, L, W, H, saved, im = ben_blocks()
    gt = raster(P, W, H); hh, hw = gt.shape
    a4 = np.load(SP + f'cufp/{N}/png_alpha_s4.npy').astype(np.uint8)
    paper = cv2.resize(a4, (hw, hh), interpolation=cv2.INTER_NEAREST) > 0
    pa = cv2.imread(U + f'{N}_pred_area_ng1.png', 0); assert pa.shape == gt.shape, (pa.shape, gt.shape)
    bm = cv2.imread(U + f'{N}_blockmask.png', 0) > 127
    polys = json.load(open(SP + f'picks22_guided/22-{N}/outlines.json', encoding='utf8'))
    inst = np.zeros(gt.shape, np.int32); k = 0
    for poly in polys:
        if poly[0].get('hole'): continue
        k += 1; pts = np.array([s['a'] for s in poly], float) * 0.5
        cv2.fillPoly(inst, [pts.round().astype(np.int32)], k)
    for poly in polys:
        if poly[0].get('hole'): cv2.fillPoly(inst, [(np.array([s['a'] for s in poly], float) * 0.5).round().astype(np.int32)], 0)
    benb = gt > 0
    xs = np.arange(hw)[None, :].repeat(hh, 0); val = xs >= int(hw * 0.75)
    res = dict(plate=N, edges_ben_saved_at=saved, ben_lines=len(L), ben_blocks=len(P), half_size=[hw, hh])
    for name, reg in (('whole', paper), ('val_quarter', paper & val), ('train_3_4', paper & ~val)):
        n = int(reg.sum()); p = pa[reg]; b = benb[reg]
        cb, cs = p >= 243, p <= 12; conf = cb | cs
        r = dict(paper_half_px=n, ben_block_share=round(float(b.mean()), 3),
                 area_conf_share=round(float(conf.mean()), 3),
                 area_conf_accuracy=round(float(((cb & b) | (cs & ~b)).sum() / max(1, conf.sum())), 4),
                 area_unsure_accuracy_at_0_5=round(float((((p >= 128) & b) | ((p < 128) & ~b))[~conf].mean()), 4),
                 ben_street_called_conf_block=round(float((cb & ~b).sum() / max(1, (~b).sum())), 4),
                 ben_street_conf_street=round(float((cs & ~b).sum() / max(1, (~b).sum())), 4),
                 ben_block_conf_block=round(float((cb & b).sum() / max(1, b.sum())), 4),
                 merged_mask_accuracy=round(float((bm[reg] == b).mean()), 4),
                 merged_street_called_block=round(float((bm[reg] & ~b).sum() / max(1, (~b).sum())), 4))
        res[name] = r
    gtp = np.where(paper, gt, 0); inp = np.where(paper, inst, 0)
    res['pq_merged_vs_ben_whole'] = pq(gtp, inp)
    # the validation quarter: blocks whose centroid lies there
    vg = gtp.copy(); vi = inp.copy()
    for i in np.unique(gtp):
        if i and np.mean(np.nonzero(gtp == i)[1]) < hw * 0.75: vg[gtp == i] = 0
    for i in np.unique(inp):
        if i and np.mean(np.nonzero(inp == i)[1]) < hw * 0.75: vi[inp == i] = 0
    res['pq_merged_vs_ben_val_quarter'] = pq(vg, vi)
    json.dump(res, open(os.path.join(OUT, 'ben1a.json'), 'w', encoding='utf8', newline='\n'), indent=1)
    print(json.dumps(res, indent=1))
    # picture: half size scan, Ben's blocks tinted green, confident-block-on-Ben-street in red, merged outlines in blue
    small = cv2.resize(im, (hw, hh), interpolation=cv2.INTER_AREA); vis = (small * 0.6 + 90).astype(np.uint8)
    vis[benb] = (vis[benb] * 0.6 + np.array([40, 160, 40]) * 0.4).astype(np.uint8)
    bad = (pa >= 243) & ~benb & paper; vis[bad] = (0, 0, 230)
    for poly in polys:
        pts = (np.array([s['a'] for s in poly], float) * 0.5).round().astype(np.int32); cv2.polylines(vis, [pts], True, (230, 80, 0), 2)
    cv2.line(vis, (int(hw * 0.75), 0), (int(hw * 0.75), hh), (0, 200, 255), 3)
    cv2.imwrite(os.path.join(OUT, 'ben1a.jpg'), cv2.resize(vis, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 85])


if __name__ == "__main__" and "--split" not in sys.argv:
    main()


def split_errors():
    """the confident-block pixels on ground Ben did not close into a block, split into connected pieces: a big piece is
    ground Ben left unclosed (not a street), a thin one is an alley or street the network fills in"""
    P, L, W, H, saved, im = ben_blocks(); gt = raster(P, W, H); hh, hw = gt.shape
    a4 = np.load(SP + f'cufp/{N}/png_alpha_s4.npy').astype(np.uint8); paper = cv2.resize(a4, (hw, hh), interpolation=cv2.INTER_NEAREST) > 0
    pa = cv2.imread(U + f'{N}_pred_area_ng1.png', 0); benb = gt > 0
    bad = ((pa >= 243) & ~benb & paper).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(bad, connectivity=8)
    sizes = sorted([int(s) for s in st[1:, cv2.CC_STAT_AREA]], reverse=True)
    big = [i for i in range(1, n) if st[i, cv2.CC_STAT_AREA] >= 50000]
    keep = paper & ~np.isin(lab, big)
    cb, cs = (pa >= 243) & keep, (pa <= 12) & keep; conf = cb | cs
    out = dict(pieces=len(sizes), largest=sizes[:6], big_unclosed_px=int(sum(st[i, cv2.CC_STAT_AREA] for i in big)),
               without_big_pieces=dict(area_conf_share=round(float(conf.sum() / keep.sum()), 3), area_conf_accuracy=round(float(((cb & benb) | (cs & ~benb)).sum() / conf.sum()), 4),
                                       ben_street_called_conf_block=round(float((cb & ~benb).sum() / max(1, (keep & ~benb).sum())), 4)))
    print(json.dumps(out, indent=1)); return out


if __name__ == '__main__' and '--split' in sys.argv:
    r = json.load(open(os.path.join(OUT, 'ben1a.json'), encoding='utf8')); r['split_errors'] = split_errors()
    json.dump(r, open(os.path.join(OUT, 'ben1a.json'), 'w', encoding='utf8', newline='\n'), indent=1)
