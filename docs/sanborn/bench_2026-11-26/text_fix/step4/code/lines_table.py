"""lines_table.py (text_fix/step4, 27 Nov 2026): copy of text_v1/handoff/code/lines_table.py for both mask sets, plus the
direct finder4-minus-finder3 change. The line bench before and after the mask, in one table.
    cd data/sanborn; python -B bench_2026-11-26/text_fix/step4/code/lines_table.py
Plate 44: bench44.py --grids paired gains (masked run minus the control run, grid by grid, over the 6 tile grids); the
control is paired with the stored baseline runs (must be 0 everywhere). 'f4-f3': the f4 run minus the f3 run, grid by
grid, from the per-grid scores.
Plates 5 and 1A: bench_plate.py headline (1A: region = train_v2/1A/valmask.png, and the whole plate), masked minus control,
and f4 minus f3.
'worse' lists every score that got worse on any grid / plate, with the worst change. Higher is better for PQ, SQ, RQ,
matched, PQ_decided, recall_interior, precision*, ben_blocks_closed, intact_rings; lower for fp, fp_decided, merges,
gt_split, delete_len, draw_len. Writes step4/scores/lines_bench.json and lines_bench.txt."""
import json, os
SP = os.getcwd().replace('\\', '/') + '/'; ST = SP + 'bench_2026-11-26/text_fix/step4/'
LOWER = {'fp', 'fp_decided', 'merges', 'gt_split', 'delete_len', 'draw_len'}
KEYS = ('PQ', 'PQ_decided', 'matched', 'fp', 'merges', 'recall_interior', 'precision', 'precision_green', 'precision_orange', 'ben_blocks_closed', 'intact_rings', 'delete_len', 'draw_len')
SHOW = ('PQ', 'precision', 'recall_interior', 'precision_green', 'precision_orange', 'ben_blocks_closed', 'intact_rings', 'delete_len', 'draw_len')
def worse(k, d): return (d > 1e-9) if k in LOWER else (d < -1e-9)
def up(k, d): return (d < -1e-9) if k in LOWER else (d > 1e-9)
out = {}; L = []
G = {}
for cfg in ('control', 'f3_ink', 'f3_states0', 'f4_ink', 'f4_states0'):
    f = ST + f'runs/bench44/{cfg}/runs44/v2_grids.json'
    if not os.path.exists(f): continue
    r = json.load(open(f, encoding='utf8')); G[cfg] = r; p = r['paired']['all']; h = r['headline']['all']
    o = dict(paired_with=r['meta']['paired_with'], mean={k: h[k]['mean'] for k in KEYS}, gain={k: dict(mean=p[k]['mean'], min=p[k]['min'], max=p[k]['max'], gains=p[k]['gains']) for k in KEYS})
    W = {}
    for k in KEYS:
        bad = p[k]['max'] if k in LOWER else p[k]['min']
        if worse(k, bad): W[k] = bad
    o['worse_on_some_grid'] = W; out[f'44:{cfg}'] = o
    L.append(f"44 {cfg:13s} vs {'stored' if cfg == 'control' else 'control'}: " + ' | '.join(f"{k} {p[k]['mean']:+.4g} ({p[k]['gains']}/6 up)" for k in SHOW))
    L.append(f"   {'':13s} worse on some grid: {W if W else 'nothing'}")
for v in ('ink', 'states0'):
    a, b = G.get(f'f3_{v}'), G.get(f'f4_{v}')
    if not (a and b): continue
    grids = sorted(a['per_grid']); D = {k: [round(b['per_grid'][g]['all'][k] - a['per_grid'][g]['all'][k], 4) for g in grids] for k in KEYS}
    W = {k: (max(d) if k in LOWER else min(d)) for k, d in D.items() if any(worse(k, x) for x in d)}
    out[f'44:f4-f3:{v}'] = dict(per_grid=D, worse_on_some_grid=W)
    L.append(f"44 f4-f3 {v:7s} per grid: " + ' | '.join(f"{k} {sum(D[k]) / len(D[k]):+.4g} ({sum(up(k, x) for x in D[k])} up, {sum(worse(k, x) for x in D[k])} down)" for k in SHOW))
    L.append(f"   {'':13s} worse on some grid: {W if W else 'nothing'} | per grid: " + '; '.join(f'{k} {D[k]}' for k in W))
for N, folds in (('5', ('all',)), ('1A', ('region', 'all'))):
    c0 = ST + f'runs/plates/{N}_control/bench_plate.json'
    if not os.path.exists(c0): continue
    C = json.load(open(c0, encoding='utf8'))['region_headline']; X = {}
    for cfg in ('f3_ink', 'f3_states0', 'f4_ink', 'f4_states0'):
        f = ST + f'runs/plates/{N}_{cfg}/bench_plate.json'
        if not os.path.exists(f): continue
        X[cfg] = json.load(open(f, encoding='utf8'))['region_headline']
        for fo in folds:
            d = {k: round(X[cfg][fo][k] - C[fo][k], 4) for k in KEYS}; W = {k: v for k, v in d.items() if worse(k, v)}
            out[f'{N}:{fo}:{cfg}'] = dict(control={k: C[fo][k] for k in KEYS}, masked={k: X[cfg][fo][k] for k in KEYS}, change=d, worse=W)
            L.append(f"{N} {fo:6s} {cfg:10s} " + ' | '.join(f'{k} {d[k]:+.4g}' for k in SHOW))
            L.append(f"   {'':17s} worse: {W if W else 'nothing'}")
    for v in ('ink', 'states0'):
        if f'f3_{v}' in X and f'f4_{v}' in X:
            for fo in folds:
                d = {k: round(X[f'f4_{v}'][fo][k] - X[f'f3_{v}'][fo][k], 4) for k in KEYS}; W = {k: x for k, x in d.items() if worse(k, x)}
                out[f'{N}:{fo}:f4-f3:{v}'] = dict(change=d, worse=W)
                L.append(f"{N} {fo:6s} f4-f3 {v:7s} " + ' | '.join(f'{k} {d[k]:+.4g}' for k in SHOW))
                L.append(f"   {'':17s} worse: {W if W else 'nothing'}")
json.dump(out, open(ST + 'scores/lines_bench.json', 'w', encoding='utf8', newline='\n'), indent=1)
open(ST + 'scores/lines_bench.txt', 'w', encoding='utf8', newline='\n').write('\n'.join(L) + '\n'); print('\n'.join(L))
