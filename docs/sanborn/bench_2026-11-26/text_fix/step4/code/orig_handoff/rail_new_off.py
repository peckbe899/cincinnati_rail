"""rail_new_off.py (handoff, 26 Nov 2026): the rule tracks of the after run that lie more than 10 px from every Ben track of
their kind, where the before run had none within 10 px either: cut out for looking at (scan | before bins | after bins,
Ben's tracks black, rule tracks of the run grey).
    cd data/sanborn; python -B .../rail_new_off.py RUN N KIND OUTPREFIX"""
import json, sys
import numpy as np, cv2
from scipy.spatial import cKDTree
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
run, N, kind, outp = sys.argv[1:5]; R = 'bench_2026-11-25/text_v1/handoff/runs/bins/'
def samp(p, step=2.0):
    p = np.asarray(p, float); S = [p[:1]]
    for a, b in zip(p[:-1], p[1:]):
        n = max(1, int(np.ceil(np.hypot(*(b - a)) / step))); S.append(a + np.linspace(0, 1, n + 1)[1:, None] * (b - a))
    return np.vstack(S)
B = [samp(t['pts']) for t in json.load(open(f'picks22_guided/22-{N}/rail_ben.json'))['tracks'] if t['kind'] == kind]
BT = cKDTree(np.vstack(B)) if B else None
tr = {w: [samp(t['pts']) for t in json.load(open(R + f'{run}_{w}_tracks.json'))['tracks'] if t['kind'] == kind] for w in ('before', 'after')}
TB = cKDTree(np.vstack(tr['before'])) if tr['before'] else None
A = np.vstack(tr['after']) if tr['after'] else np.zeros((0, 2))
off = A[(BT.query(A)[0] > 10) if BT is not None else np.ones(len(A), bool)]
new = off[(TB.query(off)[0] > 10) if TB is not None else np.ones(len(off), bool)]
print(run, kind, 'after samples off Ben', len(off), '(x2 px) of which new against before', len(new))
im = cv2.imread(f'cufp/22-{N}.jpg'); bb = cv2.imread(R + f'{run}_before.png', 0); ba = cv2.imread(R + f'{run}_after.png', 0); H, W = bb.shape
if len(new):
    pr = np.array(sorted(cKDTree(new).query_pairs(40)), int).reshape(-1, 2)
    nc, lab = connected_components(coo_matrix((np.ones(len(pr)), (pr[:, 0], pr[:, 1])), shape=(len(new), len(new))), directed=False)
    for c in range(nc):
        g = new[lab == c]; cx, cy = g.mean(0).astype(int); r = int(max(60, np.ptp(g, 0).max() / 2 + 40))
        x0, y0, x1, y1 = max(0, cx - r), max(0, cy - r), min(W, cx + r), min(H, cy + r); sc = im[y0:y1, x0:x1]; pics = [sc]
        for w, b in (('before', bb), ('after', ba)):
            v = (sc * 0.5 + 127).astype(np.uint8); s = b[y0:y1, x0:x1]; v[s == 4] = (0, 0, 230); v[s == 5] = (0, 150, 255); v[s == 8] = (255, 0, 255)
            for t in json.load(open(f'picks22_guided/22-{N}/rail_ben.json'))['tracks']:
                if t['kind'] == kind: cv2.polylines(v, [np.round(np.array(t['pts']) - [x0, y0]).astype(np.int32)], False, (0, 0, 0), 1)
            for t in json.load(open(R + f'{run}_{w}_tracks.json'))['tracks']:
                if t['kind'] == kind: cv2.polylines(v, [np.round(np.array(t['pts']) - [x0, y0]).astype(np.int32)], False, (90, 90, 90), 2)
            pics.append(v)
        z = np.hstack(pics); s_ = min(1.0, 1500 / z.shape[1]); z = cv2.resize(z, None, fx=s_, fy=s_, interpolation=cv2.INTER_AREA)
        cv2.imwrite(f'{outp}_{c}.png', z); print('  group', c, 'at', (cx, cy), 'samples', len(g))
