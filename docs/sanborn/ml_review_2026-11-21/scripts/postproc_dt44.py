"""44: precision against Ben's lines of green sides split by whether the line network runs under them (dt) and by length"""
import json, numpy as np, cv2, sys
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; U = SP + 'unet_data/'
LN = sys.argv[1] if len(sys.argv) > 1 else 'lines_v2'; OL = sys.argv[2] if len(sys.argv) > 2 else SP + 'picks22_guided/22-44/outlines.json'
pl = cv2.imread(U + f'44_lines_{LN}.png', 0); H, W = pl.shape; lp = cv2.GaussianBlur(pl, (5, 5), 0).astype(np.float32)
def along(img, a, b, o=0.0):
    d = b - a; L = np.hypot(*d); nrm = np.array([-d[1], d[0]]) / (L or 1); t = np.linspace(0.06, 0.94, max(10, int(L))); q = a + np.outer(t, d) + nrm * o
    x = np.clip(q[:, 0].round().astype(int), 0, W - 1); y = np.clip(q[:, 1].round().astype(int), 0, H - 1); return img[y, x]
sm = json.load(open(SP + 'streetmap/22-44.json', encoding='utf8'))
bn = np.full((H, W), 255, np.uint8)
for l in sm['lines']: cv2.line(bn, tuple(np.round(l['a']).astype(int)), tuple(np.round(l['b']).astype(int)), 0, 1)
dbn = cv2.distanceTransform(bn, cv2.DIST_L2, 3)
o = json.load(open(OL, encoding='utf8')); grp = {}
for p in o:
    for s in p:
        if s['state'] != 'on print' or s.get('paper_edge'): continue
        a, b = np.array(s['a']), np.array(s['b']); L = np.hypot(*(b - a)); dt = along(lp, a, b).mean() > 90
        n = max(2, int(L / 4)); P = a + np.outer(np.linspace(0, 1, n), b - a); on = (dbn[np.clip(P[:, 1].round().astype(int), 0, H - 1), np.clip(P[:, 0].round().astype(int), 0, W - 1)] <= 6).mean()
        for k in (('dt' if dt else 'no dt'), ('<130' if L < 130 else '>=130'), ('dt' if dt else 'no dt') + ('<130' if L < 130 else '>=130')):
            g = grp.setdefault(k, [0, 0, 0]); g[0] += L; g[1] += L * on; g[2] += 1
for k, (L, Lon, n) in grp.items(): print(f'green sides, {k:6s}: n={n:4d}, length {L:7.0f}, on Ben\'s lines {100 * Lon / L:.1f}%')
