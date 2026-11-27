"""rail_pics.py (text_fix/step4, 27 Nov 2026): the hand-off's two rail picture scripts (rail_new_off.py, rail_lost_spots.py)
for a chosen mask set, in one file. Pictures go to step4/pics/rail/<SET>/.
    cd data/sanborn
    python -B bench_2026-11-26/text_fix/step4/code/rail_pics.py new SET RUN N KIND [WHEN]
        rule tracks of the masked run (WHEN: after or afterstrict, default after) more than 10 px from every Ben track of
        their kind, where the before run had none within 10 px either; grouped (40 px), each group cut out: scan | before
        bins | masked bins, Ben's tracks black, the run's rule tracks grey.
    python -B bench_2026-11-26/text_fix/step4/code/rail_pics.py lost SET RUN N
        for a run sorted with Ben's rail on (44_map_ben): every sample of his tracks (every 5 px) that had ink of its bin
        within 10 px (railroad) / 30 px (streetcar) before the mask and none after; grouped (60 px) and cut out:
        scan | mask | before bins | after bins.
Prints the counts; writes json beside the pictures."""
import json, os, sys
import numpy as np, cv2
from scipy.spatial import cKDTree
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
SP = os.getcwd().replace('\\', '/') + '/'; ST = SP + 'bench_2026-11-26/text_fix/step4/'
mode, S, run, N = sys.argv[1:5]; R = ST + f'runs/bins/{S}/'; PO = ST + f'pics/rail/{S}/'; os.makedirs(PO, exist_ok=True)
im = cv2.imread(SP + f'cufp/22-{N}.jpg'); BEN = json.load(open(SP + f'picks22_guided/22-{N}/rail_ben.json', encoding='utf8'))['tracks']


def samp(p, step=2.0):
    p = np.asarray(p, float); S_ = [p[:1]]
    for a, b in zip(p[:-1], p[1:]):
        n = max(1, int(np.ceil(np.hypot(*(b - a)) / step))); S_.append(a + np.linspace(0, 1, n + 1)[1:, None] * (b - a))
    return np.vstack(S_)


def groups(P, d):
    pr = np.array(sorted(cKDTree(P).query_pairs(d)), int).reshape(-1, 2)
    return connected_components(coo_matrix((np.ones(len(pr)), (pr[:, 0], pr[:, 1])), shape=(len(P), len(P))), directed=False)


def colour(sc, b):
    v = (sc * 0.5 + 127).astype(np.uint8); v[b == 4] = (0, 0, 230); v[b == 5] = (0, 150, 255); v[b == 8] = (255, 0, 255); return v


res = []
if mode == 'new':
    kind = sys.argv[5]; when = sys.argv[6] if len(sys.argv) > 6 else 'after'
    B = [samp(t['pts']) for t in BEN if t['kind'] == kind]; BT = cKDTree(np.vstack(B)) if B else None
    tr = {w: [samp(t['pts']) for t in json.load(open(R + f'{run}_{w}_tracks.json', encoding='utf8'))['tracks'] if t['kind'] == kind] for w in ('before', when)}
    TB = cKDTree(np.vstack(tr['before'])) if tr['before'] else None
    A = np.vstack(tr[when]) if tr[when] else np.zeros((0, 2))
    off = A[(BT.query(A)[0] > 10) if BT is not None else np.ones(len(A), bool)]
    new = off[(TB.query(off)[0] > 10) if TB is not None else np.ones(len(off), bool)]
    print(S, run, when, kind, 'samples off Ben', len(off), f'({2 * len(off)} px), new against before', len(new), f'({2 * len(new)} px)')
    bb = cv2.imread(R + f'{run}_before.png', 0); ba = cv2.imread(R + f'{run}_{when}.png', 0); H, W = bb.shape
    if len(new):
        nc, lab = groups(new, 40)
        for c in range(nc):
            g = new[lab == c]; cx, cy = g.mean(0).astype(int); r = int(max(60, np.ptp(g, 0).max() / 2 + 40))
            x0, y0, x1, y1 = max(0, cx - r), max(0, cy - r), min(W, cx + r), min(H, cy + r); sc = im[y0:y1, x0:x1]; pics = [sc]
            for w, b in (('before', bb), (when, ba)):
                v = colour(sc, b[y0:y1, x0:x1])
                for t in BEN:
                    if t['kind'] == kind: cv2.polylines(v, [np.round(np.array(t['pts']) - [x0, y0]).astype(np.int32)], False, (0, 0, 0), 1)
                for t in json.load(open(R + f'{run}_{w}_tracks.json', encoding='utf8'))['tracks']:
                    if t['kind'] == kind: cv2.polylines(v, [np.round(np.array(t['pts']) - [x0, y0]).astype(np.int32)], False, (90, 90, 90), 2)
                pics.append(v)
            z = np.hstack(pics); s_ = min(1.0, 1500 / z.shape[1]); z = cv2.resize(z, None, fx=s_, fy=s_, interpolation=cv2.INTER_AREA)
            f = PO + f'new_{run}_{when}_{kind}_{c}.png'; cv2.imwrite(f, z); res.append(dict(group=c, at=[int(cx), int(cy)], px=int(2 * len(g)), pic=os.path.basename(f)))
            print('  group', c, 'at', (int(cx), int(cy)), 'px', 2 * len(g))
    json.dump(dict(run=run, when=when, kind=kind, off_px=int(2 * len(off)), new_px=int(2 * len(new)), groups=res), open(PO + f'new_{run}_{when}_{kind}.json', 'w', encoding='utf8'), indent=1)
else:
    when = 'after'; HO_mask = ST + f'masks/{S}/{N}_text.png'
    bb = cv2.imread(R + f'{run}_before.png', 0); ba = cv2.imread(R + f'{run}_{when}.png', 0); tc = cv2.imread(HO_mask, 0); H, W = bb.shape
    for kind, code, tol in (('railroad', 4, 10), ('streetcar', 5, 30)):
        Sm = []
        for t in BEN:
            if t['kind'] != kind: continue
            p = np.array(t['pts'], float)
            for q0, q1 in zip(p[:-1], p[1:]): Sm.append(q0[None] + np.linspace(0, 1, max(2, int(np.hypot(*(q1 - q0)) / 5) + 1))[:, None] * (q1 - q0)[None])
        if not Sm: continue
        q = np.vstack(Sm).round().astype(int); q = q[(q[:, 0] >= 0) & (q[:, 0] < W) & (q[:, 1] >= 0) & (q[:, 1] < H)]
        db = cv2.distanceTransform((bb != code).astype(np.uint8), cv2.DIST_L2, 5); da = cv2.distanceTransform((ba != code).astype(np.uint8), cv2.DIST_L2, 5)
        lost = q[(db[q[:, 1], q[:, 0]] <= tol) & (da[q[:, 1], q[:, 0]] > tol)]
        print(S, run, kind, 'samples lost', len(lost))
        if not len(lost): continue
        nc, lab = groups(lost.astype(float), 60)
        for c in range(nc):
            g = lost[lab == c]; cx, cy = g.mean(0).astype(int); r = int(max(60, np.ptp(g, 0).max() / 2 + 40))
            x0, y0, x1, y1 = max(0, cx - r), max(0, cy - r), min(W, cx + r), min(H, cy + r); sc = im[y0:y1, x0:x1]
            mk = np.full_like(sc, 255); mk[np.isin(tc[y0:y1, x0:x1], (2, 3))] = (255, 0, 255); mk[tc[y0:y1, x0:x1] == 1] = (0, 0, 0)
            z = np.hstack([sc, mk, colour(sc, bb[y0:y1, x0:x1]), colour(sc, ba[y0:y1, x0:x1])]); s_ = min(1.0, 1600 / z.shape[1]); z = cv2.resize(z, None, fx=s_, fy=s_, interpolation=cv2.INTER_AREA)
            f = PO + f'lost_{run}_{kind}_{c}.png'; cv2.imwrite(f, z); res.append(dict(kind=kind, group=c, at=[int(cx), int(cy)], samples=int(len(g)), pic=os.path.basename(f)))
            print('  group', c, 'at', (int(cx), int(cy)), 'samples', len(g))
    json.dump(dict(run=run, groups=res), open(PO + f'lost_{run}.json', 'w', encoding='utf8'), indent=1)
