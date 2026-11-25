"""Where are the extra false blocks on 44? For grid0 of baseline, V1S2 and V2S2: the outline step's blocks
(44_blockinst.png) over the scan: green = IoU > 0.5 with one of Ben's blocks; blue = touches 2+ of Ben's blocks (a
merge); red = other block mostly in Ben's decided ground; orange = other block mostly outside it (void in PQ_decided,
counted in PQ). Ben's blocks outlined white; undecided ground darkened. Writes pics/fp44_<step>.jpg and a count.
Reads only; system python."""
import json, glob, os, numpy as np, cv2
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; EV = SP + 'train_v2_runs/eval/'; OUT = SP + 'bench_2026-11-25/diag/recipe/'
BR = SP + 'bench_2026-11-23/train/integrate/round2/driver_mini/eval/runs_baseline44/'
dec = cv2.imread(glob.glob(BR + 'cache/decided_half_*.png')[0], 0) > 0; h, w = dec.shape
T = json.load(open(SP + 'streetmap/22-44.json', encoding='utf8')); gt = np.zeros((h, w), np.int32)
for i, b in enumerate(T['blocks']): cv2.fillPoly(gt, [(np.array(b['ring']) / 2).round().astype(np.int32)], i + 1)
img = cv2.resize(cv2.imread(SP + 'cufp/22-44.jpg'), (w, h), interpolation=cv2.INTER_AREA)
res = {}
for s in ['baseline', 'V1S2', 'V2S2', 'V1S1']:
    rd = BR + 'base__grid0/' if s == 'baseline' else EV + f'{s}/runs44/v2__grid0/'
    inst = cv2.imread(rd + '44_blockinst.png', cv2.IMREAD_UNCHANGED).astype(np.int32)
    if inst.shape != (h, w): inst = cv2.resize(inst, (w, h), interpolation=cv2.INTER_NEAREST)
    c = img.copy(); c[~dec] = (c[~dec] * 0.45).astype(np.uint8); col = np.zeros_like(c); cnt = dict(match=0, merge=0, fp_decided=0, fp_outside=0, fp_outside_area_px=0)
    for k in range(1, inst.max() + 1):
        m = inst == k; a = int(m.sum())
        if not a: continue
        g = gt[m]; ids, n = np.unique(g[g > 0], return_counts=True); big = [i for i, nn in zip(ids, n) if nn > 0.2 * (gt == i).sum()]
        best = 0.0
        for i, nn in zip(ids, n): best = max(best, nn / (a + (gt == i).sum() - nn))
        if best > 0.5: kind, cc = 'match', (60, 200, 60)
        elif len(big) >= 2: kind, cc = 'merge', (220, 120, 0)
        elif dec[m].mean() >= 0.5: kind, cc = 'fp_decided', (40, 40, 230)
        else: kind, cc = 'fp_outside', (0, 160, 255); cnt['fp_outside_area_px'] += a
        cnt[kind] += 1; col[m] = cc
    o = (c * 0.5 + col * 0.5).astype(np.uint8); o[col.sum(2) == 0] = c[col.sum(2) == 0]
    for b in T['blocks']: cv2.polylines(o, [(np.array(b['ring']) / 2).round().astype(np.int32)], True, (255, 255, 255), 2)
    cv2.imwrite(OUT + f'pics/fp44_{s}.jpg', cv2.resize(o, None, fx=0.3, fy=0.3, interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 85])
    res[s] = cnt; print(s, cnt, flush=True)
json.dump(res, open(OUT + 'fp44_grid0.json', 'w'), indent=1)
