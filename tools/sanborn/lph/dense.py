"""Lower Price Hill block: bend each 1904 sheet onto the 1922 plates with a smoothing thin-plate spline.
Displacements: (1) normalised cross-correlation of line ink (255 - max RGB, high-passed) between the 1904 sheet warped by
the joint fit (tf_all.json) and the 1922 mosaic, 80 m windows every 40 m, search +-10 m; (2) named crossings read on both
(1922 position minus the sheet's fitted position), weighted higher. Per frame: robust smoothing TPS of the displacement
field in world coordinates, tapered to zero over the last 80 m before Gest (north) and Western Ave (east) so the bent
sheets still meet the unbent neighbours there. Writes lph/tps.pkl {frame: dict(pts, vec, smooth)} and diagnostics.
"""
try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, sys, pickle, numpy as np
from PIL import Image
from scipy import ndimage as ndi
from scipy.interpolate import RBFInterpolator
from skimage.feature import match_template
SP = _ws.DATA
sys.path.insert(0, _ws.CODE + 'lph'); sys.path.insert(0, _ws.CODE + 'sbg')
import mosn, mos22
from ref22 import ref
from fit22 import pair
Image.MAX_IMAGE_PIXELS = None
X0, Y0, X1, Y1, RES = 711400.0, 4330250.0, 712950.0, 4331700.0, 0.5
FRAMES = ['33', '34', '35', '47', '460u', '461', '462', '463', '464', '466', '467', '468m']
WIN, STEP, SRCH = 160, 80, 20          # px at 0.5 m: 80 m windows, 40 m step, +-10 m search
N_TOP, E_RIGHT, TAPER = 4331620.0, 712880.0, 80.0
def taper(E, N):
    a = np.clip((N_TOP - N) / TAPER, 0, 1); b = np.clip((E_RIGHT - E) / TAPER, 0, 1)
    s = lambda t: t * t * (3 - 2 * t)
    return s(a) * s(b)
def ink(rgb):
    v = 255.0 - rgb.max(-1).astype(np.float32)
    hp = v - ndi.gaussian_filter(v, 8)
    return ndi.gaussian_filter(hp, 1.0)
def grid():
    W, H = int((X1 - X0) / RES), int((Y1 - Y0) / RES)
    jj, ii = np.meshgrid(np.arange(W), np.arange(H)); return W, H, X0 + (jj + 0.5) * RES, Y1 - (ii + 0.5) * RES
def warp_frame(TF, f):
    """1904 frame on the grid: RGB and coverage mask (page and panel)"""
    W, H, E, N = grid()
    one = mosn.mosaic(TF, X0, Y0, X1, Y1, RES, [f])
    cov = np.any(one != 245, axis=-1)
    cov = ndi.binary_erosion(ndi.binary_closing(cov, iterations=4), iterations=6)
    return one, cov
def main():
    TF = json.load(open(SP + 'lph/tf_all.json'))
    m22 = mos22.mosaic(X0, Y0, X1, Y1, RES)
    c22 = ndi.binary_erosion(np.any(np.abs(m22.astype(int) - 240) > 3, axis=-1) | (m22.min(-1) < 200), iterations=4)
    I22 = ink(m22); np.save(SP + 'lph/_i22.npy', I22.astype(np.float16))
    REF = ref(); D = pickle.load(open(SP + 'lph/obs_all.pkl', 'rb')); R = D['R']
    out = {}; diag = {}
    for f in FRAMES:
        rgb, cov = warp_frame(TF, f); I04 = ink(rgb); H, W = cov.shape
        pts, vec, wt, q = [], [], [], []
        for cy in range(WIN // 2 + SRCH, H - WIN // 2 - SRCH, STEP):
            for cx in range(WIN // 2 + SRCH, W - WIN // 2 - SRCH, STEP):
                y0, x0 = cy - WIN // 2, cx - WIN // 2
                if cov[y0:y0 + WIN, x0:x0 + WIN].mean() < 0.85: continue
                if c22[y0 - SRCH:y0 + WIN + SRCH, x0 - SRCH:x0 + WIN + SRCH].mean() < 0.9: continue
                t = I04[y0:y0 + WIN, x0:x0 + WIN]
                if t.std() < 2.0: continue
                s = I22[y0 - SRCH:y0 + WIN + SRCH, x0 - SRCH:x0 + WIN + SRCH].astype(np.float32)
                if s.std() < 2.0: continue
                cc = match_template(s, t)                 # (2*SRCH+1)^2
                iy, ix = np.unravel_index(np.argmax(cc), cc.shape); pk = cc[iy, ix]
                if pk < 0.30 or iy in (0, cc.shape[0] - 1) or ix in (0, cc.shape[1] - 1): continue
                c2 = cc.copy(); c2[max(0, iy - 4):iy + 5, max(0, ix - 4):ix + 5] = -1
                if c2.max() > 0.85 * pk: continue        # ambiguous (repeated pattern)
                def sub(a, b, c): d = a - 2 * b + c; return 0.0 if d >= 0 else 0.5 * (a - c) / d
                dx = ix - SRCH + sub(cc[iy, ix - 1], pk, cc[iy, ix + 1]); dy = iy - SRCH + sub(cc[iy - 1, ix], pk, cc[iy + 1, ix])
                E = X0 + (cx + 0.5) * RES; N = Y1 - (cy + 0.5) * RES
                pts.append((E, N)); vec.append((dx * RES, -dy * RES)); wt.append(1.0); q.append(float(pk))
        npatch = len(pts)
        # named crossings shared with the 1922 plates
        for r in R:
            if r['fr'] != f: continue
            k = pair(r['a'], r['b'])
            if k not in REF: continue
            e, n = mosn.ap(TF[f], r['x'], r['y'])
            cand = min(REF[k], key=lambda p: np.hypot(p[0] - e, p[1] - n))
            if np.hypot(cand[0] - e, cand[1] - n) < 10: pts.append((e, n)); vec.append((cand[0] - e, cand[1] - n)); wt.append(4.0); q.append(1.0)
        pts, vec, wt = np.array(pts), np.array(vec), np.array(wt)
        if len(pts) < 3: print(f, 'too few', len(pts)); continue
        keep = np.ones(len(pts), bool)
        for it in range(3):
            smooth = 25.0 / wt[keep]
            rb = RBFInterpolator(pts[keep], vec[keep], kernel='thin_plate_spline', smoothing=smooth, degree=1)
            rr = np.hypot(*(rb(pts) - vec).T)
            keep = rr < max(2.5, 3 * np.median(rr[keep]))
        smooth = 25.0 / wt[keep]
        rb = RBFInterpolator(pts[keep], vec[keep], kernel='thin_plate_spline', smoothing=smooth, degree=1)
        rr = np.hypot(*(rb(pts) - vec).T)
        out[f] = dict(pts=pts[keep], vec=vec[keep], smooth=smooth)
        mag = np.hypot(*vec[keep].T)
        diag[f] = dict(patches=npatch, crossings=int((wt > 1).sum()), kept=int(keep.sum()), med_disp=round(float(np.median(mag)), 2),
                       max_disp=round(float(mag.max()), 2), med_fit_res=round(float(np.median(rr[keep])), 2),
                       mean_vec=[round(float(v), 2) for v in vec[keep].mean(0)])
        print(f, diag[f], flush=True)
    pickle.dump(out, open(SP + 'lph/tps.pkl', 'wb')); json.dump(diag, open(SP + 'lph/tps_diag.json', 'w'), indent=1)
_RB = {}
def disp(f, E, N, models=None):
    """tapered TPS displacement of frame f at world points"""
    models = models or pickle.load(open(SP + 'lph/tps.pkl', 'rb'))
    if f not in models: return np.zeros_like(E), np.zeros_like(N)
    if f not in _RB:
        m = models[f]; _RB[f] = RBFInterpolator(m['pts'], m['vec'], kernel='thin_plate_spline', smoothing=m['smooth'], degree=1)
    P = np.c_[np.ravel(E), np.ravel(N)]; d = np.zeros_like(P)
    w = taper(P[:, 0], P[:, 1]); sel = w > 0
    for i in range(0, sel.sum(), 200000):
        idx = np.where(sel)[0][i:i + 200000]; d[idx] = _RB[f](P[idx]) * w[idx, None]
    return d[:, 0].reshape(np.shape(E)), d[:, 1].reshape(np.shape(N))
def warpfn_factory(TF, models=None):
    models = models or pickle.load(open(SP + 'lph/tps.pkl', 'rb'))
    def fn(f, E, N):
        dE, dN = disp(f, E, N, models)
        # inverse of world = T(x) + D(T(x)): two fixed-point steps
        Eq, Nq = E - dE, N - dN
        dE2, dN2 = disp(f, Eq, Nq, models); Eq, Nq = E - dE2, N - dN2
        return mosn.inv(TF[f], Eq, Nq)
    return fn
if __name__ == '__main__': main()
