"""Save the V1 (reach 300) and V4 streetcar variants' tracks for 44 and 1A, for scoring pictures (bench_2026-11-21/rail)."""
import sys, json
sys.path.insert(0, 'bench_2026-11-21/rail')
import numpy as np, cv2
import rail_tracks_copy as rt
from rail_variants import streetcar_tracks_v2
for N, bp in (('44', 'bench_2026-11-21/rail/runs/44_map_bins.png'), ('1A', 'bench_2026-11-21/rail/runs/1A_bins.png')):
    B = cv2.imread(bp, 0); rr = rt.railroad_tracks((B == 4).astype(np.uint8))
    for name, kw in (('V1', dict(reach=300)), ('V4', dict(reach=400, across=25, single=250, curved=True))):
        car = streetcar_tracks_v2((B == 5).astype(np.uint8), **kw)
        json.dump(dict(plate=N, note=f'bench variant {name} {kw}', tracks=[dict(kind='railroad', src='rule', pts=p.tolist()) for p in rr] + [dict(kind='streetcar', src='rule', pts=p.tolist()) for p in car]), open(f'bench_2026-11-21/rail/exp/{N}_{name}_rail_rule.json', 'w'))
