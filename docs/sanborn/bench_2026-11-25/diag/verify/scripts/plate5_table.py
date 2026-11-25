"""plate5_table.py (diag/verify, 25 Nov 2026): the plate-5 end-to-end runs (run_plate5.py) side by side: headline
scores and the stage-0 (area map alone) block scores, each minus the batch pair (base). One tile grid only, so a
difference under about 0.03 PQ is within the grid-to-grid noise seen on 44 (sd 0.01-0.04). Ben's plate-5 lines started
from the batch's lines, so the batch pair starts ahead on line precision and recall. V2 trained on 5's pseudo labels
(in sample). Read-only; writes diag/verify/plate5_table.json.
    python -B plate5_table.py
"""
import json, os
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
D = SP + 'bench_2026-11-25/diag/verify/plate5/runs/'
K = ['PQ', 'PQ_decided', 'matched', 'merges', 'fp', 'fp_decided', 'recall_interior', 'precision']
R = {}
for tag in ('base', 'check_batch', 'V1S1', 'V1S2', 'aV1S1', 'aV1S2', 'bV1S1', 'bV1S2', 'V2S1', 'V2S2'):
    f = D + f'{tag}/bench_plate.json'
    if not os.path.exists(f): continue
    b = json.load(open(f, encoding='utf8'))
    h = b['headline']['A'] if 'A' in b['headline'] else b['headline']['all']
    r = {k: h[k] for k in K}
    s0 = b['stages']['0_area_map_alone']; r['s0_PQ'] = s0['blocks']['A']['PQ']; r['s0_PQ_decided'] = s0['blocks_decided']['A']['PQ']
    r['s0_matched'] = s0['blocks']['A']['matched']; r['s0_fp'] = s0['blocks']['A']['fp']
    R[tag] = r
base = R.get('base')
for tag, r in R.items():
    if base and tag != 'base':
        for k in ('PQ', 'PQ_decided', 's0_PQ', 's0_PQ_decided', 'recall_interior', 'precision'): r['d_' + k] = round(r[k] - base[k], 4)
    print(tag.ljust(12), json.dumps(r))
json.dump(R, open(SP + 'bench_2026-11-25/diag/verify/plate5_table.json', 'w'), indent=1)
