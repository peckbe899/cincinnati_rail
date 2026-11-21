"""v-final: plate 44 over the 6 tile grids, paired gains (merged - repo step on the same grid). All runs made in this check:
  base   v-final/orig/runs/base__gridK    original harness, repo outline step + repo step 4
  orig   v-final/orig/runs/merged__gridK  original harness, applied merged outlines.py + applied step 4 (hooks)
  staged v-final/staged_runs/staged__gridK  the staged (applied) bench44.py, its own defaults
Also: per-grid identity of orig vs staged outlines/edges, and both against the implementer's merge/impl/r2/bench44_runs/final__gridK.
    python -B paired.py -> v-final/paired.json"""
import json, filecmp
import numpy as np
V = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-21/merge/v-final/'; IM = V + '../impl/r2/bench44_runs/'
KEYS = ['PQ', 'matched', 'merges', 'fp', 'recall_interior', 'precision', 'precision_green', 'precision_orange', 'ben_blocks_closed', 'intact_rings', 'delete_len', 'draw_len']
H = lambda p: json.load(open(p))['headline']
base = [H(V + f'orig/runs/base__grid{k}/bench44.json') for k in range(6)]; orig = [H(V + f'orig/runs/merged__grid{k}/bench44.json') for k in range(6)]; stg = [H(V + f'staged_runs/staged__grid{k}/bench44.json') for k in range(6)]
def paired(b, n):
    out = {}
    for f in ('all', 'A', 'B'):
        for k in KEYS:
            d = np.array([y[f][k] - x[f][k] for x, y in zip(b, n)], float); se = d.std(ddof=1) / np.sqrt(6)
            out[f'{f}.{k}'] = dict(base_mean=round(float(np.mean([x[f][k] for x in b])), 4), new_mean=round(float(np.mean([y[f][k] for y in n])), 4), new_sd=round(float(np.std([y[f][k] for y in n], ddof=1)), 4),
                                   gain_mean=round(float(d.mean()), 4), gain_sd=round(float(d.std(ddof=1)), 4), gains=int((d > 0).sum()), losses=int((d < 0).sum()), t95=[round(float(d.mean() - 2.571 * se), 4), round(float(d.mean() + 2.571 * se), 4)])
    return out
same = {}
for k in range(6):
    o, s, i = V + f'orig/runs/merged__grid{k}/', V + f'staged_runs/staged__grid{k}/', IM + f'final__grid{k}/'
    same[f'grid{k}'] = dict(orig_vs_staged_outlines=filecmp.cmp(o + 'outlines.json', s + 'outlines.json', False), orig_vs_staged_edges=filecmp.cmp(o + '44_edges.json', s + '44_edges.json', False),
                            orig_vs_staged_shown=filecmp.cmp(o + '44_shown.json', s + '44_shown.json', False), staged_vs_impl_outlines=filecmp.cmp(s + 'outlines.json', i + 'outlines.json', False),
                            staged_vs_impl_bench=json.load(open(s + 'bench44.json'))['headline'] == json.load(open(i + 'bench44.json'))['headline'],
                            orig_vs_staged_headline_differs={f: {kk: (orig[k][f][kk], stg[k][f][kk]) for kk in orig[k][f] if orig[k][f][kk] != stg[k][f][kk]} for f in ('all',)})
res = dict(base_vs_orig=paired(base, orig), base_vs_staged=paired(base, stg), identity=same,
           grid0=dict(base=base[0], orig=orig[0], staged=stg[0]))
json.dump(res, open(V + 'paired.json', 'w'), indent=1)
for name in ('base_vs_orig', 'base_vs_staged'):
    print(name)
    for k in ('all.PQ', 'A.PQ', 'B.PQ', 'all.recall_interior', 'A.recall_interior', 'B.recall_interior', 'all.precision', 'all.precision_green', 'all.matched', 'all.fp', 'all.ben_blocks_closed', 'all.intact_rings', 'all.delete_len', 'all.draw_len'):
        r = res[name][k]; print(f'  {k:22s} base {r["base_mean"]:>10} new {r["new_mean"]:>10} (sd {r["new_sd"]}) gain {r["gain_mean"]:>9} sd {r["gain_sd"]:>8} up {r["gains"]}/6 down {r["losses"]} t95 {r["t95"]}')
for g, v in same.items(): print(g, v)
