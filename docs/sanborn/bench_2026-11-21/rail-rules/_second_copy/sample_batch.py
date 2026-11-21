"""Random samples of what each proposed change removes or adds on the batch plates, for checking by eye (rail-rules,
21 Nov 2026). Reads batch/tracks_compare.json (batch_tracks.py); writes sample/*.json and, through montage.py, sample/*.jpg.
    cd data/sanborn
    python bench_2026-11-21/rail-rules/sample_batch.py [N_PER_SET] [SEED]
Sets (each drawn uniformly at random, seeded):
  drop_s600      railroad tracks the single 600/60 filter drops
  drop_g_extra   tracks the group 600/60 filter drops that single 600/60 keeps
  drop_s300_extra tracks single 300/30 drops that single 600/60 keeps
  car350_added   points on the streetcar length reach 350 adds over the batch (uniform by length)
  car500_extra   points on the length reach 500 adds over the batch that reach 350 does not add (uniform by length)"""
import sys, os, json, subprocess
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); O = os.path.join(HERE, 'sample'); os.makedirs(O, exist_ok=True)
n = int(sys.argv[1]) if len(sys.argv) > 1 else 36; seed = int(sys.argv[2]) if len(sys.argv) > 2 else 7
R = json.load(open(os.path.join(HERE, 'batch', 'tracks_compare.json')))['plates']; rng = np.random.default_rng(seed)
key = lambda d: (d['plate'], tuple(d['a']), tuple(d['b']))
sets = {}
s600 = [d for r in R for d in r['filters']['s600_60']['dropped']]; k600 = {key(d) for d in s600}
sets['drop_s600'] = s600
sets['drop_g_extra'] = [d for r in R for d in r['filters']['g600_60']['dropped'] if key(d) not in k600]
sets['drop_s300_extra'] = [d for r in R for d in r['filters']['s300_30']['dropped'] if key(d) not in k600]
a350 = [dict(plate=r['plate'], a=list(p), b=list(p), mark=True) for r in R for p in r['reach']['350']['added_pts']]
sets['car350_added'] = a350
p350 = {}
for r in R: p350[r['plate']] = np.array(r['reach']['350']['added_pts'] + r['reach']['300']['added_pts'] or [[-1e9, -1e9]], float)
ex = []
for r in R:
    P = np.array(r['reach']['500']['added_pts'], float).reshape(-1, 2)
    if not len(P): continue
    from scipy.spatial import cKDTree
    d = cKDTree(p350[r['plate']]).query(P)[0]
    ex += [dict(plate=r['plate'], a=[int(x), int(y)], b=[int(x), int(y)], mark=True) for (x, y), dd in zip(P, d) if dd > 40]
sets['car500_extra'] = ex
summary = {}
for name, L in sets.items():
    k = min(n, len(L)); idx = sorted(rng.choice(len(L), k, replace=False).tolist()) if L else []; S = [dict(L[i], label=f"{L[i].get('len', '')}") for i in idx]
    summary[name] = dict(population=len(L), sampled=k)
    json.dump(S, open(os.path.join(O, f'{name}.json'), 'w'), indent=1)
    if S: subprocess.run([sys.executable, os.path.join(HERE, 'montage.py'), os.path.join(O, f'{name}.json'), os.path.join(O, f'{name}.jpg'), '--max', str(k), '--half', '200' if name.startswith('car') else '220'])
json.dump(summary, open(os.path.join(O, 'summary.json'), 'w'), indent=1); print(json.dumps(summary))
