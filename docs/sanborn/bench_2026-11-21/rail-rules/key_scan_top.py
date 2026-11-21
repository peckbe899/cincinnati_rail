"""As key_scan.py, but with only the top of the KEY box as the template (its title and the RAILROAD / TROLLEY / WATER
PIPE / SEWER samples), so a KEY cut by the plate's edge (1B) is still found. Read-only on the repo; writes key/key_scan_top.json.
    cd data/sanborn
    python bench_2026-11-21/rail-rules/key_scan_top.py"""
import os, re, json
import numpy as np, cv2
OUT = 'bench_2026-11-21/rail-rules/key'
S = json.load(open('unet_data/run_plates.json', encoding='utf8')); order = lambda n: (int(re.match(r'\d+', n).group()), n)
F = 4
TPL = {'T19top': ('19', 6230, 262, 7090, 742), 'T86top': ('86', 9714, 1186, 10486, 1636)}
def grey4(N):
    g = cv2.imread(f'cufp/22-{N}.jpg', cv2.IMREAD_REDUCED_GRAYSCALE_4); return cv2.GaussianBlur(g, (0, 0), 1.0).astype(np.float32)
T = {k: grey4(n)[y0 // F:y1 // F, x0 // F:x1 // F].copy() for k, (n, x0, y0, x1, y1) in TPL.items()}
rows = []
for N in sorted(S, key=order):
    g = grey4(N); r = dict(plate=N)
    for k, t0 in T.items():
        best = (-1.0, None)
        for s in (0.95, 1.0, 1.05):
            t = cv2.resize(t0, None, fx=s, fy=s, interpolation=cv2.INTER_AREA) if s != 1.0 else t0
            m = cv2.matchTemplate(g, t, cv2.TM_CCOEFF_NORMED); _, mx, _, (x, y) = cv2.minMaxLoc(m)
            if mx > best[0]: best = (float(mx), [x * F, y * F, (x + t.shape[1]) * F, (y + t.shape[0]) * F])
        r[k] = round(best[0], 3); r[k + '_box'] = best[1]
    rows.append(r); print(r, flush=True)
json.dump(rows, open(f'{OUT}/key_scan_top.json', 'w'), indent=1)
