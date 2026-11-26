"""Analysis (finder2, 25 Nov 2026): candidate big-letter pieces on the truth v2 crops. A candidate is a connected piece of
the ink left when the LONG line ink (a straight 121 px line fits) is taken out, holding some MID line ink (a 61 px line fits,
a 121 px one does not). For each, shape features and the share of its ink the truth calls text. Development only.

    cd data/sanborn; python -B bench_2026-11-25/text_v1/finder2/scripts/anal_cands.py [T1 ...]"""
import json, os, sys
sys.dont_write_bytecode = True
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__))
TRUTH = os.path.normpath(os.path.join(HERE, '..', '..', 'truth'))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, '..', '..', 'code')))
import finder2 as F

M = 200
crops = json.load(open(os.path.join(TRUTH, 'crops.json')))
ids = sys.argv[1:] or ['T1', 'T2', 'T3', 'T4', 'T6', 'T7']
rows = []
for tid in ids:
    c = crops[tid]; x0, y0, x1, y1 = c['win']
    im, ink, paper, _ = F.load(c['plate'], (x0 - M, y0 - M, x1 + M, y1 + M))
    line, ori = F.line_ink(ink)
    fat = cv2.dilate(ink, np.ones((3, 3), np.uint8)); lng = np.zeros_like(ink)
    for i in range(F.P['angles']): lng |= cv2.morphologyEx(fat, cv2.MORPH_OPEN, F.line_kernel(121, np.pi * i / F.P['angles'])) & ink
    lng &= line; mid = (line > 0) & (lng == 0)
    Q = (ink & ~(cv2.dilate(lng, np.ones((3, 3), np.uint8)) > 0)).astype(np.uint8)
    n, lb, st, _ = cv2.connectedComponentsWithStats(Q, connectivity=8)
    midc = np.bincount(lb[mid & (Q > 0)], minlength=n)
    tr = np.zeros(ink.shape, np.uint8); tr[M:M + y1 - y0, M:M + x1 - x0] = cv2.imread(os.path.join(TRUTH, f'{tid}_mask.png'), 0) + 10
    tt = np.bincount(lb[tr == 12], minlength=n); tn = np.bincount(lb[tr == 11], minlength=n)
    dt = cv2.distanceTransform(Q, cv2.DIST_L2, 3); ridge = (dt > 0) & (dt >= cv2.dilate(dt, np.ones((3, 3), np.uint8)))
    near_long = cv2.dilate(lng, np.ones((5, 5), np.uint8)) > 0
    for j in np.nonzero(midc >= 30)[0]:
        if j == 0 or tt[j] + tn[j] < 30: continue
        bx, by, bw, bh, A = st[j]
        sub = (lb[by:by + bh, bx:bx + bw] == j).astype(np.uint8)
        cs, _ = cv2.findContours(np.pad(sub, 2), cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
        outer = max(cs, key=cv2.contourArea); (cx, cy), (rw, rh), _ = cv2.minAreaRect(outer)
        hull = cv2.contourArea(cv2.convexHull(outer)); ca = cv2.contourArea(outer)
        r = ridge[by:by + bh, bx:bx + bw] & (sub > 0); sw = 2 * np.median(dt[by:by + bh, bx:bx + bw][r]) if r.any() else 0
        rows.append(dict(tid=tid, x=int(bx + x0 - M), y=int(by + y0 - M), w=int(bw), h=int(bh), A=int(A), mid=int(midc[j]),
                         ext=round(max(rw, rh), 1), short=round(min(rw, rh), 1), sw=round(float(sw), 2), hole=round(1 - A / max(1, ca), 3),
                         solid=round(A / max(1, hull), 3), rect=round(ca / max(1, rw * rh), 3),
                         touch_long=int((near_long[by:by + bh, bx:bx + bw] & (sub > 0)).sum()),
                         text=round(tt[j] / (tt[j] + tn[j]), 3), tpx=int(tt[j]), npx=int(tn[j])))
json.dump(rows, open(os.path.join(HERE, '..', 'out', 'anal_cands.json'), 'w'), indent=0)
rows.sort(key=lambda r: -r['tpx'] - r['npx'])
print(len(rows), 'candidates; text px', sum(r['tpx'] for r in rows), 'non-text px', sum(r['npx'] for r in rows))
for r in rows[:150]:
    print(f"{r['tid']} ({r['x']},{r['y']}) {r['w']}x{r['h']} A {r['A']} mid {r['mid']} ext {r['ext']} short {r['short']} sw {r['sw']} hole {r['hole']} solid {r['solid']} rect {r['rect']} tl {r['touch_long']} | text {r['text']} ({r['tpx']}/{r['npx']})")
