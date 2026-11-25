"""crops_masks44.py (text/effect, 25 Nov 2026): where plate 44's text touches Ben's street-map lines most, the four
line-test masks side by side (magenta: the mask; green: Ben's lines). Writes crops/masks44_*.png.
    cd data/sanborn; python -B bench_2026-11-25/text/effect/code/crops_masks44.py"""
import json, os
import numpy as np, cv2
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); MK = os.path.join(ROOT, 'masks')
im = cv2.imread('cufp/22-44.jpg'); H, W = im.shape[:2]
sm = json.load(open('streetmap/22-44.json', encoding='utf8')); ln = np.zeros((H, W), np.uint8)
for l in sm['lines']: cv2.line(ln, tuple(np.round(l['a']).astype(int).tolist()), tuple(np.round(l['b']).astype(int).tolist()), 1, 1)
S = cv2.imread(os.path.join(MK, '44_map_Sref.png'), 0) > 0
touch = S & (cv2.dilate(ln, np.ones((5, 5), np.uint8)) > 0)
T = cv2.resize(touch.astype(np.float32), (W // 400, H // 400), interpolation=cv2.INTER_AREA)
idx = np.argsort(T.ravel())[::-1][:12]; picks = []
for i in idx:
    ty, tx = divmod(int(i), T.shape[1]); c = (tx * 400 + 200, ty * 400 + 200)
    if all(abs(c[0] - p[0]) > 1500 or abs(c[1] - p[1]) > 1500 for p in picks): picks.append(c)
    if len(picks) == 3: break
for k, (cx, cy) in enumerate(picks):
    x0, y0, x1, y1 = max(0, cx - 300), max(0, cy - 200), min(W, cx + 300), min(H, cy + 200); raw = im[y0:y1, x0:x1]; P = [raw]
    for name in ('Sref', 'I', 'B', 'BL'):
        m = cv2.imread(os.path.join(MK, f'44_map_{name}.png'), 0)[y0:y1, x0:x1] > 0; ov = raw.copy()
        ov[m] = (0.45 * ov[m] + 0.55 * np.array([255, 0, 255])).astype(np.uint8); ov[ln[y0:y1, x0:x1] > 0] = (0, 160, 0)
        cv2.putText(ov, name, (8, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 2); P.append(ov)
    pic = np.vstack([np.vstack([p, np.full((5, p.shape[1], 3), 255, np.uint8)]) for p in P])
    cv2.imwrite(os.path.join(ROOT, 'crops', f'masks44_{k}_{x0}_{y0}.png'), pic); print(k, (x0, y0, x1, y1))
