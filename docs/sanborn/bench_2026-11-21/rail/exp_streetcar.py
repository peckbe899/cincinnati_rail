"""Experiment: streetcar tracing variants on the rules-alone bins of 44 (complete) and 1A (10 checked tracks).
Read-only on the repo; writes bench_2026-11-21/rail/exp/streetcar_*.json.
    cd data/sanborn
    python bench_2026-11-21/rail/exp_streetcar.py"""
import sys, json, os
sys.path.insert(0, 'bench_2026-11-21/rail')
import numpy as np, cv2
import rail_tracks_copy as rt
from rail_variants import streetcar_tracks_v2
from score_rail_bench import score
OUT = 'bench_2026-11-21/rail/exp'; os.makedirs(OUT, exist_ok=True)
CASES = [('44', 'bench_2026-11-21/rail/runs/44_map_bins.png', 'picks22_guided/22-44/rail_ben.page_2026-11-21.json'),
         ('1A', 'bench_2026-11-21/rail/runs/1A_bins.png', 'picks22_guided/22-1A/rail_ben.json')]
VARS = [('V0 batch (rail_tracks.py)', None),
        ('V0b same settings, v2 code', dict()),
        ('V1 reach 300', dict(reach=300)),
        ('V2 reach 300 + lone piece >= 250', dict(reach=300, single=250)),
        ('V3 V2 + curved pieces traced', dict(reach=300, single=250, curved=True)),
        ('V4 reach 400, across 25, single 250, curved', dict(reach=400, across=25, single=250, curved=True)),
        ('V5 reach 300, ang 35, single 250, curved', dict(reach=300, ang=35, single=250, curved=True))]
res = []
for N, bp, tp in CASES:
    B = cv2.imread(bp, 0); H, W = B.shape; TJ = json.load(open(tp, encoding='utf8')); m = (B == 5).astype(np.uint8)
    rr = rt.railroad_tracks((B == 4).astype(np.uint8))
    for name, kw in VARS:
        car = rt.streetcar_tracks(m) if kw is None else streetcar_tracks_v2(m, **kw)
        tr = [dict(kind='railroad', pts=p.tolist()) for p in rr] + [dict(kind='streetcar', pts=p.tolist()) for p in car]
        r = score(N, tr, TJ, H, W); s = r['kinds']['streetcar']
        row = dict(plate=N, variant=name, n=len(car), px=round(sum(rt.plen(p) for p in car)))
        for tol in (10, 30):
            o = s[f'tol{tol}']; row.update({f'rec{tol}': o['recall'], f'pre{tol}': o['precision'], f'false{tol}': o['false_len'], f'found{tol}': o['found'], f'partial{tol}': o['partial'], f'missed{tol}': o['missed'], f'broken{tol}': o['broken'], f'gaps{tol}': o['gaps']})
        res.append(row)
        print(f"{N:3s} {name:44s} n {row['n']:3d} {row['px']:6d} px | 30px R {100 * row['rec30']:5.1f} P {100 * (row['pre30'] or 0):5.1f} false {row['false30']:5d} found/part/miss {row['found30']}/{row['partial30']}/{row['missed30']} broken {row['broken30']} gaps {row['gaps30']} | 10px R {100 * row['rec10']:5.1f} P {100 * (row['pre10'] or 0):5.1f}", flush=True)
json.dump(res, open(f'{OUT}/streetcar_variants.json', 'w'), indent=1)
