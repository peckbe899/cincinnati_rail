"""v-44: paired gains over the 6 tile grids, and block bootstraps of the PQ change, from the runs of run_bench.py
(all scored by the ORIGINAL harness copy, v-44/harness/bench44.py).

    python -B analyze44.py  -> v-44/analyze44.json (and a short print)

Paired: for each pair (new, old) and each headline key, new - old on the same grid; mean, sd, min, max, how many of the 6
grids gain (new > old), and a t interval of the mean (t 5 df, 95%: 2.571).
Bootstraps of the PQ change (4,000 resamples of Ben's 55 blocks, seed 0, paired: both chains see the same resample):
  fp_fixed       the false blocks held fixed (as critic/paired_stats.py)
  fp_attached    each false block goes with Ben's block whose centroid is nearest its own, so it is resampled with it
  grid_mean      the mean change over the 6 grids, the same block resample for all grids (fp_fixed); grids held fixed
  grid_and_block grids resampled too (6 of 6 with replacement), then blocks, fp_fixed
Per-block IoUs come from the harness's own pq() on each run's outlines.json (rasterised as the harness does)."""
import importlib.util, json, os, sys
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'hooks'))
from common import V, GRIDS  # noqa: E402
R = V + 'harness/runs/'
spec = importlib.util.spec_from_file_location('b44', V + 'harness/bench44.py'); b44 = importlib.util.module_from_spec(spec); spec.loader.exec_module(b44)
KEYS = ['PQ', 'matched', 'merges', 'fp', 'recall_interior', 'precision', 'precision_green', 'precision_orange', 'ben_blocks_closed', 'intact_rings', 'delete_len', 'draw_len']
T95 = 2.5706


def head(tag): return json.load(open(R + tag + '/bench44.json'))['headline']


def paired(new, old):
    out = {}
    for f in ('all', 'A', 'B'):
        for k in KEYS:
            a = np.array([head(f'{new}__{g}')[f][k] for g in GRIDS], float); b = np.array([head(f'{old}__{g}')[f][k] for g in GRIDS], float)
            if np.isnan(a).any() or np.isnan(b).any(): continue
            d = a - b; sd = float(d.std(ddof=1))
            out[f'{f}.{k}'] = dict(old_mean=round(float(b.mean()), 4), new_mean=round(float(a.mean()), 4), mean=round(float(d.mean()), 4), sd=round(sd, 4), min=round(float(d.min()), 4), max=round(float(d.max()), 4),
                                   gains=int((d > 0).sum()), losses=int((d < 0).sum()), of=len(d), t95=[round(float(d.mean() - T95 * sd / np.sqrt(len(d))), 4), round(float(d.mean() + T95 * sd / np.sqrt(len(d))), 4)],
                                   per_grid=[round(float(x), 4) for x in d])
    return out


TR = None
def blocks(tag):
    """per-GT-block IoU of the best prediction, the false predictions and each one's nearest GT block"""
    global TR
    if TR is None: TR = b44.load_truth()
    polys = json.load(open(R + tag + '/outlines.json', encoding='utf8'))
    rings = [np.array([s['a'] for s in p], float) for p in polys]; pr = b44.raster(rings); npr = len(rings)
    res, ious = b44.pq(TR, pr, npr)
    # false predictions, as pq() finds them (decided=None)
    gt, ng = TR['gt'], TR['ng']; g = gt.astype(np.int64); m = (g > 0) | (pr > 0)
    joint = np.bincount(g[m] * (npr + 1) + pr[m], minlength=(ng + 2) * (npr + 1)).reshape(ng + 2, npr + 1); ga = joint.sum(1); pa = joint.sum(0)
    matched = set()
    for i in range(1, ng + 1):
        j = int(np.argmax(joint[i, 1:])) + 1; inter = joint[i, j]
        if inter / max(1, ga[i] + pa[j] - inter) > 0.5: matched.add(j)
    ys, xs = np.nonzero(pr); lab = pr[ys, xs]; cnt = np.bincount(lab, minlength=npr + 1)
    cx = np.bincount(lab, xs, minlength=npr + 1) / np.maximum(cnt, 1) / b44.S; cy = np.bincount(lab, ys, minlength=npr + 1) / np.maximum(cnt, 1) / b44.S
    fp = [j for j in range(1, npr + 1) if j not in matched and cnt[j] > 0]
    assert len(fp) == res['all']['fp'], (tag, len(fp), res['all']['fp'])
    near = np.zeros(ng)
    for j in fp: near[int(np.argmin(np.hypot(TR['cen'][:, 0] - cx[j], TR['cen'][:, 1] - cy[j])))] += 1
    return dict(iou=ious, fp=len(fp), fp_near=near, PQ=res['all']['PQ'])


def pqv(iou, fp, ix):
    """PQ for each row of block indices ix, false blocks fp (a number or an array per row)"""
    v = iou[ix]; m = v > 0.5; tp = m.sum(1); fn = ix.shape[1] - tp
    return np.where(m, v, 0).sum(1) / (tp + 0.5 * fn + 0.5 * fp)


def interval(d): return dict(mean=round(float(d.mean()), 4), lo95=round(float(np.percentile(d, 2.5)), 4), hi95=round(float(np.percentile(d, 97.5)), 4), share_gt0=round(float((d > 0).mean()), 4))


def boot(new, old, n=4000, seed=0):
    rng = np.random.default_rng(seed); out = {}
    Bn = {g: blocks(f'{new}__{g}') for g in GRIDS}; Bo = {g: blocks(f'{old}__{g}') for g in GRIDS}
    for g in GRIDS:                                    # the bootstrap's PQ formula gives the harness's PQ
        for B in (Bn[g], Bo[g]): assert abs(pqv(B['iou'], B['fp'], np.arange(55)[None])[0] - B['PQ']) < 6e-5
    ng = 55; ix = rng.integers(0, ng, size=(n, ng))
    a, b = Bn['batch'], Bo['batch']
    out['batch_grid'] = dict(new_PQ=a['PQ'], old_PQ=b['PQ'], change=round(a['PQ'] - b['PQ'], 4),
                             fp_fixed=interval(pqv(a['iou'], a['fp'], ix) - pqv(b['iou'], b['fp'], ix)),
                             fp_attached=interval(pqv(a['iou'], a['fp_near'][ix].sum(1), ix) - pqv(b['iou'], b['fp_near'][ix].sum(1), ix)),
                             old_PQ_interval=interval(pqv(b['iou'], b['fp'], ix)), new_PQ_interval=interval(pqv(a['iou'], a['fp'], ix)))
    D = np.stack([pqv(Bn[g]['iou'], Bn[g]['fp'], ix) - pqv(Bo[g]['iou'], Bo[g]['fp'], ix) for g in GRIDS])   # grids x resamples
    Da = np.stack([pqv(Bn[g]['iou'], Bn[g]['fp_near'][ix].sum(1), ix) - pqv(Bo[g]['iou'], Bo[g]['fp_near'][ix].sum(1), ix) for g in GRIDS])
    out['grid_mean'] = dict(change=round(float(np.mean([Bn[g]['PQ'] - Bo[g]['PQ'] for g in GRIDS])), 4), fp_fixed=interval(D.mean(0)), fp_attached=interval(Da.mean(0)))
    gi = rng.integers(0, len(GRIDS), size=(n, len(GRIDS)))
    out['grid_and_block'] = dict(fp_fixed=interval(D[gi, np.arange(n)[:, None]].mean(1)))
    return out


if __name__ == '__main__':
    have = lambda c: all(os.path.exists(R + f'{c}__{g}/bench44.json') for g in GRIDS)
    res = dict(meta=dict(grids=GRIDS, harness=V + 'harness/bench44.py (cmp-identical to bench44/bench44.py)', runs=R), headline_batch={}, paired={}, bootstrap={})
    for t in sorted(os.listdir(R)):
        if t.endswith('__batch') or t.endswith('__guided'):
            if os.path.exists(R + t + '/bench44.json'): res['headline_batch'][t] = head(t)
    pairs = [('merged', 'base'), ('A', 'base'), ('merged', 'A'), ('noholes', 'merged'), ('norail', 'merged'), ('railshow', 'merged'), ('railrule', 'merged'), ('keepunl', 'merged'), ('noholes', 'A'), ('norail', 'A'), ('railrule', 'A')]
    for n_, o_ in pairs:
        if have(n_) and have(o_): res['paired'][f'{n_}-{o_}'] = paired(n_, o_)
    for n_, o_ in (('merged', 'base'), ('A', 'base'), ('merged', 'A'), ('railrule', 'base')):
        if have(n_) and have(o_): res['bootstrap'][f'{n_}-{o_}'] = boot(n_, o_)
    json.dump(res, open(V + 'analyze44.json', 'w'), indent=1)
    for p, d in res['paired'].items():
        print(p, {k: (d[k]['old_mean'], d[k]['new_mean'], d[k]['mean'], d[k]['sd'], f"{d[k]['gains']}/{d[k]['losses']}/{d[k]['of']}") for k in ('all.PQ', 'A.PQ', 'B.PQ', 'all.recall_interior', 'all.precision', 'all.precision_green', 'all.ben_blocks_closed', 'all.delete_len', 'all.draw_len')})
    for p, d in res['bootstrap'].items(): print(p, json.dumps(d))
