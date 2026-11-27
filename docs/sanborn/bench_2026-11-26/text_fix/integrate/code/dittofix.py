"""dittofix (26 Nov 2026): a post-step on finder3's codes that finds DITTO MARKS left as other ink and makes them text.

    cd data/sanborn
    python -B bench_2026-11-26/text_fix/fix_ditto/code/dittofix.py N --in MASK_DIR --out OUT_DIR [--pic]

    from dittofix import apply; new = apply(N, codes, gray, scale_ft, paper=paper)   # paper optional (edge rule)

Reads MASK_DIR/N_text.png (finder3's codes: 0 paper, 1 line ink, 2 text sure, 3 text by context, 4 shared ink,
5 other ink), the scan cufp/22-N.jpg (gray = Lab L), its paper mask cufp/N/png_alpha_s4.npy and scale_table.json.
Nothing else: no truth, no street map, no rail. Writes OUT_DIR/N_text.png (the same codes; the dittos found turned from
5 into 3) and OUT_DIR/N_text.json (settings, code counts before and after, timings, and every change: its box, the px
changed, the route that took it, and each of its pieces with box and px). --pic also writes N_changes.jpg, 48 changes
drawn at random (scan | codes after, changed px red), for a look by eye.
Only code 5 pixels change, and only to 3 (asserted). Codes 0, 1, 2, 3, 4 never change; line ink is never touched.

What a ditto mark looks like on the 1922 plates (dev truth, bench_2026-11-26/text_fix/dev_ditto):
  - one or two short strokes or dots side by side (=, :, " or a pair of ticks), sometimes joined into one piece;
    100 ft: up to 16 px tall, 20-120 px of ink; 200 and 400 ft: mostly 4-10 px across, 6-60 px of ink;
  - isolated in paper, not touching a line;
  - in CONTEXT: one per lot in a row of lots, so in a row of like marks at a regular spacing; also under or beside a
    figure in a column of story heights or lot figures.
Look-alikes: rail ticks (they touch their line), dashes of dashed lines (bars lined up along their own axis), streetcar
dashes (heavy bars, bigger than any mark here), hook marks, hatching, line ends and specks.

How:
  1. PIECES: 8-connected pieces of the ink that is not line ink (codes 2, 3, 5). Small pieces (2..Amax px, box side
     Smax px or less) whose boxes are gap px apart or less are linked; a linked group of 1-4 small pieces with a box of
     J px or less and MA px of ink is a MARK. Marks within edge px of the paper's edge are dropped.
  2. SHAPE: the main pieces (20% of the mark's ink or more); for two, their sizes, the angle between them and whether
     they lie side by side (a ditto) or end to end (a broken dash); for one, its length and thinness. A mark must have
     a px of paper between it and any other ink (min_paper; so a rail tick end, which touches its line, never passes),
     and its darkest px must be darker than L_dark.
  3. DASH TESTS (any one makes the mark a dash): a thin bar with another thin bar of its size along its own axis; a pair
     whose two pieces lie end to end; a mark lying in a dashed or dotted line (pieces on both sides of it, within Dn px,
     on one straight line, bars along it); a single bar whose own axis runs, on both sides, into ink that goes on along
     that axis within G px.
  4. CONTEXT: ROW = two other non-dash marks of like ink (ratio 3 or less) on one straight line through the mark
     (15 deg) at about equal spacing (0.6-1.67), within Rrow px; PAIR PARTNERS = pairs among those marks; NEAR A FIGURE
     = a text piece of figure size (codes 2/3, box side fig_ext) within Rfig px.
  5. DECISION (decide()), routes:
       1 pair in a row (all scales);
       2 pair near a figure (200 ft only);
       3 strong pair alone: two pieces of like size (ratio 2 or less), side by side, within 30 deg of parallel, both
         strokes not dots, dark, not in a line gap (100 and 200 ft);
       4 single piece in a row of dittos: one piece, s_Amin px or more, not a long bar, not a round filled dot, in a row
         and with s_ppair pair partners in reach (200 and 400 ft; at 100 ft no single pieces).
     Only the code 5 px of a taken mark change, to 3.
How the settings were set: the rules were designed by looking at all 20 dev plates (dev ditto truth, T1-T7) and at
random samples of changes on them; the numbers are hand-set. Two route changes were made after looks at fresh plates
(see the comment at P and scores/eye_checks.txt). code/folds.py grid-tunes 6 thresholds on one fold and scores them on
the other (scores/folds.json).
Results (MEASURED, scores/summary.txt): dev ditto words found 73 -> 172 of 200 (pixel recall 0.500 -> 0.891); T1-T7 F1
0.9445 -> 0.9450; Ben's line ink called text on 44, 1A, 5 unchanged except +7 px (an inch mark) on 5 at 3 px; no new text
in Ben's rail bands on 44 and 5. Takes 2-13 s per plate.
"""
import json, os, sys, time
sys.dont_write_bytecode = True
import numpy as np, cv2
from scipy.spatial import cKDTree
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

HERE = os.path.dirname(os.path.abspath(__file__))
INK_L = 140   # finder2's ink threshold (Lab L)

# settings by scale (ft to the inch). Sizes in full-size scan px (about 300 dpi).
#   Amax, Smax: a small piece has 2..Amax px of ink and a box side of Smax px or less
#   gap: small pieces whose boxes are this close or closer form one mark
#   J: a mark's box side at most J px;  MA: the mark's ink, min and max
#   Rrow: radius for row partners; Rfig: a pair this close to a figure is taken (0 = route off); Dn, G: dash tests
#   nm_min: fewest main pieces; sp_on: strong pairs alone taken; s_Amin, s_ppair: single pieces (ink, pair partners)
# (26 Nov, after the first fresh-plate look: the near-a-figure route is off at 100 and 400 ft; on the dev truth it found no
#  ditto there that the other routes miss, and on fresh plates 11, 93B and 50 it took dashes, line ends and specks.
#  At 400 ft single pieces need 2 pair partners in reach; no dev ditto is lost. After the second fresh-plate look (72) the
#  same at 200 ft: 2 dev dittos lost (both fold A), 152 of 767 single-piece changes on the dev plates dropped.)
P = {100: dict(Amax=90, Smax=17, gap=6, J=24, MA=(20, 120), Rrow=150, Rfig=0, fig_ext=(12, 70), Dn=44, G=14, nm_min=2, sp_on=True, s_Amin=99, s_ppair=1),
     200: dict(Amax=55, Smax=13, gap=5, J=16, MA=(8, 60), Rrow=100, Rfig=45, fig_ext=(9, 60), Dn=32, G=10, nm_min=1, sp_on=True, s_Amin=10, s_ppair=2),
     400: dict(Amax=48, Smax=11, gap=5, J=14, MA=(6, 48), Rrow=90, Rfig=0, fig_ext=(8, 50), Dn=22, G=9, nm_min=1, sp_on=False, s_Amin=12, s_ppair=2)}
COMMON = dict(sp_rA=2.0, sp_side=0.75, sp_dang=30, sp_L=70, sp_el=1.4, s_bar=(3.0, 9), s_dot=(1.35, 0.72, 20), ax_el=1.8, ax_sides=2, dash_ext=40, min_paper=1.9, L_dark=90, iso_r=4, row_ang=15, row_ratio=(0.6, 1.67), row_min=12, peer_ratio=3.0, edge=12)


def scale_of(N):
    t = json.load(open('scale_table.json'))
    return int(t[N]['ft_per_inch'])


def load(N):
    """the scan's Lab L (gray) and the paper mask, full size"""
    im = cv2.imread(f'cufp/22-{N}.jpg'); H, W = im.shape[:2]
    al = np.load(f'cufp/{N}/png_alpha_s4.npy'); paper = cv2.resize(al.astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST) > 0
    return cv2.cvtColor(im, cv2.COLOR_BGR2LAB)[..., 0], paper


def shape(lab, n):
    """every piece's area, length and thickness of the equivalent bar (second moments), centre and angle (as finder2)"""
    ys, xs = np.nonzero(lab); l = lab[ys, xs]; A = np.bincount(l, minlength=n).astype(float); A[A == 0] = 1
    mx = np.bincount(l, xs, n) / A; my = np.bincount(l, ys, n) / A; dx = xs - mx[l]; dy = ys - my[l]
    sxx = np.bincount(l, dx * dx, n) / A; syy = np.bincount(l, dy * dy, n) / A; sxy = np.bincount(l, dx * dy, n) / A
    t = (sxx + syy) / 2; d = np.sqrt(np.maximum(((sxx - syy) / 2) ** 2 + sxy ** 2, 0))
    return A, np.sqrt(12 * (t + d) + 1), np.sqrt(12 * np.maximum(t - d, 0) + 1), mx, my, 0.5 * np.arctan2(2 * sxy, sxx - syy)


def pieces(codes):
    free = np.isin(codes, (2, 3, 5)).astype(np.uint8)
    n, lb, st, _ = cv2.connectedComponentsWithStats(free, connectivity=8)
    A, lg, th, mx, my, an = shape(lb, n)
    m = lb > 0; cc = np.zeros((n, 6), np.int64)
    for v in (2, 3, 5): cc[:, v] = np.bincount(lb[m & (codes == v)], minlength=n)
    lin = cv2.dilate(np.isin(codes, (1, 4)).astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
    touch = np.bincount(lb[m & lin], minlength=n)
    return n, lb, dict(A=st[:, 4].astype(int), bx=st[:, 0], by=st[:, 1], bw=st[:, 2], bh=st[:, 3], long=lg, thick=th, x=mx, y=my, ang=an,
                       c2=cc[:, 2], c3=cc[:, 3], c5=cc[:, 5], touch=touch)


_TH = np.arange(24) * np.pi / 24


def line_gap(other, cx, cy, half, G, cont=6, need=0.8):
    """does the mark at (cx, cy) (crop coordinates) sit in a gap of a line or a dashed line? For 24 directions, a ray
    3 px wide goes both ways from the centre; it hits other ink within half + G px, and that ink goes on along the ray
    for cont px (need of the samples are ink), on both sides. A line crossing the ray (a lot line beside a ditto) does
    not go on along it. Returns (bool, best direction in degrees)"""
    H, W = other.shape; t = np.arange(1, int(half + G + cont) + 1)
    u = np.c_[np.cos(_TH), np.sin(_TH)]; nrm = np.c_[-np.sin(_TH), np.cos(_TH)]
    ok = np.ones(len(_TH), bool)
    for sg in (1, -1):
        hit = np.zeros((len(_TH), len(t)), bool)
        for o in (-1, 0, 1):
            x = np.round(cx + sg * t[None, :] * u[:, :1] + o * nrm[:, :1]).astype(int)
            y = np.round(cy + sg * t[None, :] * u[:, 1:] + o * nrm[:, 1:]).astype(int)
            inside = (x >= 0) & (x < W) & (y >= 0) & (y < H)
            hit |= inside & other[np.clip(y, 0, H - 1), np.clip(x, 0, W - 1)]
        lim = int(half + G)
        first = np.where(hit[:, :lim].any(1), hit[:, :lim].argmax(1), -1)
        for a in range(len(_TH)):
            if first[a] < 0: ok[a] = False; continue
            seg = hit[a, first[a]:first[a] + cont]
            if len(seg) < cont or seg.mean() < need: ok[a] = False
    if ok.any(): return True, float(np.degrees(_TH[np.argmax(ok)]))
    return False, np.nan


def axis_hits(other, cx, cy, ang, half, G, cont=6, need=0.8):
    """along one direction (the axis of a single bar), on how many sides (0, 1, 2) does a ray 3 px wide hit other ink
    within half + G px that goes on along the ray for cont px (a dash before or after it in a dashed line)"""
    H, W = other.shape; t = np.arange(1, int(half + G + cont) + 1); u = (np.cos(ang), np.sin(ang)); nr = (-np.sin(ang), np.cos(ang)); n = 0
    for sg in (1, -1):
        hit = np.zeros(len(t), bool)
        for o in (-1, 0, 1):
            x = np.round(cx + sg * t * u[0] + o * nr[0]).astype(int); y = np.round(cy + sg * t * u[1] + o * nr[1]).astype(int)
            inside = (x >= 0) & (x < W) & (y >= 0) & (y < H); hit |= inside & other[np.clip(y, 0, H - 1), np.clip(x, 0, W - 1)]
        lim = int(half + G)
        if hit[:lim].any():
            f = int(hit[:lim].argmax()); seg = hit[f:f + cont]
            if len(seg) == cont and seg.mean() >= need: n += 1
    return n


def marks(codes, gray, ft, p=None, paper=None):
    """small free-ink pieces linked into marks, with shape features. Returns (lb, pieces F, marks M)"""
    s = {**COMMON, **P[ft], **(p or {})}; H, W = codes.shape
    inner = None if paper is None else cv2.erode(paper.astype(np.uint8), np.ones((2 * s['edge'] + 1, 2 * s['edge'] + 1), np.uint8)) > 0
    n, lb, F = pieces(codes)
    A = F['A']; ext = np.maximum(F['bw'], F['bh'])
    small = (A >= 2) & (A <= s['Amax']) & (ext <= s['Smax']); small[0] = False
    si = np.nonzero(small)[0]
    x0 = F['bx'][si]; y0 = F['by'][si]; x1 = x0 + F['bw'][si] - 1; y1 = y0 + F['bh'][si] - 1
    pr = cKDTree(np.c_[F['x'][si], F['y'][si]]).query_pairs(s['gap'] + s['Smax'], output_type='ndarray')
    if len(pr):
        a, b = pr[:, 0], pr[:, 1]
        gx = np.maximum(0, np.maximum(x0[a], x0[b]) - np.minimum(x1[a], x1[b]) - 1)
        gy = np.maximum(0, np.maximum(y0[a], y0[b]) - np.minimum(y1[a], y1[b]) - 1)
        pr = pr[np.maximum(gx, gy) <= s['gap']]
    else: pr = np.zeros((0, 2), int)
    ng, gl = connected_components(coo_matrix((np.ones(len(pr)), (pr[:, 0], pr[:, 1])), shape=(len(si), len(si))), directed=False)
    order = np.argsort(gl, kind='stable'); groups = np.split(order, np.cumsum(np.bincount(gl, minlength=ng))[:-1])
    R = s['iso_r']; rec = []
    for g in groups:
        ids = si[g]
        if len(ids) > 4: continue
        bx0 = int(F['bx'][ids].min()); by0 = int(F['by'][ids].min()); bx1 = int((F['bx'][ids] + F['bw'][ids]).max()); by1 = int((F['by'][ids] + F['bh'][ids]).max())
        J = max(bx1 - bx0, by1 - by0); At = int(A[ids].sum())
        if J > s['J'] or At < s['MA'][0] or At > s['MA'][1]: continue
        if inner is not None and not inner[(by0 + by1) // 2, (bx0 + bx1) // 2]: continue   # at the paper's edge
        X0, Y0, X1, Y1 = max(0, bx0 - R), max(0, by0 - R), min(W, bx1 + R), min(H, by1 + R)
        sub = lb[Y0:Y1, X0:X1]; mine = np.isin(sub, ids); cs = codes[Y0:Y1, X0:X1]; other = (cs > 0) & ~mine
        if other.any():
            dt = cv2.distanceTransform((~mine).astype(np.uint8), cv2.DIST_L2, 3)
            d_other = float(dt[other].min()); ln = np.isin(cs, (1, 4))
            d_line = float(dt[ln].min()) if ln.any() else 99.
        else: d_other = d_line = 99.
        gv = gray[Y0:Y1, X0:X1][mine]
        # line gap test, on a wider crop
        Rg = int(J / 2 + s['G'] + 8); qx, qy = (bx0 + bx1) / 2, (by0 + by1) / 2
        GX0, GY0, GX1, GY1 = max(0, int(qx) - Rg), max(0, int(qy) - Rg), min(W, int(qx) + Rg + 1), min(H, int(qy) + Rg + 1)
        oth = (codes[GY0:GY1, GX0:GX1] > 0) & ~np.isin(lb[GY0:GY1, GX0:GX1], ids)
        lgap, lgang = line_gap(oth, qx - GX0, qy - GY0, J / 2, s['G'])
        main = ids[A[ids] >= max(2, 0.2 * At)]; main = main[np.argsort(-A[main])]
        ahit = axis_hits(oth, F['x'][main[0]] - GX0, F['y'][main[0]] - GY0, F['ang'][main[0]], F['long'][main[0]] / 2, s['G'])
        r = dict(ahit=ahit, ids=ids, box=(bx0, by0, bx1, by1), n=len(ids), nm=len(main), A=At, J=J, Wb=bx1 - bx0, Hb=by1 - by0,
                 c5=int(F['c5'][ids].sum()), c3=int(F['c3'][ids].sum()), c2=int(F['c2'][ids].sum()), touch=int(F['touch'][ids].sum()),
                 d_other=d_other, d_line=d_line, Lmin=int(gv.min()), Lmean=float(gv.mean()), lgap=float(lgap), lgang=lgang,
                 cx=float(np.average(F['x'][ids], weights=A[ids])), cy=float(np.average(F['y'][ids], weights=A[ids])))
        i = main[0]; r.update(l1=float(F['long'][i]), t1=float(F['thick'][i]), a1=float(F['ang'][i]), A1=int(A[i]))
        if len(main) >= 2:
            j = main[1]; v = np.array([F['x'][j] - F['x'][i], F['y'][j] - F['y'][i]]); dv = float(np.hypot(*v)) or 1.0
            def side(k):   # |sin| of the angle between the joining line and the piece's axis: 1 side by side, 0 end to end
                u = np.array([np.cos(F['ang'][k]), np.sin(F['ang'][k])]); return float(abs(u[0] * v[1] - u[1] * v[0]) / dv)
            da = abs(((F['ang'][j] - F['ang'][i] + np.pi / 2) % np.pi) - np.pi / 2)
            r.update(l2=float(F['long'][j]), t2=float(F['thick'][j]), A2=int(A[j]), dc=dv, side1=side(i), side2=side(j), dang=float(np.degrees(da)),
                     vang=float(np.arctan2(v[1], v[0])))
        rec.append(r)
    keys = sorted({k for r in rec for k in r} - {'ids', 'box'})
    M = {k: np.array([r.get(k, np.nan) for r in rec], float) for k in keys} if rec else {}
    if rec:
        M['ids'] = [r['ids'] for r in rec]; M['box'] = np.array([r['box'] for r in rec])
    return lb, F, M, s


def figures(F, s):
    """text pieces of figure size: most of their ink codes 2/3, box side within fig_ext, 20 px of ink or more"""
    ext = np.maximum(F['bw'], F['bh']); t = F['c2'] + F['c3']
    ok = (t >= 0.5 * F['A']) & (ext >= s['fig_ext'][0]) & (ext <= s['fig_ext'][1]) & (F['A'] >= 20); ok[0] = False
    return np.nonzero(ok)[0]


def dashed_line(M, F, s):
    """a mark lying in a dashed or dotted line: two free-ink pieces on opposite sides of it, within Dn px, on one straight
    line with it (row_ang), each of them and the mark either a dot or a bar lying along that line; and at least one of the
    three a bar along the line (elongation 2 or more), unless the mark is a single dot between two single dots (a dotted
    line). Returns a bool array."""
    nM = len(M['A']); out = np.zeros(nM, bool); Dn = s['Dn']
    ext = np.maximum(F['bw'], F['bh']); el = F['long'] / np.maximum(F['thick'], 1)
    ci = np.nonzero((F['A'] >= 3) & (ext <= s['dash_ext']))[0]; ci = ci[ci > 0]
    if not len(ci): return out
    xy = np.c_[F['x'], F['y']]; T = cKDTree(xy[ci]); sin_t = np.sin(np.radians(s['row_ang'])); cos_t = np.cos(np.radians(s['row_ang']))
    P_ = np.c_[M['cx'], M['cy']]; mel = M['l1'] / np.maximum(M['t1'], 1)
    for k, nb in enumerate(T.query_ball_point(P_, Dn)):
        own = set(int(i) for i in M['ids'][k]); nb = [ci[j] for j in nb if ci[j] not in own]
        if len(nb) < 2: continue
        V = xy[nb] - P_[k]; D = np.hypot(V[:, 0], V[:, 1]); ok = D >= 3
        nb = np.array(nb)[ok]; V = V[ok]; D = D[ok]
        if len(nb) < 2: continue
        U = V / D[:, None]
        ax = np.c_[np.cos(F['ang'][nb]), np.sin(F['ang'][nb])]
        al = np.abs(ax[:, 0] * U[:, 1] - ax[:, 1] * U[:, 0]) <= sin_t      # neighbour's axis along the direction to it
        dot = el[nb] < 1.6; isbar = (el[nb] >= 2.0) & al
        good = dot | al
        for a in range(len(nb)):
            if not good[a]: continue
            for b in range(a + 1, len(nb)):
                if not good[b] or -(U[a] @ U[b]) < cos_t: continue
                ua = U[a]
                if M['nm'][k] >= 2:     # a pair: its two pieces must lie along the line (a dash broken in two)
                    um = np.array([np.cos(M['vang'][k]), np.sin(M['vang'][k])])
                    if abs(um[0] * ua[1] - um[1] * ua[0]) > sin_t: continue
                elif mel[k] >= 1.6:
                    um = np.array([np.cos(M['a1'][k]), np.sin(M['a1'][k])])
                    if abs(um[0] * ua[1] - um[1] * ua[0]) > sin_t: continue
                mbar = (mel[k] >= 2.0) and M['nm'][k] == 1
                if isbar[a] or isbar[b] or mbar or (M['nm'][k] == 1 and dot[a] and dot[b] and mel[k] < 1.6):
                    out[k] = True; break
            if out[k]: break
    return out


def context(M, F, s):
    """for every mark: shape class, dash test, row and figure context (arrays in M)"""
    nM = len(M['A']); P_ = np.c_[M['cx'], M['cy']]
    elong = M['l1'] / np.maximum(M['t1'], 1)
    two = M['nm'] >= 2
    # pair: two main pieces of like size, side by side, near parallel or dots
    rA = np.where(two, M['A1'] / np.maximum(np.nan_to_num(M['A2'], nan=1), 1), np.nan)
    side = np.where(two, np.fmax(M['side1'], M['side2']), np.nan)
    M['elong'] = elong; M['rA'] = rA; M['side'] = side
    # dash test (single thin bar lined up with another thin bar along its axis; or a pair end to end)
    bar = (M['nm'] == 1) & (elong >= 2.5) & (M['l1'] >= 7)
    dash = np.zeros(nM, bool)
    bi = np.nonzero(bar)[0]
    if len(bi) > 1:
        T = cKDTree(P_[bi]); pr = T.query_pairs(5 * s['Smax'], output_type='ndarray')
        for a, b in pr:
            i, j = bi[a], bi[b]; v = P_[j] - P_[i]; d = np.hypot(*v)
            if d < 1: continue
            for k in (i, j):
                u = np.array([np.cos(M['a1'][k]), np.sin(M['a1'][k])])
                if abs(u[0] * v[1] - u[1] * v[0]) / d > np.sin(np.radians(12)): break
            else:
                if d <= 4 * max(M['l1'][i], M['l1'][j]) + 4: dash[i] = dash[j] = True
    el2 = M['l2'] / np.maximum(np.nan_to_num(M['t2'], nan=1), 1); M['elong2'] = el2
    endtoend = two & (np.fmax(M['side1'], M['side2']) < 0.5) & (((elong >= 1.6) & (el2 >= 1.6)) | (np.fmax(elong, el2) >= 2.0))
    M['dash_bar'] = dash; M['dash_pair'] = endtoend
    M['dash_line'] = dashed_line(M, F, s)
    # a single bar whose own axis runs into a dash or a line within G px (a dash of a dashed line, also at its end)
    M['dash_axis'] = (M['nm'] == 1) & (elong >= s['ax_el']) & (M['ahit'] >= s['ax_sides'])
    M['dash'] = dash | endtoend | M['dash_line'] | M['dash_axis']
    # plausible marks: not dashes, isolated, dark enough
    plaus = ~M['dash'] & (M['d_other'] >= s['min_paper']) & (M['d_line'] >= s['min_paper']) & (M['Lmin'] <= s['L_dark'])
    M['plaus'] = plaus
    # row context among looser peers (not dashes, dark enough; may touch other ink): a ditto beside a line still counts
    peer = ~M['dash'] & (M['Lmin'] <= s['L_dark'])
    pi = np.nonzero(peer)[0]; row = np.zeros(nM, int); peers = np.zeros(nM, int); ppair = np.zeros(nM, int)
    if len(pi) > 2:
        T = cKDTree(P_[pi]); cosr = np.cos(np.radians(s['row_ang'])); lo, hi = s['row_ratio']
        for a, nb in enumerate(T.query_ball_point(P_[pi], s['Rrow'])):
            i = pi[a]
            nb = [pi[b] for b in nb if b != a]
            nb = [j for j in nb if 1 / s['peer_ratio'] <= M['A'][j] / M['A'][i] <= s['peer_ratio']]
            peers[i] = len(nb); ppair[i] = sum(1 for j in nb if M['nm'][j] >= 2)
            if len(nb) < 2: continue
            V = P_[nb] - P_[i]; D = np.hypot(V[:, 0], V[:, 1]); ok = D >= s['row_min']; V, D, nbk = V[ok], D[ok], np.array(nb)[ok]
            best = 0
            for x in range(len(V)):
                for y in range(len(V)):
                    if x == y: continue
                    c = -(V[x] @ V[y]) / (D[x] * D[y])        # i between x and y
                    if c >= cosr and lo <= D[x] / D[y] <= hi: best = 2; break
                    w = V[y] - V[x]; dw = np.hypot(*w)          # i at the end: x then y beyond it
                    if dw >= s['row_min'] and (V[x] @ w) / (D[x] * dw) >= cosr and lo <= D[x] / dw <= hi: best = max(best, 1)
                if best == 2: break
            row[i] = best
    M['row'] = row; M['peers'] = peers; M['ppair'] = ppair
    fi = figures(F, s); dfig = np.full(nM, 999.)
    if len(fi):
        T = cKDTree(np.c_[F['x'][fi], F['y'][fi]]); d, _ = T.query(P_, k=1); dfig = d
    M['dfig'] = dfig
    return M


ROUTES = {0: 'no', 1: 'pair in a row', 2: 'pair near a figure', 3: 'strong pair alone', 4: 'single piece in a row of dittos'}


def decide(M, ft, p=None, why=False):
    """which marks are dittos. Returns a bool array (and with why=True the route per mark: 0 no, 1 pair in a row,
    2 pair near a figure, 3 strong pair alone, 4 single piece in a row)"""
    s = {**COMMON, **P[ft], **(p or {})}
    plaus = ~M['dash'] & (M['d_other'] >= s['min_paper']) & (M['d_line'] >= s['min_paper']) & (M['Lmin'] <= s['L_dark'])
    base = plaus & (M['c5'] > 0) & (M['nm'] >= s['nm_min'])
    pair = M['nm'] >= 2; single = M['nm'] == 1
    el1 = M['l1'] / np.maximum(M['t1'], 1); el2 = M['elong2']
    strong = (pair & (M['nm'] == 2) & (M['rA'] <= s['sp_rA']) & (np.fmax(M['side1'], M['side2']) >= s['sp_side']) & (M['dang'] <= s['sp_dang'])
              & (M['Lmin'] <= s['sp_L']) & (M['lgap'] == 0) & (np.fmin(el1, el2) >= s['sp_el']))
    r = np.zeros(len(base), int)
    r[base & pair & (M['row'] >= 1)] = 1
    r[(r == 0) & base & pair & (M['dfig'] <= s['Rfig'])] = 2
    if s['sp_on']: r[(r == 0) & base & strong] = 3
    sbar = (el1 >= s['s_bar'][0]) & (M['l1'] >= s['s_bar'][1])
    fill = M['A'] / np.maximum(1, M['Wb'] * M['Hb'])
    sdot = (el1 < s['s_dot'][0]) & (fill >= s['s_dot'][1]) & (M['A'] >= s['s_dot'][2])   # a round filled dot (hydrant, valve)
    r[(r == 0) & base & single & (M['row'] >= 1) & (M['ppair'] >= s['s_ppair']) & (M['A'] >= s['s_Amin']) & ~sbar & ~sdot] = 4
    return (r > 0, r) if why else r > 0


def run(N, mask_dir, out_dir=None, pic=False, p=None, verbose=True):
    t0 = time.time(); T = {}
    codes = cv2.imread(os.path.join(mask_dir, f'{N}_text.png'), cv2.IMREAD_UNCHANGED)
    gray, paper = load(N); ft = scale_of(N); T['load'] = round(time.time() - t0, 1)
    new, rep = _apply(N, codes, gray, ft, p, paper)
    rep['seconds'] = dict(T, **rep.pop('seconds'), total=round(time.time() - t0, 1))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
        cv2.imwrite(os.path.join(out_dir, f'{N}_text.png'), new)
        if pic: change_sheet(N, codes, new, rep['changes'], os.path.join(out_dir, f'{N}_changes.jpg'))
        with open(os.path.join(out_dir, f'{N}_text.json'), 'w', encoding='utf8', newline='\n') as f: json.dump(rep, f, indent=1, default=str)
    if verbose: print(f"dittofix {N} ({ft} ft): {rep['changed']['marks']} marks, {rep['changed']['px']} px 5->3, {rep['seconds']['total']} s", flush=True)
    return new, rep


def change_sheet(N, codes, new, changes, path, n=48, seed=0, half=32, z=3):
    """a contact sheet of up to n changes drawn at random (seeded): scan | codes after (red = turned 5 -> 3)"""
    import random
    im = cv2.imread(f'cufp/22-{N}.jpg'); H, W = codes.shape; ch = list(changes); random.Random(seed).shuffle(ch); tiles = []
    col = {1: (170, 170, 170), 2: (220, 0, 220), 3: (255, 120, 0), 4: (0, 200, 230), 5: (0, 150, 0)}
    for c in ch[:n]:
        cx, cy = (c['box'][0] + c['box'][2]) // 2, (c['box'][1] + c['box'][3]) // 2
        x0, y0, x1, y1 = max(0, cx - half), max(0, cy - half), min(W, cx + half), min(H, cy + half)
        a = im[y0:y1, x0:x1]; o = np.full_like(a, 245); cn = new[y0:y1, x0:x1]
        for v, cl in col.items(): o[cn == v] = cl
        o[(cn != codes[y0:y1, x0:x1])] = (0, 0, 255)
        t = cv2.resize(np.concatenate([a, o], 1), None, fx=z, fy=z, interpolation=cv2.INTER_NEAREST)
        t = np.concatenate([np.full((14, t.shape[1], 3), 255, np.uint8), t], 0)
        cv2.putText(t, f"{c['box'][0]},{c['box'][1]} {c['route']}", (2, 11), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (0, 0, 0), 1); tiles.append(t)
    if not tiles: return
    h = max(t.shape[0] for t in tiles); w = max(t.shape[1] for t in tiles); cols = 4; rows = (len(tiles) + cols - 1) // cols
    S = np.full((rows * (h + 4), cols * (w + 4), 3), 128, np.uint8)
    for i, t in enumerate(tiles):
        r, cc = divmod(i, cols); S[r * (h + 4):r * (h + 4) + t.shape[0], cc * (w + 4):cc * (w + 4) + t.shape[1]] = t
    cv2.imwrite(path, S, [cv2.IMWRITE_JPEG_QUALITY, 90])


def _apply(N, codes, gray, ft, p=None, paper=None):
    t0 = time.time()
    lb, F, M, s = marks(codes, gray, ft, p, paper); t1 = time.time()
    new = codes.copy(); ch = []
    if len(M):
        M = context(M, F, s); acc, why = decide(M, ft, p, why=True)
        for k in np.nonzero(acc)[0]:
            x0, y0, x1, y1 = (int(v) for v in M['box'][k]); sub = new[y0:y1, x0:x1]
            m = np.isin(lb[y0:y1, x0:x1], M['ids'][k]) & (sub == 5); sub[m] = 3
            pcs = [dict(box=[int(F['bx'][i]), int(F['by'][i]), int(F['bx'][i] + F['bw'][i]), int(F['by'][i] + F['bh'][i])], px=int(F['A'][i]), px5=int(F['c5'][i])) for i in M['ids'][k]]
            ch.append(dict(box=[x0, y0, x1, y1], px=int(m.sum()), route=ROUTES[int(why[k])], pieces=pcs, ink=int(M['A'][k]),
                           row=int(M['row'][k]), fig_px=round(float(M['dfig'][k]), 1)))
    assert not ((codes != new) & (codes != 5)).any()
    rep = dict(plate=N, scale_ft=ft, params={**COMMON, **P[ft], **(p or {})}, n_marks=int(len(M.get('A', []))), changed=dict(marks=len(ch), px=int(sum(c['px'] for c in ch))),
               codes_before={str(v): int(c) for v, c in enumerate(np.bincount(codes.ravel(), minlength=6))},
               codes_after={str(v): int(c) for v, c in enumerate(np.bincount(new.ravel(), minlength=6))}, changes=ch,
               seconds=dict(marks=round(t1 - t0, 1), decide=round(time.time() - t1, 1)))
    return new, rep


def apply(N, codes, gray, scale_ft, **opts):
    """the post-step: finder3's codes in, new codes out (uint8, codes 0-5; only 5 -> 3 changes)"""
    new, rep = _apply(N, codes, gray, int(scale_ft), opts.get('params'), opts.get('paper'))
    if opts.get('report') is not None: opts['report'].update(rep)
    return new


if __name__ == '__main__':
    a = sys.argv; N = a[1]
    mask_dir = a[a.index('--in') + 1]; out_dir = a[a.index('--out') + 1]
    run(N, mask_dir, out_dir, '--pic' in a)
