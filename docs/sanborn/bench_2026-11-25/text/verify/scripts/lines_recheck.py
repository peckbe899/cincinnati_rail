"""verify (25 Nov 2026): plate-44 editor lines of masked bench runs against each chain's stored run (no mask), my own code,
same definitions as effect/code/lines_score.py: shown lines (44_shown.json less state 'sheet') sampled every 1 px; false
length = samples more than 5 px from Ben's street-map lines (all kinds); a Ben line is found when 50% of its samples are
within 5 px of a shown line; lost / gained against the stored run on the same grid.

    cd data/sanborn; python -B bench_2026-11-25/text/verify/scripts/lines_recheck.py
Runs scored: verify/bench/*__F__* (finder mask, no truth) and, for comparison, effect/bench/*__I2__* and *__B2L__*.
Writes verify/out/lines_recheck.json."""
import json, os, glob
import numpy as np
from scipy.spatial import cKDTree
SP = os.getcwd() + '/'; V = SP + 'bench_2026-11-25/text/verify/'; E = SP + 'bench_2026-11-25/text/effect/'
STORED = {'base': SP + 'bench_2026-11-25/diag/swap/runs_baseline44/base__grid{g}/'}
for s in ('V1S1', 'V1S2', 'V2S1', 'V2S2'): STORED[s] = SP + f'train_v2_runs/eval/{s}/runs44/v2__grid{{g}}/'


def samples(lines):
    P, I = [], []
    for k, e in enumerate(lines):
        a, b = np.array(e['a'], float), np.array(e['b'], float); n = max(1, int(np.ceil(np.hypot(*(b - a)))))
        t = (np.arange(n) + 0.5) / n; P.append(a[None] + t[:, None] * (b - a)[None]); I.append(np.full(n, k))
    return (np.concatenate(P), np.concatenate(I)) if P else (np.zeros((0, 2)), np.zeros(0, int))


BL = json.load(open(SP + 'streetmap/22-44.json', encoding='utf8'))['lines']; BP, BI = samples(BL); BT = cKDTree(BP); blen = np.bincount(BI, minlength=len(BL))


def run(rd):
    sh = [e for e in json.load(open(rd + '44_shown.json', encoding='utf8')) if e.get('state') != 'sheet']
    P, I = samples(sh); d, _ = BT.query(P); n = len(sh); L = np.bincount(I, minlength=n).astype(float)
    fl = (np.bincount(I, d <= 8, n) / np.maximum(L, 1)) < 0.2
    dd, _ = cKDTree(P).query(BP); found = (np.bincount(BI, dd <= 5, len(BL)) / np.maximum(blen, 1)) >= 0.5
    return dict(false_len=int((d > 5).sum()), false_lines=int(fl.sum())), found


out = {}
names = sorted(glob.glob(V + 'bench/*__F__*/')) + sorted(glob.glob(E + 'bench/*__I2__*/')) + sorted(glob.glob(E + 'bench/*__B2L__*/'))
for rd in names:
    name = os.path.basename(os.path.normpath(rd)); c = name.split('__')[0]; rows = []
    for g in range(6):
        s0, f0 = run(STORED[c].format(g=g)); s1, f1 = run(rd + f'runs44/v2__grid{g}/')
        rows.append(dict(false_len0=s0['false_len'], false_len1=s1['false_len'], false_lines0=s0['false_lines'], false_lines1=s1['false_lines'],
                         lost=int((f0 & ~f1).sum()), gained=int((~f0 & f1).sum()), found0=int(f0.sum()), found1=int(f1.sum())))
    m = {k: round(float(np.mean([r[k] for r in rows])), 1) for k in rows[0]}
    out[('verify:' if rd.startswith(V) else 'effect:') + name] = dict(per_grid=rows, mean=m)
    print(f"{('verify ' if rd.startswith(V) else 'effect ') + name:24s} false length {m['false_len0']:.0f} -> {m['false_len1']:.0f} | false lines {m['false_lines0']} -> {m['false_lines1']} | Ben lines found {m['found0']} -> {m['found1']} (lost {m['lost']}, gained {m['gained']})", flush=True)
json.dump(out, open(V + 'out/lines_recheck.json', 'w'), indent=1)
