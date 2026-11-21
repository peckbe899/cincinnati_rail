"""Feasibility check of M1 (instance markers), read-only.
(a) Are 'false positives' of the instance variant fragments of a split block (a split that the missed_by_split counter
    cannot see because the bigger piece still matches at IoU > 0.5)?
(b) If only outlines.py:39-43 is replaced and the rest (binary block mask, MORPH_OPEN, 4-conn components, findContours
    RETR_EXTERNAL) is kept, do neighbouring instances join up again across the 1-px watershed line?"""
import json, sys, time
import numpy as np, cv2
import ws44 as W
from pq44 import pq
el = W.el

def ws_inst(pa, lines, cut=3, thr=127):
    H, Wd = pa.shape; alpha = W.alpha
    blk = (pa > thr) & alpha; stt = (pa <= thr) & alpha
    mk = np.zeros((H, Wd), np.int32)
    mk[cv2.erode(stt.astype(np.uint8), el(W.SEED_S)) > 0] = 1
    mk[~alpha] = 1
    seed = cv2.erode(blk.astype(np.uint8), el(W.SEED_B)) > 0
    ln = (lines > 127).astype(np.uint8)
    if cut: ln = cv2.dilate(ln, el(cut))
    seed &= ln == 0
    n, cc, st, _ = cv2.connectedComponentsWithStats(seed.astype(np.uint8), connectivity=4)
    ok = st[:, cv2.CC_STAT_AREA] >= 2000; ok[0] = False
    lab = np.where(ok[cc], cc + 1, 0).astype(np.int32)
    mk[lab > 0] = lab[lab > 0]
    ws = cv2.watershed(cv2.cvtColor(cv2.GaussianBlur(lines, (3, 3), 0), cv2.COLOR_GRAY2BGR), mk)
    ws[~alpha] = 0; ws[ws < 2] = 0
    return ws

def per_instance(ws):
    out = np.zeros_like(ws); k = 0
    for i in np.unique(ws):
        if i < 2: continue
        m = (ws == i).astype(np.uint8); ys, xs = np.where(m)
        y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
        sub = cv2.morphologyEx(m[y0:y1, x0:x1], cv2.MORPH_OPEN, el(3))
        if sub.sum() < W.MIN_AREA: continue
        k += 1; o = out[y0:y1, x0:x1]; o[sub > 0] = k
    return out, k

def downstream_unchanged(ws):
    """outlines.py:43-47 and :92 applied to the union of the instances"""
    block = ((ws >= 2) & W.alpha).astype(np.uint8)
    block = cv2.morphologyEx(block, cv2.MORPH_OPEN, el(3))
    n, cc, st, _ = cv2.connectedComponentsWithStats(block, connectivity=4)
    for i in range(1, n):
        if st[i, cv2.CC_STAT_AREA] < W.MIN_AREA: block[cc == i] = 0
    cs, _ = cv2.findContours(block, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    inst = np.zeros(block.shape, np.int32)
    for k, c in enumerate(cs, 1): cv2.drawContours(inst, [c], -1, k, -1)
    n4, cc4 = cv2.connectedComponents(block, connectivity=4)
    return inst, len(cs), cc4, n4 - 1

def half(x): return cv2.resize(x, (W.shape[1], W.shape[0]), interpolation=cv2.INTER_NEAREST)

def fp_analysis(gt, ng, pr, npr):
    m = (gt > 0) | (pr > 0)
    joint = np.bincount(gt[m].astype(np.int64) * (npr + 1) + pr[m], minlength=(ng + 1) * (npr + 1)).reshape(ng + 1, npr + 1)
    ga, pa = joint.sum(1), joint.sum(0)
    matched = {}
    for i in range(1, ng + 1):
        j = int(np.argmax(joint[i, 1:])) + 1; inter = joint[i, j]
        if inter / (ga[i] + pa[j] - inter) > 0.5: matched[j] = i
    res = dict(fp=0, fp_mostly_off_ben_blocks=0, fp_fragment_of_matched_block=0, fp_fragment_of_unmatched_block=0, fp_spans_several=0)
    frag_px = []
    for j in range(1, npr + 1):
        if j in matched: continue
        res['fp'] += 1
        inside = joint[1:, j].sum() / max(1, pa[j])
        if inside < 0.5: res['fp_mostly_off_ben_blocks'] += 1; continue
        i = int(np.argmax(joint[1:, j])) + 1
        if joint[i, j] < 0.8 * joint[1:, j].sum(): res['fp_spans_several'] += 1; continue
        if i in matched.values(): res['fp_fragment_of_matched_block'] += 1; frag_px.append(round(float(joint[i, j] / ga[i]), 3))
        else: res['fp_fragment_of_unmatched_block'] += 1
    res['fragment_share_of_its_block'] = sorted(frag_px)
    return res

if __name__ == '__main__':
    e1, ng1 = W.area('edge_v1'), W.area('area_ng1'); mn = np.minimum(e1, ng1)
    extra = {}
    if len(sys.argv) > 1 and sys.argv[1] == 'ng1lines':
        pl_ng = cv2.imread(sys.argv[2], 0); extra = {'L area_ng1 + lines_ng1 single': (ng1, pl_ng, 'single'), 'M area_ng1 + lines_ng1 inst cut3': (ng1, pl_ng, 'inst'),
                                                       'N min + lines_ng1 inst cut3': (mn, pl_ng, 'inst')}
        runs = extra
    else:
        runs = {'G edge_v1 inst cut3': (e1, W.pl, 'inst'), 'H min inst cut3': (mn, W.pl, 'inst'), 'I area_ng1 inst cut3': (ng1, W.pl, 'inst'),
                'A edge_v1 single': (e1, W.pl, 'single'), 'B area_ng1 single': (ng1, W.pl, 'single')}
    for nm, (pa, ln, how) in runs.items():
        t0 = time.time()
        if how == 'single':
            inst, n = W.blocks(pa, ln); r = pq(W.gt, W.ng, inst, n, nm); r.update(fp_analysis(W.gt, W.ng, inst, n)); r['sec'] = round(time.time() - t0)
            print(json.dumps(r), flush=True); continue
        ws = ws_inst(pa, ln)
        a, ka = per_instance(ws); ra = pq(W.gt, W.ng, half(a), ka, nm + ' [per-instance, as inst44]'); ra.update(fp_analysis(W.gt, W.ng, half(a), ka))
        print(json.dumps(ra), flush=True)
        b, kb, c4, k4 = downstream_unchanged(ws)
        rb = pq(W.gt, W.ng, half(b), kb, nm + ' [union -> outlines.py:44-47 + findContours RETR_EXTERNAL]')
        rc = pq(W.gt, W.ng, half(c4.astype(np.int32)), k4, nm + ' [union -> 4-conn components]')
        print(json.dumps(rb), flush=True); print(json.dumps(rc), flush=True)
        print('sec', round(time.time() - t0), flush=True)
