"""How much of a plate-44 score is the tile grid? Mean, spread and paired gains over 6 equally valid tile grids.

    python noise_floor.py            (reads summary44.json from run_bench44.py; writes noise_floor.json)

Grids: the batch's own (offset 0: variants batch, a_tta4, a_tta8, a_hann) and off1..off5 (make_maps44.py OFFS: both
networks' tile grids moved). For each setting (tta1 = the batch's settings, a_tta4, a_tta8, a_hann) the 6 runs give the
mean and the range of every headline number; 'paired' is setting minus tta1 on the same grid.
"""
import json, os
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)) + '/'
S = json.load(open(HERE + 'summary44.json'))
SET = {'tta1': ['batch'] + [f'off{i}_tta1' for i in range(1, 6)], 'a_tta4': ['a_tta4'] + [f'off{i}_a_tta4' for i in range(1, 6)],
       'a_tta8': ['a_tta8'] + [f'off{i}_a_tta8' for i in range(1, 6)], 'a_hann': ['a_hann'] + [f'off{i}_a_hann' for i in range(1, 6)]}
KEYS = [('all', 'PQ'), ('A', 'PQ'), ('B', 'PQ'), ('all', 'PQ_decided'), ('all', 'matched'), ('all', 'merges'), ('all', 'fp'), ('all', 'recall_interior'), ('all', 'precision'),
        ('all', 'precision_green'), ('all', 'delete_len'), ('all', 'draw_len')]
out = {}
for s, names in SET.items():
    r = {}
    for f, k in KEYS:
        v = np.array([S[n][f][k] for n in names], float); base = np.array([S[n][f][k] for n in SET['tta1']], float)
        r[f'{f}.{k}'] = dict(mean=round(float(v.mean()), 4), sd=round(float(v.std(ddof=1)), 4), min=round(float(v.min()), 4), max=round(float(v.max()), 4),
                             values=[round(float(x), 4) for x in v])
        if s != 'tta1':
            d = v - base; r[f'{f}.{k}']['paired_gain'] = dict(mean=round(float(d.mean()), 4), min=round(float(d.min()), 4), max=round(float(d.max()), 4), positive=int((d > 0).sum()), of=len(d))
    r['closed_snap40_shown'] = [S[n]['closed_snap40_shown'] for n in names]
    out[s] = r
json.dump(dict(grids=SET, results=out), open(HERE + 'noise_floor.json', 'w'), indent=1)
for s in SET:
    r = out[s]
    print(f"{s:7s} PQ {r['all.PQ']['mean']:.3f} (sd {r['all.PQ']['sd']:.3f}, {r['all.PQ']['min']:.3f}-{r['all.PQ']['max']:.3f})  A {r['A.PQ']['mean']:.3f}  B {r['B.PQ']['mean']:.3f}  "
          f"matched {r['all.matched']['mean']:.1f} merges {r['all.merges']['mean']:.1f} fp {r['all.fp']['mean']:.1f}  rec {r['all.recall_interior']['mean']:.3f} prec {r['all.precision']['mean']:.3f}  "
          f"del {r['all.delete_len']['mean']:.0f} draw {r['all.draw_len']['mean']:.0f}")
    if s != 'tta1':
        print('        paired gain PQ all %s | A %s | B %s | recall %s | precision %s' % tuple(json.dumps(r[k]['paired_gain']) for k in ('all.PQ', 'A.PQ', 'B.PQ', 'all.recall_interior', 'all.precision')))
