"""Where the proposed streetcar tracing P2 adds length over the batch's, on every batch plate except 44/1A, and a random
sample of points on that added length for a visual check (bench_2026-11-21/rail). Read-only on the repo.
    cd data/sanborn
    python bench_2026-11-21/rail/exp_p2_added.py N_SAMPLE SEED
Writes exp/p2/N_rail_rule.json (batch railroad + P2 streetcar), exp/p2/added_sample.json."""
import sys, json, os, re
sys.path.insert(0, 'bench_2026-11-21/rail')
import numpy as np, cv2
from rail_variants import streetcar_tracks_v2
from score_rail_bench import samples, seglen_weights, draw, dist, clip
O = 'bench_2026-11-21/rail/exp/p2'; os.makedirs(O, exist_ok=True)
n, seed = int(sys.argv[1]), int(sys.argv[2])
S = json.load(open('unet_data/run_plates.json', encoding='utf8')); order = lambda k: (int(re.match(r'\d+', k).group()), k)
segs = []; tot_add = 0.0
for N in sorted(S, key=order):
    if N in ('44', '1A'): continue
    B = cv2.imread(f'unet_data/{N}_bins.png', 0); H, W = B.shape; old = json.load(open(f'unet_data/{N}_rail_rule.json', encoding='utf8'))['tracks']
    car = streetcar_tracks_v2((B == 5).astype(np.uint8), reach=400, across=25, single=250, curved=True)
    json.dump(dict(plate=N, note='bench P2 streetcar + batch railroad', tracks=[t for t in old if t['kind'] == 'railroad'] + [dict(kind='streetcar', src='rule', pts=p.tolist()) for p in car]), open(f'{O}/{N}_rail_rule.json', 'w'))
    D = dist(draw([t['pts'] for t in old if t['kind'] == 'streetcar'], H, W))
    for p in car:
        Sm = samples(p); w = seglen_weights(Sm); q = clip(Sm, H, W); add = D[q[:, 1], q[:, 0]] > 15
        for s, ww in zip(Sm[add], w[add]): segs.append((N, s, ww)); tot_add += ww
print(f'P2 streetcar length farther than 15 px from the batch streetcar tracks: {tot_add:.0f} px')
cum = np.cumsum([s[2] for s in segs]); rng = np.random.default_rng(seed); pts = []
for u in np.sort(rng.uniform(0, cum[-1], n)):
    k = int(np.searchsorted(cum, u)); N, s, _ = segs[k]; pts.append(dict(plate=N, a=[round(float(s[0])), round(float(s[1]))], b=[round(float(s[0])), round(float(s[1]))], mark=True))
pts.sort(key=lambda x: order(x['plate'])); json.dump(pts, open(f'{O}/added_sample.json', 'w'), indent=1)
