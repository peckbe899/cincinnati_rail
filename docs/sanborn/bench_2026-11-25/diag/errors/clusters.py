"""errors census: the biggest NEW errors on grid 0 (the batch grid), pooled over the four pairs.
Error samples = new false (the pair's false shown line samples far from the baseline's false ones) + lost (Ben's samples
the baseline found and the pair did not). All four pairs go into one 1/8-size raster, dilated 24 px, 8-connected pieces.
A piece's size = mean over the 4 pairs of its error length (px). For the 10 biggest a full-size crop (the 1400 x 1000 px
window holding most of its error samples) is written for the pair with the most error there:
  pics/err_K.jpg   top: the scan at full size with the pair's lines: red = new false, orange = other shown, magenta =
                   lost Ben line, blue = Ben's line (thin), green = baseline's shown line (thin, offset 0)
                   bottom: P(line) of the baseline | P(line) of the pair (half size)
    python -B clusters.py -> clusters.json, pics/err_*.jpg
"""
import json, os
import numpy as np, cv2
HERE = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-25/diag/errors/'
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
EV = SP + 'train_v2_runs/eval/'
PAIRS = ['V1S1', 'V2S1', 'V1S2', 'V2S2']
W, H = 10768, 7219; F = 8; g = 0
ben = dict(np.load(HERE + 'runs/ben.npz')); bins = cv2.imread(SP + 'unet_data/44_bins.png', cv2.IMREAD_UNCHANGED)
dec = cv2.imread(HERE + 'runs/decided_half.png', 0) > 0
base = dict(np.load(HERE + f'runs/baseline_g{g}.npz'))
E = {}
acc = np.zeros((H // F + 3, W // F + 3), np.uint8)
for s in PAIRS:
    r = dict(np.load(HERE + f'runs/{s}_g{g}.npz')); df = dict(np.load(HERE + f'runs/{s}_g{g}_diff.npz'))
    E[s] = dict(r=r, new=r['P'][df['new']], lost=ben['P'][df['lost']], newmask=df['new'], lostmask=df['lost'])
    for P in (E[s]['new'], E[s]['lost']):
        q = np.clip((P / F).astype(int), 0, [acc.shape[1] - 1, acc.shape[0] - 1]); acc[q[:, 1], q[:, 0]] = 1
acc = cv2.dilate(acc, np.ones((7, 7), np.uint8))
n, lab = cv2.connectedComponents(acc, connectivity=8)
rows = []
for k in range(1, n):
    rows.append(dict(id=k))
def lab_of(P): q = np.clip((P / F).astype(int), 0, [lab.shape[1] - 1, lab.shape[0] - 1]); return lab[q[:, 1], q[:, 0]]
per = {s: dict(new=np.bincount(lab_of(E[s]['new']), minlength=n), lost=np.bincount(lab_of(E[s]['lost']), minlength=n)) for s in PAIRS}
for row in rows:
    k = row['id']
    row['by_pair'] = {s: dict(new_false=int(per[s]['new'][k]), lost=int(per[s]['lost'][k])) for s in PAIRS}
    row['size'] = float(np.mean([per[s]['new'][k] + per[s]['lost'][k] for s in PAIRS]))
    ys, xs = np.nonzero(lab == k); row['bbox_full'] = [int(xs.min() * F), int(ys.min() * F), int(xs.max() * F + F), int(ys.max() * F + F)]
rows.sort(key=lambda r: -r['size'])
top = rows[:10]
os.makedirs(HERE + 'pics', exist_ok=True)
img = cv2.imread(SP + 'cufp/22-44.jpg')
blmap = cv2.imread(EV + f'baseline/maps44/grid{g}/44_lines.png', 0)
WW, HH = 1400, 1000
for i, row in enumerate(top):
    k = row['id']
    s = max(PAIRS, key=lambda s: per[s]['new'][k] + per[s]['lost'][k]); row['pair_shown'] = s
    pts = np.vstack([E[s]['new'][lab_of(E[s]['new']) == k], E[s]['lost'][lab_of(E[s]['lost']) == k]])
    # the window holding most error samples: try centres on a coarse grid of the samples
    best, bc = -1, None
    for c in pts[::max(1, len(pts) // 200)]:
        x0 = int(np.clip(c[0] - WW / 2, 0, W - WW)); y0 = int(np.clip(c[1] - HH / 2, 0, H - HH))
        m = ((pts[:, 0] >= x0) & (pts[:, 0] < x0 + WW) & (pts[:, 1] >= y0) & (pts[:, 1] < y0 + HH)).sum()
        if m > best: best, bc = m, (x0, y0)
    x0, y0 = bc; row['window'] = [x0, y0, x0 + WW, y0 + HH]
    crop = img[y0:y0 + HH, x0:x0 + WW].copy()
    def draw(P, col, rad, sel=None):
        Q = P if sel is None else P[sel]
        Q = Q - [x0, y0]; ok = (Q[:, 0] >= 0) & (Q[:, 0] < WW) & (Q[:, 1] >= 0) & (Q[:, 1] < HH)
        for x, y in Q[ok].astype(int): cv2.circle(crop, (int(x), int(y)), rad, col, -1)
    draw(ben['P'], (255, 120, 0), 0)
    draw(base['P'], (0, 170, 0), 0)
    r = E[s]['r']
    draw(r['P'], (0, 140, 255), 0, ~E[s]['newmask'])
    draw(ben['P'], (200, 0, 200), 2, E[s]['lostmask'])
    draw(r['P'], (0, 0, 230), 1, E[s]['newmask'])
    lm = cv2.imread(EV + f'{s}/maps44/grid{g}/44_lines.png', 0)
    a = cv2.resize(blmap[y0:y0 + HH, x0:x0 + WW], (WW // 2, HH // 2)); b = cv2.resize(lm[y0:y0 + HH, x0:x0 + WW], (WW // 2, HH // 2))
    bottom = cv2.cvtColor(np.hstack([255 - a, 255 - b]), cv2.COLOR_GRAY2BGR)
    cv2.putText(bottom, 'P(line) baseline', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2); cv2.putText(bottom, f'P(line) {s}', (WW // 2 + 10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)
    cv2.putText(crop, f'#{i + 1} {s} grid0 window x{x0}-{x0 + WW} y{y0}-{y0 + HH}: red new false, magenta lost, orange other shown, green baseline shown, blue Ben', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    cv2.imwrite(HERE + f'pics/err_{i + 1}.jpg', np.vstack([crop, bottom]), [cv2.IMWRITE_JPEG_QUALITY, 88])
    # what lies under: ink of the error samples in the window
    def inkof(P):
        q = np.round(P).astype(int); cnt = np.zeros(10, int)
        for x, y in q:
            w = bins[max(0, y - 3):y + 4, max(0, x - 3):x + 4].ravel(); w = w[w > 0]
            cnt[np.bincount(w).argmax() if len(w) else 0] += 1
        return cnt.tolist()
    inw = lambda P: P[(P[:, 0] >= x0) & (P[:, 0] < x0 + WW) & (P[:, 1] >= y0) & (P[:, 1] < y0 + HH)]
    row['ink_new_false_in_window'] = inkof(inw(E[s]['new'])); row['ink_lost_in_window'] = inkof(inw(E[s]['lost']))
    cx, cy = x0 + WW // 2, y0 + HH // 2; row['decided_at_centre'] = bool(dec[cy // 2, cx // 2])
    print(i + 1, row['id'], round(row['size']), s, row['bbox_full'], 'window', row['window'], row['by_pair'], 'ink new', row['ink_new_false_in_window'], 'ink lost', row['ink_lost_in_window'], flush=True)
json.dump(dict(note=__doc__, top=top, all_sizes=[[r['id'], round(r['size']), r['bbox_full']] for r in rows[:40]]), open(HERE + 'clusters.json', 'w'), indent=1)
