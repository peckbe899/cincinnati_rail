"""overview5.py (text/effect, 25 Nov 2026): plate 5 at 1/6 size with the 23 railroad tracks Ben deleted, coloured by
the first text mask that removes them: green = today's text bin (S0) already removes it; orange = only the text bin
sorted with rail off (S1) or the idealised mask removes it; red = no mask removes it. Group numbers as diag/rail5.
    cd data/sanborn; python -B bench_2026-11-25/text/effect/code/overview5.py      -> crops/overview5_text_first.jpg"""
import json, os
import numpy as np, cv2
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); RU = os.path.join(ROOT, 'runs')
G5 = json.load(open(os.path.join(ROOT, '..', '..', 'diag', 'rail5', 'crops', 'groups.json')))
rr = lambda f: [np.array(t['pts'], float) for t in json.load(open(os.path.join(RU, f), encoding='utf8'))['tracks'] if t['kind'] == 'railroad']
im = cv2.imread('cufp/22-5.jpg'); H, W = im.shape[:2]; S = 6; c = cv2.resize(im, (W // S, H // S), interpolation=cv2.INTER_AREA); c = (c * 0.6 + 100).astype(np.uint8)
base = rr('5_nets_base_tracks.json')
def dmap(T):
    m = np.zeros((H, W), np.uint8)
    for p in T: cv2.polylines(m, [np.round(p).astype(np.int32)], False, 1, 1)
    return cv2.distanceTransform((m == 0).astype(np.uint8), cv2.DIST_L2, 5)
D = {k: dmap(rr(f'5_nets_{k}_tracks.json')) for k in ('tS0', 'tS1', 'tI2')}
def kept(p, d):
    q = np.vstack([a + np.linspace(0, 1, max(2, int(np.hypot(*(b - a)) / 2)))[:, None] * (b - a) for a, b in zip(p[:-1], p[1:])]).round().astype(int)
    return (d[q[:, 1].clip(0, H - 1), q[:, 0].clip(0, W - 1)] <= 10).mean() >= 0.2
for p in base:
    col = (0, 170, 0) if not kept(p, D['tS0']) else ((0, 140, 255) if not kept(p, D['tS1']) or not kept(p, D['tI2']) else (0, 0, 230))
    cv2.polylines(c, [np.round(p / S).astype(np.int32)], False, col, 4)
for g in G5:
    x0, y0, x1, y1 = (np.array(g['box']) / S).astype(int); cv2.rectangle(c, (x0, y0), (x1, y1), (60, 60, 60), 1); cv2.putText(c, str(g['group']), (x0, max(14, y0 - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
cv2.imwrite(os.path.join(ROOT, 'crops', 'overview5_text_first.jpg'), c, [cv2.IMWRITE_JPEG_QUALITY, 88]); print('ok', c.shape)
