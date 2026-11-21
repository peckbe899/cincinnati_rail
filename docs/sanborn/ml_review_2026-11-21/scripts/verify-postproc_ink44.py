"""on_ink null tests and coverage buckets on plate 44 (reads only)."""
import json, sys
import numpy as np, cv2
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; O = 'C:/Users/peckb/AppData/Local/Temp/claude/8945a8e3044b4e4c/2a2bcb12-80e8-4366-9a59-3be15cce3445/scratchpad/ml_review/verify-postproc/'
full = cv2.imread(SP + 'cufp/22-44.jpg'); H, W = full.shape[:2]
hsv = cv2.cvtColor(full, cv2.COLOR_BGR2HSV); ink = (hsv[:, :, 2] < 120) | ((hsv[:, :, 1] < 90) & (hsv[:, :, 2] < 170)); del hsv
gray = cv2.cvtColor(full, cv2.COLOR_BGR2GRAY)
print('ink gray values: median', float(np.median(gray[ink])), 'p25', float(np.percentile(gray[ink], 25)), 'p75', float(np.percentile(gray[ink], 75)))
g = cv2.GaussianBlur(np.where(ink, gray, 255).astype(np.uint8), (3, 3), 0).astype(np.float32); del full
alpha = cv2.resize(np.load(SP + 'cufp/44/png_alpha_s4.npy').astype(np.float32), (W, H)) > 0.5
def along(img, a, b, o=0.0):
    d = b - a; L = np.hypot(*d); nrm = np.array([-d[1], d[0]]) / (L or 1); t = np.linspace(0.06, 0.94, max(10, int(L))); q = a + np.outer(t, d) + nrm * o
    return img[np.clip(q[:, 1].round().astype(int), 0, H - 1), np.clip(q[:, 0].round().astype(int), 0, W - 1)]
def on_ink(a, b):
    d = b - a; nrm = np.array([-d[1], d[0]]) / np.hypot(*d)
    return bool(max(np.mean([along(g, a + nrm * s, b + nrm * s, o).mean() for o in (-6, -3, 3, 6)]) - along(g, a + nrm * s, b + nrm * s).mean() for s in (-2, -1, 0, 1, 2)) > 25)
def coverage(a, b):
    d = b - a; nrm = np.array([-d[1], d[0]]) / np.hypot(*d)
    c = np.min([along(g, a + nrm * s, b + nrm * s) for s in (-2, -1, 0, 1, 2)], axis=0)
    l = np.min([along(g, a + nrm * s, b + nrm * s) for s in (-7, -6, -5)], axis=0); r = np.min([along(g, a + nrm * s, b + nrm * s) for s in (5, 6, 7)], axis=0)
    return float(((c < 170) & (l > c + 40) & (r > c + 40)).mean())
sm = json.load(open(SP + 'streetmap/22-44.json', encoding='utf8'))
pr = [(np.array(l['a'], float), np.array(l['b'], float)) for l in sm['lines'] if l['kind'] == 'printed']
rng = np.random.default_rng(1)
def rate(segs):
    L = np.array([np.hypot(*(b - a)) for a, b in segs]); ok = np.array([on_ink(a, b) for a, b in segs]); return round(float((L * ok).sum() / L.sum()), 3), round(float(ok.mean()), 3)
print('Ben printed lines pass (by length, by count):', rate(pr))
for sh in (4, 8, 12):
    segs = []
    for a, b in pr:
        d = (b - a) / np.hypot(*(b - a)); n = np.array([-d[1], d[0]]); sg = rng.choice([-1, 1]); segs.append((a + n * sh * sg, b + n * sh * sg))
    print(f'shifted {sh} px pass:', rate(segs))
segs = []
for a, b in pr:
    for _ in range(3):
        while True:
            c = np.array([rng.uniform(0, W), rng.uniform(0, H)]); a2 = c - (b - a) / 2; b2 = c + (b - a) / 2
            if 0 <= min(a2[0], b2[0]) and max(a2[0], b2[0]) < W and 0 <= min(a2[1], b2[1]) and max(a2[1], b2[1]) < H and alpha[int(a2[1]), int(a2[0])] and alpha[int(b2[1]), int(b2[0])]: break
        segs.append((a2, b2))
print('random placement, same length+direction, pass:', rate(segs))
# synthetic coverage: a perfect line on 44's printed line, cut to fraction f -> does on_ink pass?  use Ben's lines, and blank (set to 255) part of g? -> instead: theoretical
# coverage buckets for ng-44 green sides, split by line-network support
lp = cv2.imread(O + 'lp_44_lines_ng1.png', 0).astype(np.float32)
bn = np.full((H, W), 255, np.uint8)
for l in sm['lines']: cv2.line(bn, tuple(np.round(l['a']).astype(int)), tuple(np.round(l['b']).astype(int)), 0, 1)
dbn = cv2.distanceTransform(bn, cv2.DIST_L2, 3)
for f in ('ol_44_area_ng1_lines_ng1.json', 'ol_44_edge_v1_lines_v2.json'):
    rows = []
    lpx = lp if 'ng1' in f else cv2.imread(O + 'lp_44_lines_v2.png', 0).astype(np.float32)
    for p in json.load(open(O + f)):
        for s in p:
            if s['state'] != 'on print' or s.get('paper_edge'): continue
            a, b = np.array(s['a']), np.array(s['b']); L = np.hypot(*(b - a)); n = max(2, int(L / 4)); P = a + np.outer(np.linspace(0, 1, n), b - a)
            on = (dbn[np.clip(P[:, 1].round().astype(int), 0, H - 1), np.clip(P[:, 0].round().astype(int), 0, W - 1)] <= 6).mean()
            rows.append((coverage(a, b), L, on, along(lpx, a, b).mean() > 90))
    r = np.array(rows, float); print(f)
    print('  short green (<130 px): n share %.2f, len share %.2f, on Ben %.3f' % ((r[:, 1] < 130).mean(), r[r[:, 1] < 130, 1].sum() / r[:, 1].sum(), (r[r[:, 1] < 130, 1] * r[r[:, 1] < 130, 2]).sum() / r[r[:, 1] < 130, 1].sum()))
    for sup in (1, 0):
        for lo, hi in ((0, .3), (.3, .5), (.5, .7), (.7, 1.01)):
            m = (r[:, 0] >= lo) & (r[:, 0] < hi) & (r[:, 3] == sup)
            if m.any(): print(f'  dt={sup} coverage {lo:.1f}-{hi:.1f}: n={int(m.sum()):3d}, len {r[m, 1].sum():7.0f}, on Ben {100 * (r[m, 1] * r[m, 2]).sum() / r[m, 1].sum():5.1f}%')
    m = (r[:, 3] == 1) & (r[:, 0] >= 0.5); print('  gate dt & cov>=0.5: precision %.3f len %.0f ; gate dt only: precision %.3f len %.0f' % ((r[m, 1] * r[m, 2]).sum() / r[m, 1].sum(), r[m, 1].sum(), (r[r[:, 3] == 1, 1] * r[r[:, 3] == 1, 2]).sum() / r[r[:, 3] == 1, 1].sum(), r[r[:, 3] == 1, 1].sum()))
