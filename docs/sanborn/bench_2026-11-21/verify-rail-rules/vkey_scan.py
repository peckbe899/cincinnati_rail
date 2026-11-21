"""verify-rail-rules (21 Nov 2026): KEY detection margin on every batch plate, checked two ways.
  1. my own re-implementation of the score (mean over the two top-of-KEY templates of the best TM_CCOEFF_NORMED over
     scales 0.95/1.0/1.05, quarter-size grey blurred sigma 1), compared with rail-rules/key/key_scan_top.json;
  2. the patched ink_bins.key_box() itself (patched/ink_bins.py, imported; it only reads cufp/), full window.
Writes only keyscan/vkey_scan.json here.
    cd data/sanborn
    python bench_2026-11-21/verify-rail-rules/vkey_scan.py"""
import os, re, json, sys, time, importlib.util
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, 'keyscan'); os.makedirs(OUT, exist_ok=True)
spec = importlib.util.spec_from_file_location('ibp', os.path.join(HERE, 'patched', 'ink_bins.py')); ib = importlib.util.module_from_spec(spec); spec.loader.exec_module(ib)
S = json.load(open('unet_data/run_plates.json', encoding='utf8')); order = lambda n: (int(re.match(r'\d+', n).group()), n)
THEIRS = {r['plate']: r for r in json.load(open('bench_2026-11-21/rail-rules/key/key_scan_top.json'))}


def g4(N): return cv2.GaussianBlur(cv2.imread(f'cufp/22-{N}.jpg', cv2.IMREAD_REDUCED_GRAYSCALE_4), (0, 0), 1.0).astype(np.float32)


TPL = [g4(n)[y0 // 4:y1 // 4, x0 // 4:x1 // 4].copy() for n, (x0, y0, x1, y1), _ in ib.KEY_TPL]
rows = []
for N in sorted(S, key=order):
    t0 = time.time(); g = g4(N); sc = []
    for t0_ in TPL:
        b = -1.0
        for s in (0.95, 1.0, 1.05):
            t = cv2.resize(t0_, None, fx=s, fy=s, interpolation=cv2.INTER_AREA) if s != 1.0 else t0_
            if t.shape[0] >= g.shape[0] or t.shape[1] >= g.shape[1]: continue
            b = max(b, float(cv2.minMaxLoc(cv2.matchTemplate(g, t, cv2.TM_CCOEFF_NORMED))[1]))
        sc.append(b)
    H, W = g.shape[0] * 4, g.shape[1] * 4   # approx full size; key_box clips to the window it is given
    im = cv2.imread(f'cufp/22-{N}.jpg', cv2.IMREAD_GRAYSCALE); H, W = im.shape[:2]
    kb = ib.key_box(N, (0, 0, W, H))
    th = THEIRS.get(N, {})
    r = dict(plate=N, mine=[round(v, 3) for v in sc], mean=round(float(np.mean(sc)), 3), theirs=[th.get('T19top'), th.get('T86top')], key_box=kb, found=kb is not None, src='pdf' if os.path.exists(f'cufp/{N}/source.json') else 'cut', secs=round(time.time() - t0, 1))
    rows.append(r); print(json.dumps(r), flush=True)
json.dump(rows, open(os.path.join(OUT, 'vkey_scan.json'), 'w'), indent=1)
F = [r for r in rows if r['found']]; NF = [r for r in rows if not r['found']]
print('found', len(F), sorted(r['plate'] for r in F))
print('lowest found mean', min(F, key=lambda r: r['mean']) if F else None)
print('highest not-found mean', max(NF, key=lambda r: r['mean']) if NF else None)
print('decision == (mean >= KEY_MIN):', all(r['found'] == (r['mean'] >= ib.KEY_MIN) for r in rows))
print('my scores == theirs (3 dp):', sum(r['mine'] == r['theirs'] for r in rows), 'of', len(rows))
