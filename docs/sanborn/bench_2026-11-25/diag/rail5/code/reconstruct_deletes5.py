"""Which of the 80 rule tracks Ben was shown on plate 5 (unet_data/5_rail_rule.json, reproduced exactly by
runs/orig_nets_tracks.json) he kept as they were, changed, or deleted: an ESTIMATE from geometry, since the editor
records no deletions. diag/rail5, 25 Nov 2026.  cd data/sanborn; python -B bench_2026-11-25/diag/rail5/code/reconstruct_deletes5.py"""
import json, os
import numpy as np, cv2
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
rule = json.load(open(os.path.join(ROOT, 'inputs', '5_rail_rule.json'), encoding='utf8'))['tracks']
ben = json.load(open(os.path.join(ROOT, 'inputs', 'rail_ben_5_copy.json'), encoding='utf8'))['tracks']
H, W = 7150, 10076
def samp(p, step=2):
    p = np.asarray(p, float); S = [a + np.linspace(0, 1, max(2, int(np.hypot(*(b - a)) / step) + 1))[:-1, None] * (b - a) for a, b in zip(p[:-1], p[1:])]; return np.vstack(S + [p[-1:]])
D = {}
for k in ('railroad', 'streetcar'):
    m = np.zeros((H, W), np.uint8)
    for t in ben:
        if t['kind'] == k: cv2.polylines(m, [np.round(np.array(t['pts'])).astype(np.int32)], False, 1, 1)
    D[k] = cv2.distanceTransform((m == 0).astype(np.uint8), cv2.DIST_L2, 5)
bset = {json.dumps(t['pts']) for t in ben}
res = []
for i, t in enumerate(rule):
    S = samp(t['pts']); q = S.round().astype(int); L = float(np.hypot(*np.diff(np.array(t['pts']), axis=0).T).sum())
    cov = float((D[t['kind']][q[:, 1], q[:, 0]] <= 10).mean())
    how = 'kept as is' if json.dumps(t['pts']) in bset else ('kept, changed or redrawn' if cov >= 0.8 else ('partly kept' if cov >= 0.2 else 'deleted'))
    res.append(dict(i=i, kind=t['kind'], len=round(L), cov10=round(cov, 3), how=how))
from collections import Counter
c = Counter((r['kind'], r['how']) for r in res); print(c)
for k in ('railroad', 'streetcar'):
    for h in ('kept as is', 'kept, changed or redrawn', 'partly kept', 'deleted'):
        R = [r for r in res if r['kind'] == k and r['how'] == h]
        if R: print(k, h, len(R), 'tracks', sum(r['len'] for r in R), 'px')
print('Ben tracks identical to a rule track:', sum(json.dumps(t['pts']) in {json.dumps(r['pts']) for r in rule} for t in ben), 'of', len(ben))
json.dump(res, open(os.path.join(ROOT, 'scores', 'reconstructed_verdicts5.json'), 'w'), indent=1)
