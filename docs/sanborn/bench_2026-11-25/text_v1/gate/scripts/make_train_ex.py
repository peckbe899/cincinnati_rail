"""Gate scorer (26 Nov 2026): the classifier's training set less every row whose box overlaps a held-out window.
Reads classifier/data/train.npz (read only); writes gate/refit/data/train_ex.npz. Same rule as build_train.py --exclude
(box overlap), applied to the finished rows so everything else stays identical."""
import json, os, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); G = os.path.join(HERE, '..')
D = dict(np.load(os.path.join(G, 'refit', 'data', 'train.npz'), allow_pickle=True))
W = json.load(open(os.path.join(G, 'out', 'heldout_windows.json')))
bb = D['bbox']; pl = D['plate']; drop = np.zeros(len(pl), bool)
for N, ws in W.items():
    for x0, y0, x1, y1 in ws:
        drop |= (pl == N) & (bb[:, 0] < x1) & (bb[:, 1] < y1) & (bb[:, 0] + bb[:, 2] > x0) & (bb[:, 1] + bb[:, 3] > y0)
print('rows', len(pl), 'dropped', int(drop.sum()))
n = len(pl)
E = {k: (v[~drop] if (hasattr(v, 'shape') and v.ndim >= 1 and v.shape[0] == n) else v) for k, v in D.items()}
E['exclude'] = np.array(json.dumps(W))
np.savez_compressed(os.path.join(G, 'refit', 'data', 'train_ex.npz'), **E)
