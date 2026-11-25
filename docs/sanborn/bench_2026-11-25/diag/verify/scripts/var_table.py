"""var_table.py (diag/verify, 25 Nov 2026): the outline-step robustness test. For each outline setting VAR (outlines_var.py:
SB10 = SEED_B 10, SB20 = SEED_B 20, MS1000 / MS4000 = MK_SEED_MIN 1000 / 4000; 'default' = the runs as they are), the
6-grid mean PQ / PQ_decided of the baseline and of each pair under that same setting, and each pair's paired gain over
the baseline under that setting (grid by grid). If the new area maps lose only because the outline step was tuned on
area_ng1's maps of 44, the gains should shrink under other settings. Read-only; writes diag/verify/var_table.json.
    python -B var_table.py
"""
import json, os
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
D = SP + 'bench_2026-11-25/diag/'


def runs(path):
    out = []
    for g in range(6):
        p = path.format(g=g)
        if not os.path.exists(p): return None
        h = json.load(open(p, encoding='utf8'))['headline']['all']; out.append(h)
    return out


R = {}
for var in ('default', 'SB10', 'SB20', 'MS1000', 'MS4000'):
    if var == 'default':
        paths = {'base': D + 'swap/runs_baseline44/base__grid{g}/bench44.json'}
        for s in ('V1S1', 'V1S2', 'V2S1', 'V2S2'): paths[s] = SP + f'train_v2_runs/eval/{s}/runs44/v2__grid{{g}}/bench44.json'
    else:
        paths = {m: D + f'verify/mix/{m}__{var}/runs44/v2__grid{{g}}/bench44.json' for m in ('base', 'V1S1', 'V1S2', 'V2S1', 'V2S2')}
    H = {m: runs(p) for m, p in paths.items()}
    if H['base'] is None: continue
    row = {'base': dict(PQ=round(sum(h['PQ'] for h in H['base']) / 6, 4), PQ_decided=round(sum(h['PQ_decided'] for h in H['base']) / 6, 4), fp=round(sum(h['fp'] for h in H['base']) / 6, 2))}
    for m in ('V1S1', 'V1S2', 'V2S1', 'V2S2'):
        if H[m] is None: continue
        gains = [a['PQ'] - b['PQ'] for a, b in zip(H[m], H['base'])]; gd = [a['PQ_decided'] - b['PQ_decided'] for a, b in zip(H[m], H['base'])]
        row[m] = dict(PQ=round(sum(h['PQ'] for h in H[m]) / 6, 4), gain=round(sum(gains) / 6, 4), up=sum(x > 0 for x in gains), gain_decided=round(sum(gd) / 6, 4), up_decided=sum(x > 0 for x in gd))
    R[var] = row
    print(var.ljust(8), json.dumps(row))
json.dump(R, open(D + 'verify/var_table.json', 'w'), indent=1)
