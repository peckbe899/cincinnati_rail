"""How pure are the k-means glyph clusters of plate 44? Two checks:
1. by eye: the clusters judged one-character from pics/clusters_44_0..2.png (the 60 biggest of 80), listed below;
2. measured with the hand labels of out/label_sample_44.json (240 random pieces): inside the clusters judged pure,
   how many sampled pieces carry the cluster's main label.
Writes out/cluster_purity_44.json. Usage: python -B cluster_purity.py"""
import json, numpy as np
from collections import Counter, defaultdict
d = np.load('out/glyphs_44.npz'); cl = d['cluster']
PURE_BY_EYE = {64: '2', 47: '6', 46: '2', 1: '5', 51: '1', 7: '2', 45: '9', 59: '2', 14: '4', 63: '3', 13: '7', 67: '25 rotated', 29: '5',
               76: '4', 9: '7', 74: '3', 8: '3', 53: '4 rotated', 43: '0', 44: '2', 61: 'E', 34: '0',
               37: '2', 19: '0', 58: '5 rotated', 69: 'P', 15: '2 rotated', 36: '4', 62: '0', 4: '2'}
size = np.bincount(cl, minlength=80)
top60 = np.argsort(-size)[:60]
share_pure = size[list(PURE_BY_EYE)].sum() / size.sum()
lab = json.load(open('out/label_sample_44.json'))
per = defaultdict(list)
for i, L in zip(lab['pick'], lab['labels']):
    per[int(cl[i])].append(L)
agree = tot = 0; rows = []
for c, want in PURE_BY_EYE.items():
    ls = per.get(c, [])
    w = want.split(' ')[0]
    a = sum(1 for L in ls if L.rstrip('r') == w)
    agree += a; tot += len(ls); rows.append((c, want, len(ls), a, dict(Counter(ls))))
inpure = sum(len(per.get(int(c), [])) for c in range(80) if c not in PURE_BY_EYE)
res = {'glyph_candidates': int(size.sum()), 'clusters': 80, 'clusters_looked_at': 60,
       'clusters_pure_by_eye': len(PURE_BY_EYE), 'share_of_glyphs_in_pure_clusters': round(float(share_pure), 3),
       'sample_in_pure_clusters': tot, 'sample_agreeing_with_cluster_label': agree,
       'sample_in_other_clusters': inpure, 'per_cluster': rows}
print(json.dumps({k: v for k, v in res.items() if k != 'per_cluster'}, indent=1))
for r in rows: print(r)
json.dump(res, open('out/cluster_purity_44.json', 'w'), indent=1)
