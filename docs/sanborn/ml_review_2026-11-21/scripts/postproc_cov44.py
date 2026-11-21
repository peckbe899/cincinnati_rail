import json, numpy as np, cv2
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
full = cv2.imread(SP + 'cufp/22-44.jpg'); H, W = full.shape[:2]
hsv = cv2.cvtColor(full, cv2.COLOR_BGR2HSV); ink = (hsv[:, :, 2] < 120) | ((hsv[:, :, 1] < 90) & (hsv[:, :, 2] < 170)); del hsv
g = cv2.GaussianBlur(np.where(ink, cv2.cvtColor(full, cv2.COLOR_BGR2GRAY), 255).astype(np.uint8), (3, 3), 0).astype(np.float32)
def along(img, a, b, o=0.0):
    d = b - a; L = np.hypot(*d); nrm = np.array([-d[1], d[0]]) / (L or 1); t = np.linspace(0.06, 0.94, max(10, int(L))); q = a + np.outer(t, d) + nrm * o
    return img[np.clip(q[:, 1].round().astype(int), 0, H - 1), np.clip(q[:, 0].round().astype(int), 0, W - 1)]
def coverage(a, b):
    d = b - a; nrm = np.array([-d[1], d[0]]) / np.hypot(*d)
    c = np.min([along(g, a + nrm * s, b + nrm * s) for s in (-2, -1, 0, 1, 2)], axis=0)
    l = np.min([along(g, a + nrm * s, b + nrm * s) for s in (-7, -6, -5)], axis=0); r = np.min([along(g, a + nrm * s, b + nrm * s) for s in (5, 6, 7)], axis=0)
    return float(((c < 170) & (l > c + 40) & (r > c + 40)).mean())
sm = json.load(open(SP + 'streetmap/22-44.json', encoding='utf8'))
bn = np.full((H, W), 255, np.uint8)
for l in sm['lines']: cv2.line(bn, tuple(np.round(l['a']).astype(int)), tuple(np.round(l['b']).astype(int)), 0, 1)
dbn = cv2.distanceTransform(bn, cv2.DIST_L2, 3)
o = json.load(open(SP + 'picks22_guided/22-44/outlines.json', encoding='utf8')); rows = []
for p in o:
    for s in p:
        if s['state'] != 'on print' or s.get('paper_edge'): continue
        a, b = np.array(s['a']), np.array(s['b']); L = np.hypot(*(b - a)); n = max(2, int(L / 4)); P = a + np.outer(np.linspace(0, 1, n), b - a)
        on = (dbn[np.clip(P[:, 1].round().astype(int), 0, H - 1), np.clip(P[:, 0].round().astype(int), 0, W - 1)] <= 6).mean()
        rows.append((coverage(a, b), L, on))
r = np.array(rows)
for lo, hi in ((0, .3), (.3, .5), (.5, .7), (.7, 1.01)):
    m = (r[:, 0] >= lo) & (r[:, 0] < hi)
    if m.any(): print(f'green sides with coverage {lo:.1f}-{hi:.1f}: n={m.sum():3d}, length {r[m, 1].sum():6.0f}, on Ben\'s lines {100 * (r[m, 1] * r[m, 2]).sum() / r[m, 1].sum():.1f}%')
