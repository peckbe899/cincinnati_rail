"""Lower Price Hill block (State Ave - Western Ave, Gest St - river; Ben 2026-10-12): bend each 1904 sheet onto the
1922 plates with a smoothing thin-plate spline.
Data per frame: named crossings read on the sheet and on the 1922 plates (lph/ref22.py), displacement = 1922 position
minus the sheet's joint-fit position (lph/tf_all.json); zero-displacement anchors on a 60 m grid over the sheet wherever no
crossing lies within 120 m, so the bend stays local and never extrapolates from crossings along one street.
Spline in units of 100 m, smoothing 0.05 at crossings and 0.5 at anchors. Tapered to zero over the last 80 m before Gest
(north) and Western Ave (east), so the bent sheets meet the unbent neighbours there.
Image correlation between the 1904 and 1922 sheets was tried and dropped (peaks 0.1-0.45, shifts scattered 3-5 m).
Writes lph/tps.pkl and lph/tps_diag.json. disp() and warpfn_factory() are used by the warp and tile scripts.
"""
try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, sys, pickle, numpy as np
from scipy.interpolate import RBFInterpolator
from scipy.spatial import cKDTree
SP = _ws.DATA
sys.path.insert(0, _ws.CODE + 'lph'); sys.path.insert(0, _ws.CODE + 'sbg')
FRAMES = ['33', '34', '35', '47', '460u', '461', '462', '463', '464', '466', '467', '468m']
N_TOP, E_RIGHT, TAPER = 4331620.0, 712880.0, 80.0
U = 100.0
def taper(E, N):
    s = lambda t: t * t * (3 - 2 * t)
    return s(np.clip((N_TOP - N) / TAPER, 0, 1)) * s(np.clip((E_RIGHT - E) / TAPER, 0, 1))
def footprint(TF, f, step=60.0):
    """grid of world points over the frame's page (paper mask)"""
    import mosn
    from PIL import Image
    from sb import find
    Image.MAX_IMAGE_PIXELS = None
    im = np.asarray(Image.open(find(mosn.sheet_of(f))).convert('RGB')); pm, pd = mosn.page_mask(mosn.sheet_of(f), im)
    ys, xs = np.nonzero(pm[::4, ::4]); xs = xs * 32.0; ys = ys * 32.0
    keep = np.ones(len(xs), bool)
    for bx in mosn.PANEL_KEEP.get(f, []): keep &= (xs >= bx[0]) & (ys >= bx[1]) & (xs < bx[2]) & (ys < bx[3])
    for bx in mosn.PANEL_DROP.get(f, []): keep &= ~((xs >= bx[0]) & (ys >= bx[1]) & (xs < bx[2]) & (ys < bx[3]))
    E, N = mosn.ap(TF[f], xs[keep], ys[keep])
    g = np.unique(np.c_[np.round(E / step), np.round(N / step)], axis=0) * step
    return g
def main():
    import mosn
    from ref22 import ref
    from fit22 import pair
    TF = json.load(open(SP + 'lph/tf_all.json')); REF = ref(); R = pickle.load(open(SP + 'lph/obs_all.pkl', 'rb'))['R']
    out = {}; diag = {}
    for f in FRAMES:
        P, V = [], []
        for r in R:
            if r['fr'] != f: continue
            k = pair(r['a'], r['b'])
            if k not in REF: continue
            e, n = mosn.ap(TF[f], r['x'], r['y'])
            c = min(REF[k], key=lambda p: np.hypot(p[0] - e, p[1] - n))
            if np.hypot(c[0] - e, c[1] - n) < 10: P.append((e, n)); V.append((c[0] - e, c[1] - n))
        if not P: print(f, 'no crossings'); continue
        P, V = np.array(P), np.array(V)
        G = footprint(TF, f); d, _ = cKDTree(P).query(G); A = G[d > 120]
        pts = np.r_[P, A]; vec = np.r_[V, np.zeros((len(A), 2))]; sm = np.r_[np.full(len(P), 0.05), np.full(len(A), 0.5)]
        rb = RBFInterpolator(pts / U, vec, kernel='thin_plate_spline', smoothing=sm, degree=1)
        res = np.hypot(*(rb(P / U) - V).T)
        out[f] = dict(pts=pts, vec=vec, smooth=sm)
        # largest bend over the page
        dg = np.hypot(*rb(G / U).T) * taper(G[:, 0], G[:, 1])
        diag[f] = dict(crossings=len(P), anchors=len(A), disp_med=round(float(np.median(np.hypot(*V.T))), 2), disp_max=round(float(np.hypot(*V.T).max()), 2),
                       fit_res_med=round(float(np.median(res)), 2), fit_res_max=round(float(res.max()), 2), page_bend_max=round(float(dg.max()), 2))
        print(f, diag[f], flush=True)
    pickle.dump(out, open(SP + 'lph/tps.pkl', 'wb')); json.dump(diag, open(SP + 'lph/tps_diag.json', 'w'), indent=1)
_RB = {}
def disp(f, E, N, models):
    if f not in models: return np.zeros_like(E, dtype=float), np.zeros_like(N, dtype=float)
    if f not in _RB:
        m = models[f]; _RB[f] = RBFInterpolator(m['pts'] / U, m['vec'], kernel='thin_plate_spline', smoothing=m['smooth'], degree=1)
    Pq = np.c_[np.ravel(E), np.ravel(N)].astype(float); d = np.zeros_like(Pq)
    w = np.ones(len(Pq)) if models[f].get('notaper') else taper(Pq[:, 0], Pq[:, 1]); idx = np.where(w > 0)[0]      # 'notaper': frames outside Lower Price Hill (168, 2026-10-19)
    for i in range(0, len(idx), 100000):
        j = idx[i:i + 100000]; d[j] = _RB[f](Pq[j] / U) * w[j, None]
    return d[:, 0].reshape(np.shape(E)), d[:, 1].reshape(np.shape(N))
def warpfn_factory(TF, models=None):
    import mosn
    models = models if models is not None else pickle.load(open(SP + 'lph/tps.pkl', 'rb'))
    def fn(f, E, N):
        if f not in models: return mosn.inv(TF[f], E, N)
        Eq, Nq = np.asarray(E, float), np.asarray(N, float)
        for _ in range(3):                 # invert world = T(x) + D(T(x)) by fixed point
            dE, dN = disp(f, Eq, Nq, models); Eq, Nq = E - dE, N - dN
        return mosn.inv(TF[f], Eq, Nq)
    return fn
if __name__ == '__main__': main()
