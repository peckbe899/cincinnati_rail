"""pq_without_void.py (diag/swap, 25 Nov 2026): bench44's PQ (all) recomputed per grid with the false blocks that lie
more than half on undecided ground (fp_anatomy.py's 'void' kind) left out; SQ and matches unchanged, so it is bench44's
own formula PQ = SQ * TP / (TP + FP/2 + FN/2). Reads diag/swap/fp/*.json. System python."""
import json, glob, os
import numpy as np
D = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-25/diag/swap/'
base = None; rows = {}
for f in sorted(glob.glob(D + 'fp/*.json')):
    d = json.load(open(f)); per = d['per_grid']; r = {}
    for g, p in per.items():
        tp = p['matched']; fn = 55 - tp; fp = p['fp_bench44']; fpv = p['fp_by_kind']['void']
        r[g] = dict(PQ=p['PQ'], PQ_novoid=p['SQ'] * tp / (tp + 0.5 * (fp - fpv) + 0.5 * fn), void_fp=fpv)
    rows[d['name']] = r
B = rows['base']
out = {}
for n, r in rows.items():
    gs = sorted(r); out[n] = dict(PQ=round(np.mean([r[g]['PQ'] for g in gs]), 4), PQ_novoid=round(np.mean([r[g]['PQ_novoid'] for g in gs]), 4),
                                  gain_PQ=round(np.mean([r[g]['PQ'] - B[g]['PQ'] for g in gs]), 4), gain_PQ_novoid=round(np.mean([r[g]['PQ_novoid'] - B[g]['PQ_novoid'] for g in gs]), 4),
                                  up_novoid=int(sum(r[g]['PQ_novoid'] > B[g]['PQ_novoid'] for g in gs)), void_fp=round(np.mean([r[g]['void_fp'] for g in gs]), 2))
    print(n.ljust(16), json.dumps(out[n]))
json.dump(out, open(D + 'fp/pq_without_void.json', 'w'), indent=1)
