try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Ben 2026-10-20: the 1922 plates are the reference; bend the 1904 sheets already on the page onto them, the same way as Lower Price Hill
# (lph/tps.py): per frame, displacement = 1922 position minus the sheet's position at its named crossings (cuf/x1904.json, run first);
# which matches count is decided below (similarity check per frame, else agreement with the neighbours); the page's kept matches plus the
# neighbouring frames' kept matches over it (so seams share one field); zero anchors on a 60 m grid more than 120 m from any of them;
# smoothing thin-plate spline (100 m units; 0.05 own crossings, 0.3 neighbours', 0.5 anchors), no taper.
#   python3 cuf/tps1922.py 256,257,...      -> frames added to lph/tps.pkl (from lph/tps_pre1922.pkl), report cuf/tps1922_report.json
import json, sys, os, shutil, pickle, numpy as np
SP = _ws.DATA
sys.path.insert(0, _ws.CODE + 'lph'); sys.path.insert(0, _ws.CODE + 'sbg')
import mosn, tps
from scipy.interpolate import RBFInterpolator
from scipy.spatial import cKDTree
from matplotlib.path import Path
from PIL import Image
from sb import find
Image.MAX_IMAGE_PIXELS = None
TF = {}
for fn in ('lph/tf_all.json', 'lph/tf_ext.json', 'lph/tf_ext2.json', 'lph/tf_ext3.json'): TF.update(json.load(open(SP + fn)))
PX = {}
for fn in ('lph/panels_ext.json', 'lph/panels_ext2.json', 'lph/panels_ext3.json'): PX.update(json.load(open(SP + fn)))
if not os.path.exists(SP + 'lph/tps_pre1922.pkl'): shutil.copy(SP + 'lph/tps.pkl', SP + 'lph/tps_pre1922.pkl')
MOD = pickle.load(open(SP + 'lph/tps_pre1922.pkl', 'rb'))
X = json.load(open(SP + 'cuf/x1904.json'))
FR = sys.argv[1].split(','); U = 100.0
def footprint(f, step=60.0):
    sh = ''.join(ch for ch in f if ch.isdigit())
    im = np.asarray(Image.open(find(int(sh))).convert('RGB')); pm, pd = mosn.page_mask(int(sh), im)
    ys, xs = np.nonzero(pm[::4, ::4]); xs = xs * 32.0; ys = ys * 32.0; q = np.c_[xs, ys]; keep = np.ones(len(q), bool)
    if f in PX: keep &= Path(np.array(PX[f])).contains_points(q)
    for s in PX:
        if s != f and ''.join(ch for ch in s if ch.isdigit()) == sh: keep &= ~Path(np.array(PX[s])).contains_points(q)
    E, N = mosn.ap(TF[f], xs[keep], ys[keep])
    return np.unique(np.c_[np.round(E / step), np.round(N / step)], axis=0) * step
# which matches to trust: a street can have moved between 1904 and 1922, or the 1904 sheet can sit off because it was fitted to today's
# streets where today's differ from both atlases (Dixmyth). Pass 1: a frame with 3+ matches gets a robust similarity onto the 1922
# positions; matches within 6 m of it are kept (whatever the shift). Pass 2: matches on frames with fewer are kept when they agree within
# matches on frames with fewer are kept when under 10 m (as Lower Price Hill), plus the forced ones below.
rows = {f: [r for r in X if r['fr'] == f and 'd' in r] for f in FR}
def sim(A, B):
    a = A - A.mean(0); b = B - B.mean(0); za = a[:, 0] + 1j * a[:, 1]; zb = b[:, 0] + 1j * b[:, 1]; c = (np.conj(za) @ zb) / (np.conj(za) @ za)
    return lambda Q: (lambda z: np.c_[z.real, z.imag])(((Q[:, 0] - A.mean(0)[0]) + 1j * (Q[:, 1] - A.mean(0)[1])) * c) + B.mean(0)
ok = {}
for f in FR:
    R_ = rows[f]
    if len(R_) < 3: continue
    A = np.array([[r['E'], r['N']] for r in R_]); B = np.array([[r['E22'], r['N22']] for r in R_]); k = np.ones(len(R_), bool)
    for _ in range(len(R_)):
        if k.sum() < 3: break
        e = np.hypot(*(sim(A[k], B[k])(A) - B).T); w = int(np.argmax(np.where(k, e, -1)))
        if e[w] > 6: k[w] = False
        else: break
    e = np.hypot(*(sim(A[k], B[k])(A) - B).T) if k.sum() >= 3 else np.full(len(R_), 99.0)
    for r, ee in zip(R_, e): r['acc'] = bool(ee < 6); r['why'] = f'similarity residual {ee:.1f} m'
    ok[f] = True
P1 = [r for f in FR for r in rows[f] if r.get('acc')]
if P1:
    gp = np.array([[r['E'], r['N']] for r in P1]); gv = np.array([[r['E22'] - r['E'], r['N22'] - r['N']] for r in P1])
    GF = RBFInterpolator(gp / U, gv, kernel='thin_plate_spline', smoothing=0.5, degree=1) if len(P1) >= 3 else (lambda q: np.tile(gv.mean(0), (len(q), 1)))
# Dixmyth/Whitfield on 292: sheet 292 has no other crossing and was hung on today's corner; both 1922 plates put the corner 35 m away
# and agree with each other within 5 m, so Dixmyth was realigned after 1922 and the sheet moves with the plates.
FORCE = {('292', 'dixmyth', 'whitfield')}
for f in FR:
    if f in ok: continue
    for r in rows[f]:
        forced = (f,) + tuple(sorted(r['k'])) in FORCE
        r['acc'] = bool(r['d'] < 10 or forced); r['why'] = 'forced (see FORCE)' if forced else f"{r['d']:.1f} m apart"
ACC = [r for f in FR for r in rows[f] if r.get('acc')]
rep = {}
for f in FR:
    if f in MOD: print(f, 'already has a spline (kept)'); continue
    own = [r for r in rows[f] if r.get('acc')]
    out = [f"{r['a']} / {r['b']} {r['d']:.1f} m ({r['why']})" for r in rows[f] if not r.get('acc')]
    G = footprint(f)
    from shapely.geometry import MultiPoint
    hull = MultiPoint([tuple(g) for g in G]).convex_hull.buffer(150)
    from shapely.geometry import Point as _P
    nb = [r for r in ACC if r['fr'] != f and hull.contains(_P(r['E'], r['N'])) and r['why'] != 'forced (see FORCE)']     # neighbours' kept matches over this page: same field across seams
    if own:                                                    # a neighbour's match that disagrees with this page's own by more than 8 m is the neighbour's business
        mv = np.median([[r['E22'] - r['E'], r['N22'] - r['N']] for r in own], 0)
        nb = [r for r in nb if np.hypot(r['E22'] - r['E'] - mv[0], r['N22'] - r['N'] - mv[1]) < 8]
    if not own and not nb: rep[f] = dict(kept=0, left_out=out); print(f, 'no usable match', out); continue
    P = np.array([[r['E'], r['N']] for r in own + nb]); V = np.array([[r['E22'] - r['E'], r['N22'] - r['N']] for r in own + nb])
    d, _ = cKDTree(P).query(G); A = G[d > 120]
    pts = np.r_[P, A]; vec = np.r_[V, np.zeros((len(A), 2))]; sm = np.r_[np.full(len(own), 0.05), np.full(len(nb), 0.3), np.full(len(A), 0.5)]
    MOD[f] = dict(pts=pts, vec=vec, smooth=sm, notaper=True, src='1922 plates (cuf/tps1922.py)')
    rb = RBFInterpolator(pts / U, vec, kernel='thin_plate_spline', smoothing=sm, degree=1)
    res = np.hypot(*(rb(P[:len(own)] / U) - V[:len(own)]).T) if own else np.array([0.0]); bend = np.hypot(*rb(G / U).T)
    rep[f] = dict(kept=len(own), neighbours=len(nb), left_out=out, move_med=round(float(np.median(np.hypot(*V[:max(len(own), 1)].T))), 2),
                  move_max=round(float(np.hypot(*V.T).max()), 2), res_max=round(float(res.max()), 2), page_bend_max=round(float(bend.max()), 2), anchors=len(A))
    print(f, rep[f])
pickle.dump(MOD, open(SP + 'lph/tps.pkl', 'wb')); json.dump(rep, open(SP + 'cuf/tps1922_report.json', 'w'), indent=1)
