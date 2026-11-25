"""ink_states.py (text/effect, 25 Nov 2026): how the outline step's side states change when text is taken out of its ink
test (bench CHAIN__MASK__ink against the chain's stored run), grid by grid: counts of each state (not paper_edge, not
short) and the summed side length per state.
    cd data/sanborn; python -B bench_2026-11-25/text/effect/code/ink_states.py CHAIN MASK      -> scores/ink_states_<CHAIN>_<MASK>.json"""
import json, os, sys
from collections import Counter
import numpy as np
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; E = SP + 'bench_2026-11-25/text/effect/'
chain, mask = sys.argv[1:3]
ST = SP + 'bench_2026-11-25/diag/swap/runs_baseline44/base__grid{g}/' if chain == 'base' else SP + f'train_v2_runs/eval/{chain}/runs44/v2__grid{{g}}/'
def states(f):
    c, L = Counter(), Counter()
    for p in json.load(open(f, encoding='utf8')):
        for s in p:
            if s.get('paper_edge') or s['state'] == 'short': continue
            c[s['state']] += 1; L[s['state']] += float(np.hypot(s['b'][0] - s['a'][0], s['b'][1] - s['a'][1]))
    return c, L
out = {}
for g in range(6):
    a, la = states(ST.format(g=g) + 'outlines.json'); b, lb = states(E + f'bench/{chain}__{mask}__ink/runs44/v2__grid{g}/outlines.json')
    out[g] = {k: dict(stored=a[k], masked=b[k], stored_len=round(la[k]), masked_len=round(lb[k])) for k in sorted(set(a) | set(b))}
print(json.dumps({k: (round(np.mean([out[g][k]['stored'] for g in out if k in out[g]]), 1), round(np.mean([out[g][k]['masked'] for g in out if k in out[g]]), 1)) for k in out[0]}))
json.dump(out, open(E + f'scores/ink_states_{chain}_{mask}.json', 'w'), indent=1)
