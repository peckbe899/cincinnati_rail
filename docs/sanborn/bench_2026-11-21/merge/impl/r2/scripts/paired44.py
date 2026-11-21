"""merge/impl/r2: paired gains over the 6 tile grids of plate 44 (21 Nov 2026), as critic/paired_stats.py.

Inputs (read only):
  new      merge/impl/r2/bench44_runs/TAG__gridK/bench44.json       (staged bench44.py --grids staged/data/sanborn/bench44_maps)
  repo     bench_2026-11-21/inference/bench/runs/NAME/bench44.json  (the repo's outline step + step 4 on the same maps)
  A        bench_2026-11-21/critic/harness/runs/oq__NAME/bench44.json (outline-quality alone, its step 4)
  round1   merge/impl/bench44_runs/merged__gridK/bench44.json        (the first staged merge)
  OTHER    with a second argument: merge/impl/r2/bench44_runs/OTHER__gridK/bench44.json
gridK = NAME: grid0 batch, grid1..5 off1_tta1..off5_tta1 (bench44_maps/gridK/info.json says so; the PNGs are byte-identical copies).
    python -B paired44.py TAG [OTHER]  -> merge/impl/r2/paired44_TAG.json
'intact_rings' of the repo, A and round-1 runs were counted by the old rule (a ring is intact unless a side is short or
paper_edge), which overcounts for a step 4 that drops more; it is left out of the comparison.
"""
import json, sys
import numpy as np
import common as C
B = C.DATA + 'bench_2026-11-21/'; TAG = sys.argv[1]; OTHER = sys.argv[2] if len(sys.argv) > 2 else None
NAMES = ['batch'] + [f'off{i}_tta1' for i in range(1, 6)]
KEYS = ['PQ', 'matched', 'fp', 'merges', 'recall_interior', 'precision', 'precision_green', 'ben_blocks_closed', 'delete_len', 'draw_len']
for k, n in enumerate(NAMES):
    assert json.load(open(C.STAGED + f'data/sanborn/bench44_maps/grid{k}/info.json'))['name'] == n
head = lambda p: json.load(open(p))['headline']
M = [head(C.IMPL + f'bench44_runs/{TAG}__grid{k}/bench44.json') for k in range(6)]
R = [head(B + f'inference/bench/runs/{n}/bench44.json') for n in NAMES]
A = [head(B + f'critic/harness/runs/oq__{n}/bench44.json') for n in NAMES]
R1 = [head(C.IMPL1 + f'bench44_runs/merged__grid{k}/bench44.json') for k in range(6)]
O = [head(C.IMPL + f'bench44_runs/{OTHER}__grid{k}/bench44.json') for k in range(6)] if OTHER else None


def paired(base, new):
    out = {}
    for f in ('all', 'A', 'B'):
        for k in KEYS:
            d = np.array([n[f][k] - b[f][k] for b, n in zip(base, new)], float); m = len(d); se = d.std(ddof=1) / np.sqrt(m)
            out[f'{f}.{k}'] = dict(base_mean=round(float(np.mean([b[f][k] for b in base])), 4), new_mean=round(float(np.mean([n[f][k] for n in new])), 4), new_sd_over_grids=round(float(np.std([n[f][k] for n in new], ddof=1)), 4),
                                   mean=round(float(d.mean()), 4), sd=round(float(d.std(ddof=1)), 4), min=round(float(d.min()), 4), max=round(float(d.max()), 4), gains=int((d > 0).sum()), losses=int((d < 0).sum()), of=m,
                                   t95=[round(float(d.mean() - 2.571 * se), 4), round(float(d.mean() + 2.571 * se), 4)])
    return out


res = dict(vs_repo=paired(R, M), vs_A=paired(A, M), vs_round1=paired(R1, M), **({f'vs_{OTHER}': paired(O, M)} if O else {}), per_grid={k: M[k]['all'] for k in range(6)})
for name, d in res.items():
    if name == 'per_grid': continue
    print(name)
    for k in ('all.PQ', 'A.PQ', 'B.PQ', 'all.recall_interior', 'A.recall_interior', 'B.recall_interior', 'all.precision', 'all.precision_green', 'all.fp', 'all.matched', 'all.ben_blocks_closed', 'all.delete_len', 'all.draw_len'):
        v = d[k]; print(f'   {k:22s} {v["base_mean"]:>10} -> {v["new_mean"]:>10}  gain {v["mean"]:+.4f} sd {v["sd"]:.4f}  [{v["min"]:+.4f}, {v["max"]:+.4f}]  up {v["gains"]} down {v["losses"]} of {v["of"]}  t95 {v["t95"]}')
json.dump(res, open(C.IMPL + f'paired44_{TAG}.json', 'w'), indent=1)
