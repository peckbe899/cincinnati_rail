"""critic: how big are the plate-44 gains compared with their uncertainty?

Two sources of uncertainty, both on plate 44 only:
  1. tile-grid noise: the same networks with their tile grids moved (6 equally valid grids, inference agent's maps).
     For each proposal, the paired difference against the repo's outline step on the SAME grid's maps.
  2. which blocks happen to be on the plate: a paired bootstrap over Ben's 55 blocks (resampling blocks with
     replacement, false positives held fixed), for the batch grid only.

Inputs (read-only): critic/harness/runs/{oq,nest}__GRID (from run_grid.py), inference/bench/runs/GRID (the repo's
outline step on each grid's maps, scored by the inference agent with an unchanged bench44 copy).
    python paired_stats.py  -> paired_stats.json
"""
import json, os, sys, importlib.util
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/') + '/'
B = HERE + '../'
spec = importlib.util.spec_from_file_location('b44', HERE + 'harness/bench44.py'); b44 = importlib.util.module_from_spec(spec); spec.loader.exec_module(b44)

GR1 = ['batch'] + [f'off{i}_tta1' for i in range(1, 6)]
GR8 = ['a_tta8'] + [f'off{i}_a_tta8' for i in range(1, 6)]
KEYS = ['PQ', 'matched', 'fp', 'merges', 'recall_interior', 'precision', 'precision_green', 'ben_blocks_closed', 'delete_len', 'draw_len']


def head(path):
    d = json.load(open(path)); return d['headline']


def cur(g): return head(B + f'inference/bench/runs/{g}/bench44.json')
def mine(v, g): return head(HERE + f'harness/runs/{v}__{g}/bench44.json')


def paired(base, new, label):
    out = {}
    for f in ('all', 'A', 'B'):
        for k in KEYS:
            d = np.array([n[f][k] - b[f][k] for b, n in zip(base, new)], float)
            out[f'{f}.{k}'] = dict(mean=round(float(d.mean()), 4), sd=round(float(d.std(ddof=1)), 4), min=round(float(d.min()), 4), max=round(float(d.max()), 4),
                                   gains=int((d > 0).sum()), of=len(d), base_mean=round(float(np.mean([b[f][k] for b in base])), 4), new_mean=round(float(np.mean([n[f][k] for n in new])), 4))
    print(label, {k: (v['base_mean'], v['new_mean'], v['mean'], v['sd'], f"{v['gains']}/{v['of']}") for k, v in out.items() if k.endswith(('.PQ', 'recall_interior', '.precision', 'ben_blocks_closed')) }, flush=True)
    return out


def per_block(run_dir):
    T = per_block.T
    polys = json.load(open(run_dir + 'outlines.json', encoding='utf8'))
    rings = [np.array([s['a'] for s in p], float) for p in polys]; pr = b44.raster(rings); npr = len(rings)
    res, ious = b44.pq(T, pr, npr)
    return ious, res['all']['fp'], res['all']


def boot(runs, n=4000, seed=0):
    """paired bootstrap over Ben's 55 blocks: PQ = sum(iou>0.5) / (TP + FN/2 + FP/2), FP fixed per run"""
    rng = np.random.default_rng(seed); out = {}
    I = {k: per_block(d) for k, d in runs.items()}
    for k, (iou, fp, a) in I.items(): out[k] = dict(PQ_check=a['PQ'], fp=fp)
    names = list(runs); ng = len(I[names[0]][0])
    idx = rng.integers(0, ng, size=(n, ng))
    def pqv(iou, fp, ix):
        m = iou[ix] > 0.5; tp = m.sum(1); fn = ng - tp
        return np.where(m, iou[ix], 0).sum(1) / (tp + 0.5 * fn + 0.5 * fp)
    P = {k: pqv(I[k][0], I[k][1], idx) for k in names}
    base = names[0]
    for k in names[1:]:
        d = P[k] - P[base]
        out[k].update(diff_vs_base=round(float(np.mean(d)), 4), ci95=[round(float(np.quantile(d, 0.025)), 4), round(float(np.quantile(d, 0.975)), 4)], p_le0=round(float((d <= 0).mean()), 4))
    out[base].update(PQ_ci95=[round(float(np.quantile(P[base], 0.025)), 4), round(float(np.quantile(P[base], 0.975)), 4)])
    return out


if __name__ == '__main__':
    R = {}
    base1 = [cur(g) for g in GR1]; base8 = [cur(g) for g in GR8]
    R['oq_vs_cur_tta1'] = paired(base1, [mine('oq', g) for g in GR1], 'oq vs cur, tta1 grids')
    R['nest_vs_cur_tta1'] = paired(base1, [mine('nest', g) for g in GR1], 'nest vs cur, tta1 grids')
    if all(os.path.exists(HERE + f'harness/runs/oq__{g}/bench44.json') for g in GR8):
        R['oq_vs_cur_tta8'] = paired(base8, [mine('oq', g) for g in GR8], 'oq vs cur, tta8 grids')
        R['oq_tta8_vs_cur_tta1'] = paired(base1, [mine('oq', g) for g in GR8], 'oq+tta8 vs cur tta1 (same grid offsets)')
        R['oq_tta8_vs_oq_tta1'] = paired([mine('oq', g) for g in GR1], [mine('oq', g) for g in GR8], 'tta8 gain on top of oq')
    R['tta8_vs_tta1_cur'] = paired(base1, base8, 'tta8 vs tta1, repo outline step')
    per_block.T = b44.load_truth()
    runs = {'batch': B + 'bench44/runs/batch/', 'oq': HERE + 'harness/runs/oq__batch/', 'nest': HERE + 'harness/runs/nest__batch/',
            'a_tta8': B + 'inference/bench/runs/a_tta8/', 'guided': B + 'bench44/runs/guided/'}
    if os.path.exists(HERE + 'harness/runs/oq__a_tta8/outlines.json'): runs['oq+a_tta8'] = HERE + 'harness/runs/oq__a_tta8/'
    R['block_bootstrap_batch_grid'] = boot(runs)
    print(json.dumps(R['block_bootstrap_batch_grid'], indent=1))
    json.dump(R, open(HERE + 'paired_stats.json', 'w'), indent=1)
