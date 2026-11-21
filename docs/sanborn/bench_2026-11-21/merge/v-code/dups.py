"""v-code: lines the line editor shows (edit_server.clean of an N_edges.json) that lie on top of another shown line:
parallel within 3 deg, within 8 px of it along >= 50% of the shorter one (read only)."""
import json, sys
import numpy as np
sys.path.insert(0, 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/tools/sanborn/unet'); import edit_server as ES  # noqa
for f in sys.argv[1:]:
    E = ES.clean(json.load(open(f, encoding='utf8'))); n = len(E); dup = []; L = 0.0
    A = np.array([e['a'] for e in E], float); B = np.array([e['b'] for e in E], float)
    for i in range(n):
        for j in range(i + 1, n):
            a, b, c, d = A[i], B[i], A[j], B[j]; u = b - a; Lu = np.hypot(*u); v = d - c; Lv = np.hypot(*v)
            if Lu < 1 or Lv < 1 or abs(u @ v) / (Lu * Lv) < np.cos(np.radians(3)): continue
            if Lu < Lv: a, b, c, d, u, v, Lu, Lv = c, d, a, b, v, u, Lv, Lu   # a-b the shorter
            w = v / Lv; nrm = np.array([-w[1], w[0]])
            if max(abs((a - c) @ nrm), abs((b - c) @ nrm)) > 8: continue
            t0, t1 = sorted(((a - c) @ w, (b - c) @ w)); ov = min(t1, Lv) - max(t0, 0)
            if ov >= 0.5 * Lu: dup.append((i, j, E[i]['state'], E[j]['state'], round(ov))); L += ov
    print(json.dumps(dict(file=f[-60:], shown=n, on_top_pairs=len(dup), overlap_px=round(L), states=dict(__import__('collections').Counter(f'{x[2]}/{x[3]}' for x in dup)))))
