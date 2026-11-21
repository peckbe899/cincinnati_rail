"""Plate 44: Ben's street corridors (thin ground between his lines that no block of his covers) vs the area label.
Ground Ben's map leaves unclosed is split by width: what an opening of OPEN half px removes is a corridor (a street,
alley or rail strip between his lines); what survives is wide unclosed ground (yards, open land, blocks left open)."""
import json, os, sys
import numpy as np, cv2
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; U = SP + 'unet_data/'
OUT = os.path.dirname(os.path.abspath(__file__)) + '/'
N = '44'; OPEN = int(sys.argv[1]) if len(sys.argv) > 1 else 91
SM = json.load(open(SP + f'streetmap/22-{N}.json', encoding='utf8'))
lab = cv2.imread(U + f'{N}_label.png', 0); h, w = lab.shape
alpha = cv2.resize(np.load(SP + f'cufp/{N}/png_alpha_s4.npy').astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR) > 0.5
I = lambda p: tuple(np.round(p).astype(int).tolist())
bk = np.zeros((h, w), np.uint8)
for b in SM['blocks']: cv2.fillPoly(bk, [np.round(np.array(b['ring']) / 2).astype(np.int32)], 1)
lines = np.zeros((h, w), np.uint8)
for l in SM['lines']: cv2.line(lines, I(np.array(l['a']) / 2), I(np.array(l['b']) / 2), 1, 3)
free = ((bk == 0) & alpha & (lines == 0)).astype(np.uint8)
# split free ground by Ben's lines: each connected piece is one face of his line drawing (open faces merge)
k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (OPEN, OPEN))
wide = cv2.morphologyEx(free, cv2.MORPH_OPEN, k)
wide = cv2.dilate(wide, np.ones((9, 9), np.uint8)) & free           # the wide part and its rim
corr = (free == 1) & (wide == 0)
core = cv2.dilate(lines, np.ones((5, 5), np.uint8)) == 0
res = dict(open_half_px=OPEN, corridor_px=int(corr.sum()), wide_unclosed_px=int(wide.sum()), ben_block_px=int((bk == 1).sum()), paper_px=int(alpha.sum()))
m = corr & core
res['label_on_corridor'] = {kk: round(float((lab[m] == kk).mean()), 4) for kk in (0, 1, 255)}
m2 = (wide == 1) & core
res['label_on_wide_unclosed'] = {kk: round(float((lab[m2] == kk).mean()), 4) for kk in (0, 1, 255)}
m3 = (bk == 1) & core
res['label_on_ben_block'] = {kk: round(float((lab[m3] == kk).mean()), 4) for kk in (0, 1, 255)}
bad = (m & (lab == 1)).astype(np.uint8); bad = cv2.morphologyEx(bad, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
n, cc, st, cen = cv2.connectedComponentsWithStats(bad, connectivity=8)
comps = sorted([(int(st[i, 4]), [int(st[i, 0] * 2), int(st[i, 1] * 2), int((st[i, 0] + st[i, 2]) * 2), int((st[i, 1] + st[i, 3]) * 2)]) for i in range(1, n)], reverse=True)
res['corridor_label1_components_gt500'] = [c for c in comps if c[0] > 500]
res['corridor_label1_px_total'] = int(bad.sum())
json.dump(res, open(OUT + f'corr{N}_result.json', 'w'), indent=1)
for kk, v in res.items(): print(kk, v)
img = cv2.imread(U + f'{N}_img.jpg'); vis = (img * 0.5 + 110).astype(np.uint8)
vis[corr & (lab == 1)] = (0, 0, 230); vis[corr & (lab == 0)] = (200, 120, 0); vis[corr & (lab == 255)] = (0, 200, 230)
vis[wide == 1] = (vis[wide == 1] * 0.6 + np.array([60, 60, 60]) * 0.4).astype(np.uint8)
for l in SM['lines']: cv2.line(vis, I(np.array(l['a']) / 2), I(np.array(l['b']) / 2), (0, 120, 0), 2)
for i, (a, bb) in enumerate(res['corridor_label1_components_gt500'][:30]):
    cv2.putText(vis, str(i), (bb[0] // 2, bb[1] // 2), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 0), 3)
cv2.imwrite(OUT + f'corr{N}.jpg', cv2.resize(vis, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 85])
