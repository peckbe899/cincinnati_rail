"""collect_runs.py (diag/verify, 25 Nov 2026): re-read every plate-44 bench44.json that the swap agent and the run left,
recompute the 6-grid means and the paired gains (run minus the baseline, grid by grid), and add the stage-by-stage PQ
(0 = area map alone, 1 = watershed regions, 2 = straightened outlines = the headline). Read-only on everything; writes
diag/verify/runs_table.json and prints a table.
    python -B collect_runs.py
"""
import json, os, glob, hashlib
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
D = SP + 'bench_2026-11-25/diag/'
OUT = D + 'verify/'


def jl(p):
    with open(p, encoding='utf8') as f: return json.load(f)


def grid_runs(runs_dir, prefix='v2__grid'):
    out = {}
    for g in range(6):
        p = f'{runs_dir}/{prefix}{g}/bench44.json'
        if os.path.exists(p): out[g] = jl(p)
    return out


def row(b):
    h = b['headline']['all']; st = b['stages']
    r = dict(PQ=h['PQ'], PQ_decided=h['PQ_decided'], fp=h['fp'], fp_decided=h['fp_decided'], matched=h['matched'], merges=h['merges'],
             recall=h['recall_interior'], precision=h['precision'])
    for k, name in (('0_area_map_alone', 's0'), ('1_watershed_regions', 's1'), ('2_straightened_outlines', 's2')):
        bb = st[k]['blocks']['all']; r[name + '_PQ'] = bb['PQ']; r[name + '_fp'] = bb['fp']; r[name + '_matched'] = bb['matched']; r[name + '_merges'] = bb['merges']
        bd = st[k]['blocks_decided']['all']; r[name + '_PQd'] = bd['PQ']
    r['lines_sha'] = b['meta'].get('lines_sha'); r['area_sha'] = b['meta'].get('area_sha'); r['area'] = b['meta'].get('area')
    return r


base = {g: row(b) for g, b in grid_runs(D + 'swap/runs_baseline44', 'base__grid').items()}
sets = {}
for s in ('V1S1', 'V1S2', 'V2S1', 'V2S2'):
    sets[f'pair:{s}'] = SP + f'train_v2_runs/eval/{s}/runs44'
for e in sorted(glob.glob(D + 'swap/eval/*/runs44')):
    sets[os.path.basename(os.path.dirname(e))] = e
for m in sorted(glob.glob(D + 'swap/mix/*/runs44')):
    sets['mix:' + os.path.basename(os.path.dirname(m))] = m
for m in sorted(glob.glob(OUT + 'mix/*/runs44')):
    sets['verify:' + os.path.basename(os.path.dirname(m))] = m

keys = ['PQ', 'PQ_decided', 'fp', 'fp_decided', 'matched', 'merges', 'recall', 'precision', 's0_PQ', 's0_fp', 's0_matched', 's0_merges', 's0_PQd', 's1_PQ', 's1_fp', 's1_matched', 's2_PQ']
T = {'baseline': {k: round(sum(base[g][k] for g in base) / len(base), 4) for k in keys}}
T['baseline']['n'] = len(base)
for name, d in sets.items():
    R = {g: row(b) for g, b in grid_runs(d).items()}
    if len(R) != 6: T[name] = dict(n=len(R)); continue
    t = {k: round(sum(R[g][k] for g in R) / 6, 4) for k in keys}
    for k in ('PQ', 'PQ_decided', 's0_PQ', 's0_PQd', 's1_PQ', 'fp', 'matched'):
        gains = [R[g][k] - base[g][k] for g in range(6)]
        t['gain_' + k] = round(sum(gains) / 6, 4); t['up_' + k] = sum(x > 0 for x in gains)
    t['n'] = 6
    t['area_maps'] = sorted({R[g]['area'] for g in R})[:1]
    T[name] = t
json.dump(T, open(OUT + 'runs_table.json', 'w'), indent=1)
cols = ['PQ', 'gain_PQ', 'up_PQ', 'gain_PQ_decided', 'fp', 'matched', 'merges', 's0_PQ', 'gain_s0_PQ', 'gain_s0_PQd', 's0_fp', 's0_matched', 's0_merges', 'gain_s1_PQ']
print('name'.ljust(28), ' '.join(c[:12].rjust(12) for c in cols))
for n, t in T.items():
    print(n[:28].ljust(28), ' '.join(str(t.get(c, '-'))[:12].rjust(12) for c in cols))
