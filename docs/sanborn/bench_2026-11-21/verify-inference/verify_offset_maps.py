"""verify-inference: are the inference agent's moved-tile-grid maps (maps/offK_*) aligned with the plate? A wrong crop
after the reflect padding would shift the whole map and lower every off-grid score. For each map, the share of
P>0.5 decisions that differ from the batch grid's map of the same setting is computed at shifts of -3..3 px; the
smallest must be at shift (0, 0). Read only; prints and writes logs/offset_maps.json.

    python verify_offset_maps.py
"""
import json
import numpy as np, cv2
V = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-21/verify-inference/'
M = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-21/inference/maps/'
out = {}
for ref, fam in (('batch', 'tta1'), ('a_tta8', 'a_tta8')):
    for kind in ('area', 'lines'):
        r = cv2.imread(M + f'{ref}/44_{kind}.png', 0) > 127
        for i in range(1, 6):
            m = cv2.imread(M + f'off{i}_{fam}/44_{kind}.png', 0) > 127; c = r[8:-8, 8:-8]; best = None
            for dy in range(-3, 4):
                for dx in range(-3, 4):
                    s = m[8 + dy:m.shape[0] - 8 + dy, 8 + dx:m.shape[1] - 8 + dx]; v = float((s != c).mean())
                    if best is None or v < best[0]: best = (v, dy, dx)
            z = float((m[8:-8, 8:-8] != c).mean())
            out[f'off{i}_{fam}_{kind}'] = dict(differ_at_0=round(z, 5), best_shift=best[1:], differ_at_best=round(best[0], 5))
            print(f'off{i}_{fam:6s} {kind:5s} decisions differ from the batch-grid map: {100 * z:.2f}% at (0,0); best shift {best[1:]}')
json.dump(out, open(V + 'logs/offset_maps.json', 'w'), indent=1)
