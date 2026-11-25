"""ben_lines_text44.py (text/effect, 25 Nov 2026): how much of Ben's plate-44 lines (streetmap/22-44.json) each text mask
lies on (mask within 1 px of the line, i.e. the line's own pixels would be masked) and touches (within 2 px), by kind.
    cd data/sanborn; python -B bench_2026-11-25/text/effect/code/ben_lines_text44.py      -> scores/ben_lines_text44.json"""
import json, os
import numpy as np, cv2
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); MK = os.path.join(ROOT, 'masks')
SM = json.load(open('streetmap/22-44.json', encoding='utf8')); H, W = 7219, 10768
P, K = [], []
for l in SM['lines']:
    a, b = np.array(l['a'], float), np.array(l['b'], float); n = max(1, int(np.ceil(np.hypot(*(b - a))))); t = (np.arange(n) + 0.5) / n
    P.append(a + t[:, None] * (b - a)); K += [l.get('kind', '')] * n
P = np.clip(np.round(np.concatenate(P)).astype(int), 0, [W - 1, H - 1]); K = np.array(K); out = {}
for m in ('Sref', 'I2', 'B2', 'B2L', 'S1'):
    M = cv2.imread(os.path.join(MK, f'44_map_{m}.png'), 0) > 0; o = {}
    for r, nm in ((1, 'on_1px'), (2, 'touch_2px')):
        D = cv2.dilate(M.astype(np.uint8), np.ones((2 * r + 1, 2 * r + 1), np.uint8)) > 0; v = D[P[:, 1], P[:, 0]]
        o[nm] = {k: round(float(v[K == k].mean()), 4) for k in sorted(set(K))}; o[nm]['all'] = round(float(v.mean()), 4)
    out[m] = o; print(m, json.dumps(o))
json.dump(out, open(os.path.join(ROOT, 'scores', 'ben_lines_text44.json'), 'w'), indent=1)
