"""Page curl (Ben, 6 November 2026): the plates are bound-book scans, so near the spine the page is compressed along the
axis perpendicular to the gutter. A plate's curl correction moves its pixels before its own model places them:

    x' = x + s(u) * (1 + k * v)          (gutter along y; for a gutter along x, y' = y + ... with u, v swapped)
    new(px) = F(px') + d(F(px'))         F the plate's own model, d its affine correction (jointlib.py)

- u: distance in pixels from the plate's gutter edge, measured into the page;
- s: a monotone cubic spline in u with knots at u = 0, 200, 500, 1000, 2000, 4000 and zero beyond 4000 (value and slope),
  written as s(u) = sum_i a_i G_i(u): G_i(u) = integral from u to 4000 of the i-th quadratic B-spline on those knots
  (the one that is non-zero at 4000 left out, so s meets zero smoothly), each scaled to G_i(0) = 1. All a_i >= 0 (s falls
  from s(0) to 0) or all a_i <= 0 (s rises to 0): monotone either way;
- v: position along the gutter, (y - y_mid) / (h / 2), from -1 to 1; k a slow linear variation, |k| <= 0.9 so the
  factor stays positive (Ben's k per pixel is k / (h / 2));
- past the fold (u < 0: a strip of the facing page that the image also shows, as on 37L and 37R) the facing page is
  taken to curl the same way, mirrored: x' = x + 2 s(0) - s(-u), which keeps the displacement continuous and monotone
  across the fold.

The gutter edge per plate: data/sanborn/joint/curl_sides.json (sides() below; the choice and its reason per plate).
"""
import json, os, sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import _ws  # noqa: E402

KNOTS = (0.0, 200.0, 500.0, 1000.0, 2000.0, 4000.0)
UMAX = KNOTS[-1]
NA = 6                      # spline coefficients
K_MAX = 0.9
SIDES = 'joint/curl_sides.json'
BAND_PX = 2000.0            # controls this close to an edge count for that edge's held-out rms
MIN_EDGE_CONTROLS = 4


def _make_basis():
    from scipy.interpolate import BSpline
    t = np.r_[[KNOTS[0]] * 3, KNOTS[1:-1], [KNOTS[-1]] * 3]       # clamped, quadratic: 7 B-splines
    G = []
    for i in range(NA):                                             # the 7th (non-zero at 4000) is left out
        c = np.zeros(len(t) - 3); c[i] = 1.0
        A = BSpline(t, c, 2, extrapolate=False).antiderivative()
        top = float(A(UMAX)); g0 = top - float(A(0.0))
        G.append((A, top, g0))
    return G


_G = None


def phi(u):
    """(n, 6) basis values at u (pixels; u < 0 past the fold, mirrored)"""
    global _G
    if _G is None:
        _G = _make_basis()
    u = np.asarray(u, float); au = np.clip(np.abs(u), 0.0, UMAX)
    out = np.empty((len(u), NA))
    for i, (A, top, g0) in enumerate(_G):
        g = (top - A(au)) / g0
        g = np.where(np.abs(u) >= UMAX, 0.0, g)
        out[:, i] = np.where(u < 0, 2.0 - g, g)
    return out


def uv(side, q):
    """u (pixels into the page from the gutter) and v (-1..1 along the gutter) for pixels q (n, 2)"""
    q = np.asarray(q, float); x, y = q[:, 0], q[:, 1]
    w, h = side['size']
    if side['axis'] == 'x':
        along, half = y, h / 2.0
        line = side['fold'][0] + side['fold'][1] * y if side.get('fold') else (w if side['side'] == 'right' else 0.0)
        u = (line - x) if side['side'] == 'right' else (x - line)
    else:
        along, half = x, w / 2.0
        line = side['fold'][0] + side['fold'][1] * x if side.get('fold') else (h if side['side'] == 'bottom' else 0.0)
        u = (line - y) if side['side'] == 'bottom' else (y - line)
    return u, (along - half) / half


def axis_vec(side):
    return np.array([1.0, 0.0]) if side['axis'] == 'x' else np.array([0.0, 1.0])


def disp(side, a, k, q):
    """pixel displacement (n, 2) of the curl with coefficients a (6,) and k"""
    u, v = uv(side, q)
    s = phi(u) @ np.asarray(a, float)
    return (s * (1.0 + k * v))[:, None] * axis_vec(side)[None, :]


def s_of_u(a, u):
    return phi(np.atleast_1d(np.asarray(u, float))) @ np.asarray(a, float)


# ------------------------------------------------------------------ the gutter edge per plate
def detect_fold(pid, side, size):
    """the fold on a half that shows a strip of the facing page: where the paper's background brightness (85th percentile
    of each pixel column in 500 px bands) dips, within 1,300 px of the gutter-side edge; a line x = c0 + c1 y fitted to
    the bands' minima (robust). None if the dip is not clear in at least 8 bands."""
    import cv2
    sys.path.insert(0, _ws.CODE + 'sbg')
    from sb import find
    im = cv2.imread(find(pid), cv2.IMREAD_GRAYSCALE)
    w, h = size
    x0, x1 = (w - 1300, w) if side == 'right' else (0, 1300)
    pts = []
    for y0 in range(0, h - 250, 500):
        b = im[y0:y0 + 500, x0:x1].astype(float)
        bg = np.convolve(np.percentile(b, 85, axis=0), np.ones(31) / 31, 'same')[20:-20]
        i = int(np.argmin(bg)); dip = float(np.median(bg) - bg[i])
        if dip >= 15:
            pts.append((y0 + 250, x0 + 20 + i, dip))
    if len(pts) < 8:
        return None, pts
    P = np.array(pts); keep = np.ones(len(P), bool)
    for _ in range(4):
        c1, c0 = np.polyfit(P[keep, 0], P[keep, 1], 1)
        keep = np.abs(P[:, 1] - (c0 + c1 * P[:, 0])) < 60
    return [float(c0), float(c1)], pts


def sides(write=False):
    """per plate: the gutter edge. Halves (L / R, docs/sanborn/workspace_notes/sbg/INSTRUCTIONS22.md: "Each plate is a
    double page photographed as two images ... the same strip of streets appears near the right edge of L and the left
    edge of R"): L halves on the right, R halves on the left, the fold line found from the paper's shading where the image
    runs past it. Other plates (no page position in docs/sanborn): the edge whose controls (within 2,000 px of it) have
    the worst held-out residuals of the plate's own model."""
    import importlib.util
    sys.path.insert(0, HERE)
    import seams as S
    spec = importlib.util.spec_from_file_location('joint_solve', os.path.join(HERE, 'solve.py'))
    SV = importlib.util.module_from_spec(spec); spec.loader.exec_module(SV)
    out = {}
    for p in S.plate_ids():
        w, h = SV.plate_size(p)
        X, O, P, Pl, names, model = SV.controls(p)
        res = np.hypot(*(Pl - O).T)
        dist = dict(left=X[:, 0], right=w - X[:, 0], top=X[:, 1], bottom=h - X[:, 1])
        edge = {}
        for e, d in dist.items():
            m = d < BAND_PX
            edge[e] = dict(controls=int(m.sum()), heldout_rms=round(float(np.sqrt(np.mean(res[m] ** 2))), 2) if m.sum() else None)
        rec = dict(size=[int(w), int(h)], edges=edge, heldout_source='own model leave-one-out' if p != '22-35N' else 'own residual (Ben georeference, nothing fitted)')
        n = p[3:]
        if n[-1] in 'LR' and n[:-1].isdigit():
            sd = 'right' if n[-1] == 'L' else 'left'
            fold, pts = detect_fold(p, sd, (w, h))
            rec.update(side=sd, axis='x', how=f"page position: a {'left' if sd == 'right' else 'right'} half, spine on its {sd} edge (INSTRUCTIONS22.md)",
                       fold=fold, fold_bands=[[int(a), int(b), round(c, 1)] for a, b, c in pts],
                       fold_how='paper shading dip, line fitted to the bands' if fold else 'no clear fold in the image: the image edge')
        else:
            cand = {e: v for e, v in edge.items() if v['controls'] >= MIN_EDGE_CONTROLS}
            sd = max(cand, key=lambda e: cand[e]['heldout_rms'])
            rec.update(side=sd, axis='x' if sd in ('left', 'right') else 'y',
                       how=f"page position not in docs/sanborn: the edge with the worst held-out rms of its controls ({cand[sd]['heldout_rms']} m, {cand[sd]['controls']} controls within {BAND_PX:.0f} px)",
                       fold=None, fold_how='the image edge')
        out[p] = rec
    if write:
        os.makedirs(os.path.dirname(_ws.DATA + SIDES), exist_ok=True)
        json.dump(dict(note='gutter edge per 1922 plate for the page-curl correction (tools/sanborn/joint/curl.py sides())', plates=out),
                  open(_ws.DATA + SIDES, 'w', encoding='utf8', newline='\n'), indent=1)
    return out


_S = None


def side_of(pid):
    global _S
    if _S is None:
        _S = json.load(open(_ws.DATA + SIDES, encoding='utf8'))['plates']
    return _S[pid]


if __name__ == '__main__':
    r = sides(write='--write' in sys.argv)
    for p, v in r.items():
        print(p, v['side'], v.get('fold'), {e: (d['controls'], d['heldout_rms']) for e, d in v['edges'].items()})
