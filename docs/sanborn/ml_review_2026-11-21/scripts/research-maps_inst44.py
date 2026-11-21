"""Read-only experiment: outlines.py's watershed with one marker per block seed (instances) instead of a single 'block'
label, so a detected line between two blocks stays a boundary even where no street seed lies between them.
Block seeds are cut by the detected lines (dilated CUT px to close small gaps) before labelling."""
import json, sys, time
import numpy as np, cv2
import ws44 as W
from pq44 import pq
el = W.el

def blocks_inst(pa, lines, cut=3, thr=127, seed_b=W.SEED_B, seed_s=W.SEED_S):
    H, Wd = pa.shape; alpha = W.alpha
    blk = (pa > thr) & alpha; stt = (pa <= thr) & alpha
    mk = np.zeros((H, Wd), np.int32)
    mk[cv2.erode(stt.astype(np.uint8), el(seed_s)) > 0] = 1
    mk[~alpha] = 1
    seed = cv2.erode(blk.astype(np.uint8), el(seed_b)) > 0
    ln = (lines > 127).astype(np.uint8)
    if cut: ln = cv2.dilate(ln, el(cut))
    seed &= ln == 0
    n, cc, st, _ = cv2.connectedComponentsWithStats(seed.astype(np.uint8), connectivity=4)
    ok = st[:, cv2.CC_STAT_AREA] >= 2000; ok[0] = False                 # tiny seed crumbs are left to the watershed
    lab = np.where(ok[cc], cc + 1, 0).astype(np.int32)                   # block instances are 2 .. n+1
    mk[lab > 0] = lab[lab > 0]
    ws = cv2.watershed(cv2.cvtColor(cv2.GaussianBlur(lines, (3, 3), 0), cv2.COLOR_GRAY2BGR), mk)
    ws[~alpha] = 0; ws[ws < 2] = 0
    # per instance: open, drop small
    out = np.zeros_like(ws); k = 0
    ids = np.unique(ws); ids = ids[ids >= 2]
    for i in ids:
        m = (ws == i).astype(np.uint8)
        ys, xs = np.where(m)
        y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
        sub = cv2.morphologyEx(m[y0:y1, x0:x1], cv2.MORPH_OPEN, el(3))
        if sub.sum() < W.MIN_AREA: continue
        k += 1; o = out[y0:y1, x0:x1]; o[sub > 0] = k
    return cv2.resize(out, (W.shape[1], W.shape[0]), interpolation=cv2.INTER_NEAREST), k

if __name__ == '__main__':
    e1, ng1 = W.area('edge_v1'), W.area('area_ng1'); mn = np.minimum(e1, ng1)
    runs = [('G edge_v1 inst cut3', e1, W.pl, 3), ('H min inst cut3', mn, W.pl, 3), ('I area_ng1 inst cut3', ng1, W.pl, 3),
            ('J edge_v1 inst cut6', e1, W.pl, 6), ('K area_ng1 + ink inst cut3', ng1, W.inkdark, 3)]
    sel = sys.argv[1:] or [r[0][0] for r in runs]
    for nm, pa, ln, cut in runs:
        if nm[0] not in sel: continue
        t0 = time.time(); inst, n = blocks_inst(pa, ln, cut=cut); r = pq(W.gt, W.ng, inst, n, nm); r['sec'] = round(time.time() - t0)
        print(json.dumps({k: r[k] for k in ('src', 'pred', 'tp', 'fp', 'fn', 'SQ', 'RQ', 'PQ', 'missed_by_merge', 'missed_by_split', 'sec')}), flush=True)
