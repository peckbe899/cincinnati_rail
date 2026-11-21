"""verify-inference: grid statistics of my own rescoring (rescore.json + bench/runs/batch), computed independently of
the inference agent's noise_floor.py. For the batch settings (tta1) and area TTA x8 on the 6 tile grids: mean, sd,
paired gain, how many grids gain, a paired t value and an exact sign-flip (permutation) p value over the 6 grids.
Also the same for fold A and fold B. Writes grid_stats.json.

    python verify_grid_stats.py
"""
import itertools, json
import numpy as np
V = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-21/verify-inference/'
R = json.load(open(V + 'rescore.json')); R['batch'] = json.load(open(V + 'bench/runs/batch/bench44.json'))['headline']
T1 = ['batch'] + [f'inf_off{i}_tta1' for i in range(1, 6)]; T8 = ['inf_a_tta8'] + [f'inf_off{i}_a_tta8' for i in range(1, 6)]
if 'p_tta8_cpu' in R: print('CPU-made TTA x8 maps (batch grid):', R['p_tta8_cpu']['all']['PQ'])
out = {}
for f, k in (('all', 'PQ'), ('A', 'PQ'), ('B', 'PQ'), ('all', 'PQ_decided'), ('all', 'recall_interior'), ('all', 'precision'), ('all', 'matched'), ('all', 'merges'), ('all', 'fp')):
    a = np.array([R[n][f][k] for n in T1], float); b = np.array([R[n][f][k] for n in T8], float); d = b - a
    t = d.mean() / (d.std(ddof=1) / np.sqrt(len(d))) if d.std(ddof=1) > 0 else float('inf')
    flips = [np.mean(d * np.array(s)) for s in itertools.product((1, -1), repeat=len(d))]
    p = float(np.mean([x >= d.mean() - 1e-12 for x in flips]))
    out[f'{f}.{k}'] = dict(tta1_mean=round(a.mean(), 4), tta1_sd=round(a.std(ddof=1), 4), tta8_mean=round(b.mean(), 4), tta8_sd=round(b.std(ddof=1), 4),
                           paired_mean=round(d.mean(), 4), paired_sd=round(d.std(ddof=1), 4), gains=int((d > 0).sum()), of=len(d), paired_t=round(float(t), 2),
                           sign_flip_p_one_sided=round(p, 4), diffs=[round(x, 4) for x in d])
    print(f'{f:3s} {k:16s} tta1 {a.mean():.4f} (sd {a.std(ddof=1):.4f})  tta8 {b.mean():.4f} (sd {b.std(ddof=1):.4f})  paired {d.mean():+.4f} sd {d.std(ddof=1):.4f}  '
          f'gains {(d > 0).sum()}/6  t {t:.2f}  p {p:.3f}  diffs {np.round(d, 4).tolist()}')
json.dump(out, open(V + 'grid_stats.json', 'w'), indent=1)
