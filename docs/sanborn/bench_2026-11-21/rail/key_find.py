"""Find the printed KEY box on every plate by template matching (the KEY of uncut sheet 86 as the template), and count
the rules' rail inside it (bench_2026-11-21/rail). Read-only on the repo.
    cd data/sanborn
    python bench_2026-11-21/rail/key_find.py
Writes bench_2026-11-21/rail/census/key_boxes.json and a thumbnail per hit in census/key/."""
import os, re, json
import numpy as np, cv2
OUT = 'bench_2026-11-21/rail/census'; os.makedirs(f'{OUT}/key', exist_ok=True)
S = json.load(open('unet_data/run_plates.json', encoding='utf8'))
order = lambda n: (int(re.match(r'\d+', n).group()), n)
F = 8   # work at 1/8 size
g86 = cv2.imread('cufp/22-86.jpg', cv2.IMREAD_REDUCED_GRAYSCALE_8)
KX0, KY0, KX1, KY1 = 9714, 1186, 10486, 2557   # the KEY box on 86, full-size px (read off crops/86_keybox.jpg)
tpl = g86[KY0 // F:KY1 // F, KX0 // F:KX1 // F]
res = []
for N in sorted(S, key=order):
    g = cv2.imread(f'cufp/22-{N}.jpg', cv2.IMREAD_REDUCED_GRAYSCALE_8)
    if g.shape[0] < tpl.shape[0] or g.shape[1] < tpl.shape[1]: res.append(dict(plate=N, score=None)); continue
    best = (-1, None, 1.0)
    for s in (0.9, 1.0, 1.1):   # the sheets are all printed at one size; allow a little
        t = cv2.resize(tpl, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
        if g.shape[0] < t.shape[0] or g.shape[1] < t.shape[1]: continue
        m = cv2.matchTemplate(g, t, cv2.TM_CCOEFF_NORMED); _, mx, _, loc = cv2.minMaxLoc(m)
        if mx > best[0]: best = (mx, loc, s)
    sc, loc, s = best; x0, y0 = loc[0] * F, loc[1] * F; x1, y1 = x0 + int((KX1 - KX0) * s), y0 + int((KY1 - KY0) * s)
    r = dict(plate=N, source='pdf' if os.path.exists(f'cufp/{N}/source.json') else 'cut', score=round(float(sc), 3), box=[x0, y0, x1, y1])
    if sc >= 0.5:
        B = cv2.imread(f'unet_data/{N}_bins.png', 0)[y0:y1, x0:x1]; r['rr_bin_px'] = int((B == 4).sum()); r['sc_bin_px'] = int((B == 5).sum())
        T = json.load(open(f'unet_data/{N}_rail_rule.json', encoding='utf8'))['tracks']; inside = []
        for t in T:
            p = np.asarray(t['pts']); f = ((p[:, 0] >= x0) & (p[:, 0] < x1) & (p[:, 1] >= y0) & (p[:, 1] < y1)).mean()
            if f > 0.5: inside.append(dict(kind=t['kind'], len=round(float(np.hypot(*np.diff(p, axis=0).T).sum()))))
        r['tracks_inside'] = inside
        im = cv2.imread(f'cufp/22-{N}.jpg')[y0:y1, x0:x1].copy(); b = cv2.imread(f'unet_data/{N}_bins.png', 0)[y0:y1, x0:x1]; im[b == 4] = (0, 0, 230); im[b == 5] = (0, 150, 255)
        cv2.imwrite(f'{OUT}/key/{N}_key.jpg', cv2.resize(im, None, fx=0.3, fy=0.3, interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 85])
    res.append(r); print(r)
json.dump(res, open(f'{OUT}/key_boxes.json', 'w'), indent=1)
