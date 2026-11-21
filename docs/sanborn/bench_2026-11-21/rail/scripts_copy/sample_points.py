"""Random points along the batch's rule tracks, uniform by length, for a visual precision estimate (bench_2026-11-21/rail).
Read-only on the repo. 44 and 1A are left out (their files mix in Ben's tracks).
    cd data/sanborn
    python bench_2026-11-21/rail/sample_points.py KIND N SEED OUT.json"""
import sys, json, os, re
import numpy as np
kind, n, seed, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
S = json.load(open('unet_data/run_plates.json', encoding='utf8')); order = lambda n: (int(re.match(r'\d+', n).group()), n)
segs = []
for N in sorted(S, key=order):
    if N in ('44', '1A'): continue
    for ti, t in enumerate(json.load(open(f'unet_data/{N}_rail_rule.json', encoding='utf8'))['tracks']):
        if t['kind'] != kind: continue
        p = np.asarray(t['pts'], float); L = float(np.hypot(*np.diff(p, axis=0).T).sum())
        for a, b in zip(p[:-1], p[1:]): segs.append((N, ti, L, a, b, float(np.hypot(*(b - a)))))
lens = np.array([s[5] for s in segs]); cum = np.cumsum(lens); rng = np.random.default_rng(seed); pts = []
for u in np.sort(rng.uniform(0, cum[-1], n)):
    k = int(np.searchsorted(cum, u)); N, ti, L, a, b, l = segs[k]; f = (u - (cum[k] - l)) / max(l, 1e-6); q = a + f * (b - a)
    pts.append(dict(plate=N, track=ti, len=round(L), a=[round(float(q[0])), round(float(q[1]))], b=[round(float(q[0])), round(float(q[1]))], mark=True))
pts.sort(key=lambda x: order(x['plate'])); json.dump(pts, open(out, 'w'), indent=1)
print(f'{kind}: total rule length {cum[-1]:.0f} px; {n} points written to {out}')
