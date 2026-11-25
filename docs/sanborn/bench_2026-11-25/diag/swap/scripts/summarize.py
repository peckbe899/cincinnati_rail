"""summarize.py (diag/swap, 25 Nov 2026): one table of every plate-44 evaluation (6 tile grids, merged outline step),
paired with the baseline (area_ng1 + lines_ng1) grid by grid, and the 1A validation region where there is one.
Reads train_v2_runs/eval/<STEP>/eval_v2.json, diag/swap/eval/*/eval_v2.json and diag/swap/mix/*/runs44/v2_grids.json.
Writes diag/swap/summary.json and summary.md. System python.
"""
import json, os, glob
import numpy as np
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
D = SP + 'bench_2026-11-25/diag/swap/'
STEPS = ('V1S1', 'V1S2', 'V2S1', 'V2S2')
K = ('PQ', 'recall_interior', 'precision', 'merges', 'fp', 'PQ_decided', 'matched', 'ben_blocks_closed')


def from_grids(G):
    h = G['headline']['all']; p = (G.get('paired') or {}).get('all', {})
    return {k: dict(mean=h[k]['mean'], sd=h[k]['sd'], gain=p.get(k, {}).get('mean'), up=p.get(k, {}).get('gains'), of=p.get(k, {}).get('of')) for k in K if k in h}


def load():
    R = {}
    def add(code, label, how, g, e=None):
        R[code] = dict(label=label, how=how, b44=from_grids(g))
        if e and 'bench1A' in e:
            r = e['bench1A']['v2']['region']; R[code]['r1A'] = {k: r.get(k) for k in ('PQ', 'recall_interior', 'precision', 'matched', 'merges', 'fp')}
            R[code]['r1A_batch'] = {k: e['bench1A']['batch_ng1']['region'].get(k) for k in ('PQ', 'recall_interior', 'precision')}
        if e: R[code]['models'] = {k: os.path.basename(v['file']) for k, v in e['models'].items()}
    for s in STEPS:
        e = json.load(open(SP + f'train_v2_runs/eval/{s}/eval_v2.json', encoding='utf8'))
        add(f'{s}:111', f'{s} pair (area {s} best + lines {s} best)', 'run 24 Nov (train_v2_runs/eval)', json.load(open(SP + f'train_v2_runs/eval/{s}/runs44/v2_grids.json', encoding='utf8')), e)
    for f in sorted(glob.glob(D + 'eval/*/eval_v2.json')):
        n = os.path.basename(os.path.dirname(f)); e = json.load(open(f, encoding='utf8'))
        g = json.load(open(os.path.dirname(f) + '/runs44/v2_grids.json', encoding='utf8'))
        add(n, f"area {e['models']['area']['file'].split(os.sep)[-1]} + lines {e['models']['lines']['file'].split(os.sep)[-1]}", 'eval_v2 (GPU), diag/swap/eval', g, e)
    for f in sorted(glob.glob(D + 'mix/*/runs44/v2_grids.json')):
        n = os.path.basename(os.path.dirname(os.path.dirname(f)))
        add('mix:' + n, n, 'mixed maps, bench44 --grids (no GPU), diag/swap/mix', json.load(open(f, encoding='utf8')))
    return R


def main():
    R = load(); json.dump(R, open(D + 'summary.json', 'w'), indent=1)
    L = ['| code | what | 44 PQ (sd) | paired gain PQ (grids up) | recall | precision | merges | false blocks | PQ decided (gain) | 1A region PQ |', '|---|---|---|---|---|---|---|---|---|---|']
    for c, r in R.items():
        b = r['b44']; f = lambda k, d=3: f"{b[k]['mean']:.{d}f}" if k in b else '-'
        g = lambda k, d=3: (f"{b[k]['gain']:+.{d}f}" if b.get(k, {}).get('gain') is not None else '-')
        L.append(f"| {c} | {r['label']} | {f('PQ')} ({b['PQ']['sd']:.3f}) | {g('PQ')} ({b['PQ']['up']}/{b['PQ']['of']}) | {f('recall_interior')} ({g('recall_interior')}) | {f('precision')} ({g('precision')}) | {f('merges',1)} ({g('merges',1)}) | {f('fp',1)} ({g('fp',1)}) | {f('PQ_decided')} ({g('PQ_decided')}) | {r.get('r1A', {}).get('PQ', '-')} |")
    open(D + 'summary.md', 'w', encoding='utf8').write('\n'.join(L) + '\n'); print('\n'.join(L))


if __name__ == '__main__':
    main()
