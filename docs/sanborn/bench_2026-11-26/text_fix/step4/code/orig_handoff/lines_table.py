"""lines_table.py (text_v1/handoff, 26 Nov 2026): the line bench before and after the mask, in one table.
    cd data/sanborn; python -B bench_2026-11-25/text_v1/handoff/code/lines_table.py
Plate 44: bench44.py --grids paired gains (the masked run minus the control run, grid by grid, over the 6 tile grids), for
every config in runs/bench44/; the controls are paired with the stored runs (they must be 0 everywhere).
Plates 5 and 1A: bench_plate.py headline (1A: region = train_v2/1A/valmask.png, and the whole plate), masked minus control.
'worse' lists every score that got worse on any grid / plate, with the worst change. Higher is better for PQ, SQ, RQ,
matched, PQ_decided, recall_interior, precision*, ben_blocks_closed, intact_rings; lower for fp, fp_decided, merges,
gt_split, delete_len, draw_len. Writes handoff/scores/lines_bench.json and lines_bench.txt."""
import json, os
SP = os.getcwd().replace('\\', '/') + '/'; HO = SP + 'bench_2026-11-25/text_v1/handoff/'
LOWER = {'fp', 'fp_decided', 'merges', 'gt_split', 'delete_len', 'draw_len'}
KEYS = ('PQ', 'PQ_decided', 'matched', 'fp', 'merges', 'recall_interior', 'precision', 'precision_green', 'precision_orange', 'ben_blocks_closed', 'intact_rings', 'delete_len', 'draw_len')
def worse(k, d): return (d > 1e-9) if k in LOWER else (d < -1e-9)
out = {}; L = []
for cfg in ('control', 'ink', 'inkdrop', 'states', 'states0', 'V2S1_control', 'V2S1_inkdrop', 'V2S1_states'):
    f = HO + f'runs/bench44/{cfg}/runs44/v2_grids.json'
    if not os.path.exists(f): continue
    r = json.load(open(f, encoding='utf8')); p = r['paired']['all']; h = r['headline']['all']
    o = dict(paired_with=r['meta']['paired_with'], mean={k: h[k]['mean'] for k in KEYS}, gain={k: dict(mean=p[k]['mean'], min=p[k]['min'], max=p[k]['max'], better=sum(1 for g in r['per_grid'] if 0), gains=p[k]['gains']) for k in KEYS})
    W = {}
    for k in KEYS:
        bad = p[k]['max'] if k in LOWER else p[k]['min']
        if worse(k, bad): W[k] = bad
    o['worse_on_some_grid'] = W; out[f'44:{cfg}'] = o
    L.append(f"44 {cfg:13s} " + ' | '.join(f"{k} {p[k]['mean']:+.4g} ({p[k]['gains']}/6 up)" for k in ('PQ', 'precision', 'recall_interior', 'precision_green', 'precision_orange', 'ben_blocks_closed', 'intact_rings', 'delete_len', 'draw_len')))
    L.append(f"   {'':13s} worse on some grid: {W if W else 'nothing'}")
for N, folds in (('5', ('all',)), ('1A', ('region', 'all'))):
    c0 = HO + f'runs/plates/{N}_control/bench_plate.json'
    if not os.path.exists(c0): continue
    C = json.load(open(c0, encoding='utf8'))['region_headline']
    for cfg in ('ink', 'inkdrop', 'states', 'states0'):
        f = HO + f'runs/plates/{N}_{cfg}/bench_plate.json'
        if not os.path.exists(f): continue
        X = json.load(open(f, encoding='utf8'))['region_headline']
        for fo in folds:
            d = {k: round(X[fo][k] - C[fo][k], 4) for k in KEYS}; W = {k: v for k, v in d.items() if worse(k, v)}
            out[f'{N}:{fo}:{cfg}'] = dict(control={k: C[fo][k] for k in KEYS}, masked={k: X[fo][k] for k in KEYS}, change=d, worse=W)
            L.append(f"{N} {fo:6s} {cfg:8s} " + ' | '.join(f'{k} {d[k]:+.4g}' for k in ('PQ', 'precision', 'recall_interior', 'precision_green', 'precision_orange', 'ben_blocks_closed', 'intact_rings', 'delete_len', 'draw_len')))
            L.append(f"   {'':15s} worse: {W if W else 'nothing'}")
json.dump(out, open(HO + 'scores/lines_bench.json', 'w', encoding='utf8', newline='\n'), indent=1)
open(HO + 'scores/lines_bench.txt', 'w', encoding='utf8', newline='\n').write('\n'.join(L) + '\n'); print('\n'.join(L))
