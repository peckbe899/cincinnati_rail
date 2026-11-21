"""Find the printed KEY box on every batch plate (rail-rules, 21 Nov 2026). Read-only on the repo; writes only into
bench_2026-11-21/rail-rules/key/.
Two templates, both the whole KEY box cut at quarter size from a sheet at run time:
  T19  plate 19, full-size box (6230, 262)-(7090, 1730)   (the box visual-pdf/make_templates.py uses)
  T86  plate 86, full-size box (9714, 1186)-(10486, 2557) (the box rail/key_find.py uses)
Matching: quarter-size grey, Gaussian blur sigma 1 on image and template, TM_CCOEFF_NORMED, scales 0.95 / 1.0 / 1.05.
    cd data/sanborn
    python bench_2026-11-21/rail-rules/key_scan.py
Writes key/key_scan.json (best score and box per plate and template) and key/key_scan_*.jpg (the best box of every
plate scoring 0.3 or more, for checking by eye)."""
import os, re, json
import numpy as np, cv2
OUT = 'bench_2026-11-21/rail-rules/key'; os.makedirs(OUT, exist_ok=True)
S = json.load(open('unet_data/run_plates.json', encoding='utf8')); order = lambda n: (int(re.match(r'\d+', n).group()), n)
F = 4
TPL = {'T19': ('19', 6230, 262, 7090, 1730), 'T86': ('86', 9714, 1186, 10486, 2557)}


def grey4(N):
    g = cv2.imread(f'cufp/22-{N}.jpg', cv2.IMREAD_REDUCED_GRAYSCALE_4); return cv2.GaussianBlur(g, (0, 0), 1.0).astype(np.float32)


T = {}
for k, (n, x0, y0, x1, y1) in TPL.items():
    T[k] = grey4(n)[y0 // F:y1 // F, x0 // F:x1 // F].copy()
rows = []
for N in sorted(S, key=order):
    g = grey4(N); r = dict(plate=N, source='pdf' if os.path.exists(f'cufp/{N}/source.json') else 'cut', size=[g.shape[1] * F, g.shape[0] * F])
    for k, t0 in T.items():
        best = (-1.0, None)
        for s in (0.95, 1.0, 1.05):
            t = cv2.resize(t0, None, fx=s, fy=s, interpolation=cv2.INTER_AREA) if s != 1.0 else t0
            if g.shape[0] <= t.shape[0] or g.shape[1] <= t.shape[1]: continue
            m = cv2.matchTemplate(g, t, cv2.TM_CCOEFF_NORMED); _, mx, _, (x, y) = cv2.minMaxLoc(m)
            if mx > best[0]: best = (float(mx), [x * F, y * F, (x + t.shape[1]) * F, (y + t.shape[0]) * F])
        r[k] = round(best[0], 3); r[k + '_box'] = best[1]
    rows.append(r); print(r, flush=True)
json.dump(rows, open(f'{OUT}/key_scan.json', 'w'), indent=1)
# montage of the best T19 box per plate with either score >= 0.3, labelled, sorted by score
sel = sorted([r for r in rows if max(r['T19'], r['T86']) >= 0.3], key=lambda r: -max(r['T19'], r['T86']))
tiles = []
for r in sel:
    k = 'T19' if r['T19'] >= r['T86'] else 'T86'; x0, y0, x1, y1 = r[k + '_box']
    im = cv2.imread(f'cufp/22-{r["plate"]}.jpg', cv2.IMREAD_REDUCED_COLOR_4)[y0 // F:y1 // F, x0 // F:x1 // F]
    im = cv2.resize(im, (160, 270), interpolation=cv2.INTER_AREA); im = cv2.copyMakeBorder(im, 22, 0, 0, 0, cv2.BORDER_CONSTANT, value=(255, 255, 255))
    cv2.putText(im, f"{r['plate']} {r['T19']:.2f}/{r['T86']:.2f}", (2, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1); tiles.append(im)
for p in range(0, len(tiles), 30):
    t = tiles[p:p + 30]; t += [np.full_like(tiles[0], 255)] * (30 - len(t))
    cv2.imwrite(f'{OUT}/key_scan_{p // 30}.jpg', np.vstack([np.hstack(t[i:i + 10]) for i in range(0, 30, 10)]), [cv2.IMWRITE_JPEG_QUALITY, 85])
