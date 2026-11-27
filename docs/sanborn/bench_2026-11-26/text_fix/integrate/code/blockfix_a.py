"""blockfix (fix_block_a, 26 Nov 2026): BLOCK NUMBERS, approach A (geometry). A post-step on finder3's codes.

    cd data/sanborn
    python -B bench_2026-11-26/text_fix/fix_block_a/code/blockfix.py N --in MASK_DIR --out OUT_DIR [--win X0 Y0 X1 Y1] [--set k=v ...]

Reads MASK_DIR/N_text.png (finder3's codes: 0 paper, 1 line ink, 2 text sure, 3 text by context, 4 shared ink, 5 other
ink), the scan cufp/22-N.jpg, its paper mask cufp/N/png_alpha_s4.npy and scale_table.json. Reads no truth. Writes
OUT_DIR/N_text.png (same codes) and OUT_DIR/N_text.json (counts, timings, every change listed by piece).

What it does (all sizes in full-size scan px, about 300 dpi; the lettering is the same size at 100, 200 and 400 ft):
  1. CORE: the ink opened with a 5 px disk (core_d): strokes 5 px wide or more. Block numbers are the boldest figures on
     the plate (strokes 6-9 px); lot and house numbers (2-4 px) and thin lines are not in it.
  2. LONG LINES: ink that a straight band_len (121) px line fits, at 64 angles, on the ink grown by 1 px (finder2's
     long_ink). finder2 cut its big-letter core by this ink grown by 2 px and judged each piece alone, so a figure crossed
     by a line fell apart into pieces that were refused as links, bars or line bits.
  3. ROUGH WORDS: the core less the long lines, in pieces; pieces side by side (vertical overlap) within a small gap, or
     one above the other (a figure cut by a horizontal line), make a rough word.
  4. CROSSING LINES, per rough word: a line that crosses the figures runs on BOTH sides of the word's box. It is fitted
     from the line ink OUTSIDE the box only (long lines and finder3's code 1; a Hough count over angle and offset, then
     a fit through the median offset of each 1 px step, the two sides in line within 1.5 px and running the same way
     within 2.5 deg, ink on 70% of the first 30 px out of the box on both sides), and only its own width (measured
     outside, + 1 px) is taken out through the box (cross_lines). Two lines that meet the figure from both sides but are
     not in line (a lot line that jogs at a block line) are not a crossing: the long-line rule in step 2 lets a 121 px
     line tilt through a thick stroke from one to the other.
     STUBS: a line that comes in from ONE side is followed into the box while there is ink along it; its thin ink there
     is line ink, and when it is as wide as a stroke (5 px or more: a heavy line ending at a figure) its core too
     (stub_lines).
  5. FIGURES: in the box (grown 4 px), the core less the crossing strips, in pieces. Pieces are dropped when they are
     not text yet and are pieces of lines: they carry on a line along their own axis, or sit between two lines that run
     on past one end (the fill of a double line), or are slanted dashes with a stroke in line beyond a gap, or half or
     more of them is a streetcar dash (finder2.heavy_bars). Round symbols are dropped group by group (ring_groups).
     Pieces not yet text must stand in the row of the pieces that are (the band rule). The word is a FIGURE WORD when
     its height, width, density and stroke width fit a bold upright figure group (accept()), it is not one smooth heavy
     stroke (is_curve: an arc or bend of a heavy line), and a quarter or more of it is already text (ANCHOR: finder3
     found part of the number), or it passes the stricter tests for figures found nowhere (free_figures: 1-3 upright
     figures of full height, touching line ink at one place at most; a lone bar only when upright, free, and with no
     like bar in line within 300 px).
  6. FIGURE INK: the accepted pieces grown by grow px over the ink, but never into a crossing strip, a stub, long-line
     ink (inside the box too), nor thin straight ink (thin ink, not core, on which a straight ts_len px line fits:
     lines, ticks and dashes beside the figure).
  7. CODES: figure ink that finder3 calls 1, 4 or 5 becomes 2 (text sure), except where it touches line ink that stays
     (the strips, the stubs, the long lines, thin straight ink, code 1 left outside the figure): there it becomes 4
     (shared). Never a px of a streetcar dash. The strips keep their code. Nothing outside the accepted words changes;
     text (2, 3) is never taken away.
Parameters: P below; --set k=v (JSON value) changes one for a run. The defaults were chosen by two-fold tuning on the dev
block truth (code/tune.py; both folds chose the same setting). Dev and check scripts are in this folder's code/.
"""
import json, os, sys, time
sys.dont_write_bytecode = True
import numpy as np, cv2
from scipy.spatial import cKDTree

HERE = os.path.dirname(os.path.abspath(__file__))
# finder2's streetcar-dash rule (heavy_bars) is used as it is (imported read-only from text_v1/code)
sys.path.insert(0, os.path.normpath(os.path.join(HERE, '..', '..', '..', '..', 'bench_2026-11-25', 'text_v1', 'code')))
import finder2  # noqa: E402
P = dict(core_d=5, band_len=121, band_angles=64, ts_len=25, ts_angles=48, grow=3, min_area=40,
         # rough words: side by side (vertical overlap share, gap as share of the taller height, px floor) and stacked
         side_ov=0.3, side_gap=0.45, side_gap_min=8, side_xov=0.3, stack_ov=0.5, stack_gap=14, stack_hmax=42, stack_wr=0.5, stack_Hmax=85, rough_H=(25, 110), join_A=100, near_d=6,
         # crossing lines: angle step (deg), px of line on each side, collinearity (px), box margin
         x_step=1.5, x_near=6, x_min=24, x_col=1.5, x_out=2, x_maxw=14, x_run=30, x_cov=0.7, x_ang=2.5, x_rms=1.2, box_g=4,
         # figure word: height, width/height, density (core px / box), stroke width (median ridge, px)
         H=(36, 100), WH=3.6, dens=(0.12, 0.62), sw=(5.0, 15.0),
         anchor=0.25, pad=40, own_anchor=0.5, el_ratio=3.0, co_hits=0.7, ring_min=45, ring_ar=1.2, ring_hole=0.45,
         strip_m=0.5, src_code1=True, touch_r=1, grow_noLB=True, stub_heavy=5.0, bars=True, curve=True, curve_r=1.6, band=True, band_anchor=0.25, band_tol=0.25, band_x=1.2, stubs=True, free=True, free_H=(40, 90), free_sw=(4.8, 12.0), free_ring_ar=1.3, free_full=0.75, free_ar=1.1, free_contacts=1)
CODE = dict(paper=0, line=1, sure=2, ctx=3, shared=4, other=5)


def E(k): return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))


def line_kernel(length, ang):
    k = np.zeros((length, length), np.uint8); c = length // 2; d = np.array([np.cos(ang), np.sin(ang)]) * c
    cv2.line(k, tuple(np.round(c - d).astype(int).tolist()), tuple(np.round(c + d).astype(int).tolist()), 1, 1); return k


def straight(ink, L, NA):
    """ink on which a straight L px line fits, tried at NA angles on the ink grown by 1 px (finder2.long_ink's rule)"""
    fat = cv2.dilate(ink, np.ones((3, 3), np.uint8)); o = np.zeros_like(ink)
    for i in range(NA): o |= cv2.morphologyEx(fat, cv2.MORPH_OPEN, line_kernel(L, np.pi * i / NA)) & ink
    return o


def euler8(lab, n):
    b = (lab > 0); a, bb, c, d = b[:-1, :-1], b[:-1, 1:], b[1:, :-1], b[1:, 1:]
    s = a.astype(np.int8) + bb + c + d
    lw = np.maximum(np.maximum(lab[:-1, :-1], lab[:-1, 1:]), np.maximum(lab[1:, :-1], lab[1:, 1:]))
    c1 = np.bincount(lw[s == 1], minlength=n); c3 = np.bincount(lw[s == 3], minlength=n)
    diag = (s == 2) & (((a & d) & ~bb & ~c) | ((bb & c) & ~a & ~d)); cd = np.bincount(lw[diag], minlength=n)
    return (c1 - c3 - 2 * cd) / 4.0


def pieces(FC, codes):
    n, lb, st, _ = cv2.connectedComponentsWithStats(FC, connectivity=8)
    m = lb > 0; A = st[:, 4].astype(float)
    txt = np.bincount(lb[m & np.isin(codes, (2, 3))], minlength=n)
    # stroke width: 2 x area / boundary px (a bar of width w and length L >> w: 2 w L / 2 L)
    bd = (FC > 0) & ~(cv2.erode(FC, cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))) > 0)
    sw = 2 * A / np.maximum(np.bincount(lb[bd], minlength=n), 1); sw[0] = 0
    holes = np.round(1 - euler8(lb, n)).astype(int)
    return dict(n=n, lb=lb, x=st[:, 0], y=st[:, 1], w=st[:, 2], h=st[:, 3], A=A, txt=txt / np.maximum(A, 1), sw=sw, holes=holes)


class UF:
    def __init__(s, n): s.p = list(range(n))
    def f(s, a):
        while s.p[a] != a: s.p[a] = s.p[s.p[a]]; a = s.p[a]
        return a
    def u(s, a, b): s.p[s.f(a)] = s.f(b)


def group(Q, keep):
    """join pieces into words: side by side, or stacked (a figure cut by a horizontal line)"""
    idx = np.nonzero(keep)[0]; uf = UF(len(Q['A']))
    if len(idx) < 2: return uf
    cx = Q['x'][idx] + Q['w'][idx] / 2; cy = Q['y'][idx] + Q['h'][idx] / 2
    T = cKDTree(np.c_[cx, cy]); R = float(max(Q['w'][idx].max(), Q['h'][idx].max())) * 1.6 + 20
    box = {int(i): (Q['x'][i], Q['y'][i], Q['x'][i] + Q['w'][i], Q['y'][i] + Q['h'][i]) for i in idx}
    pr = T.query_pairs(R, output_type='ndarray')
    if len(pr): pr = pr[np.argsort(np.hypot(cx[pr[:, 0]] - cx[pr[:, 1]], cy[pr[:, 0]] - cy[pr[:, 1]]), kind='stable')]
    for a, b in pr:
        i, j = idx[a], idx[b]
        x0i, x1i, y0i, y1i = Q['x'][i], Q['x'][i] + Q['w'][i], Q['y'][i], Q['y'][i] + Q['h'][i]
        x0j, x1j, y0j, y1j = Q['x'][j], Q['x'][j] + Q['w'][j], Q['y'][j], Q['y'][j] + Q['h'][j]
        vov = min(y1i, y1j) - max(y0i, y0j); hov = min(x1i, x1j) - max(x0i, x0j)
        hm = max(Q['h'][i], Q['h'][j])
        side = (vov >= P['side_ov'] * min(Q['h'][i], Q['h'][j]) and -hov <= max(P['side_gap_min'], P['side_gap'] * hm)
                and hov <= P['side_xov'] * min(Q['w'][i], Q['w'][j]))   # side by side, not one under the other
        # stacked: two parts of ONE figure cut by a line (each part shorter than a whole figure, together a figure)
        stack = (hov >= P['stack_ov'] * min(Q['w'][i], Q['w'][j]) and -vov <= P['stack_gap'] and hm <= P['stack_hmax']
                 and min(Q['w'][i], Q['w'][j]) >= P['stack_wr'] * max(Q['w'][i], Q['w'][j])
                 and max(y1i, y1j) - min(y0i, y0j) <= P['H'][1])
        if not (side or stack): continue
        # the joined group must stay one row of figures: not taller than H[1], and a stacked join not taller than
        # stack_Hmax (a figure split by a line, not a figure with a letter under it)
        a_, b_ = uf.f(i), uf.f(j)
        if a_ == b_: continue
        ga, gb = box[a_], box[b_]; nb = (min(ga[0], gb[0]), min(ga[1], gb[1]), max(ga[2], gb[2]), max(ga[3], gb[3]))
        if nb[3] - nb[1] > (P['H'][1] if side else P['stack_Hmax']): continue
        uf.u(i, j); box[uf.f(i)] = nb
    return uf


def box_interval(r, u, n_, box):
    """for lines at offset r (array) along direction u: the stretch [ta, tb] of t where the line t u + r n_ lies inside box
    (x0, y0, x1, y1); nan where it misses the box"""
    x0, y0, x1, y1 = box; lo = np.full(r.shape, -np.inf); hi = np.full(r.shape, np.inf); ok = np.ones(r.shape, bool)
    for k, (a, b) in enumerate(((x0, x1), (y0, y1))):
        if abs(u[k]) < 1e-9:
            v = r * n_[k]; ok &= (v >= a) & (v <= b)
        else:
            ta = (a - r * n_[k]) / u[k]; tb = (b - r * n_[k]) / u[k]
            lo = np.maximum(lo, np.minimum(ta, tb)); hi = np.minimum(hi, np.maximum(ta, tb))
    ok &= lo <= hi; lo[~ok] = np.nan; hi[~ok] = np.nan
    return lo, hi


def line_cands(pts, box, both):
    """Hough count over angle and offset of the line px pts (outside the box) on the two sides of the box. For each px its
    own line's stretch inside the box (grown by x_near across, x_out along) splits it into before / after. both: score
    min(before, after) (lines through the box); else each side apart (lines coming in from one side)"""
    x0, y0, x1, y1 = box; e_ = P['x_near']; g = P['x_out']; cand = []
    for th in np.radians(np.arange(0, 180, P['x_step'])):
        u = np.array([np.cos(th), np.sin(th)]); n_ = np.array([-u[1], u[0]])
        t = pts @ u; r = pts @ n_
        ta, tb = box_interval(r, u, n_, (x0 - e_, y0 - e_, x1 + e_, y1 + e_))
        sel = ~np.isnan(ta)
        if not sel.any(): continue
        rmin = np.floor(r[sel].min()); rb = np.floor(r[sel] - rmin).astype(int); nb = int(rb.max()) + 2
        bef = np.bincount(rb[t[sel] < ta[sel] - g], minlength=nb); aft = np.bincount(rb[t[sel] > tb[sel] + g], minlength=nb)
        b3 = np.convolve(bef, np.ones(3), 'same'); a3 = np.convolve(aft, np.ones(3), 'same')
        if both:
            sc = np.minimum(b3, a3)
            for j in np.nonzero(sc >= P['x_min'])[0]: cand.append((sc[j], -1, th, rmin + j + 0.5))
        else:
            for side, h3 in ((0, b3), (1, a3)):
                for j in np.nonzero(h3 >= P['x_min'])[0]: cand.append((h3[j], side, th, rmin + j + 0.5))
    cand.sort(key=lambda c: -c[0]); picks = []
    for sc, side, th, r in cand:
        if any(q[1] == side and abs(((th - q[2] + np.pi / 2) % np.pi) - np.pi / 2) <= np.radians(8) and abs(r - q[3]) <= 5 for q in picks): continue
        picks.append((sc, side, th, r))
    return picks


def side_px(pts, th, r, box, side):
    """px near the trial line (within 2.5 px), on one side of the box (0 before, 1 after), their t, r and the distance out
    of the box along the line"""
    x0, y0, x1, y1 = box; e_ = P['x_near']; g = P['x_out']
    u = np.array([np.cos(th), np.sin(th)]); n_ = np.array([-u[1], u[0]]); t = pts @ u; rr = pts @ n_
    ta, tb = box_interval(np.array([r]), u, n_, (x0 - e_, y0 - e_, x1 + e_, y1 + e_)); ta, tb = float(ta[0]), float(tb[0])
    if np.isnan(ta): return None
    near = np.abs(rr - r) <= 2.5
    sd = near & ((t < ta - g) if side == 0 else (t > tb + g)); dist = (ta - t) if side == 0 else (t - tb)
    return sd, t, rr, dist, u, n_, ta, tb


def coverage(sd, dist):
    dd = np.unique(np.floor(dist[sd]).astype(int)); D = P['x_run']
    return len(dd[(dd >= P['x_out'] + 1) & (dd <= D)]) / max(1, D - P['x_out'])


def cross_lines(LBw, box):
    """lines crossing box (x0, y0, x1, y1, window coords), fitted from the line ink LBw outside the box grown by x_out px.
    Returns a list of dict(p=point, u=direction, w=width, n=(px before, px after))"""
    x0, y0, x1, y1 = box; g = P['x_out']
    out_ = LBw.copy(); out_[max(0, y0 - g):y1 + g, max(0, x0 - g):x1 + g] = 0
    ys, xs = np.nonzero(out_)
    if len(xs) < 2 * P['x_min']: return []
    pts = np.c_[xs + 0.5, ys + 0.5]; lines = []
    for sc, _, th, r in line_cands(pts, box, True):
        S0 = side_px(pts, th, r, box, 0); S1 = side_px(pts, th, r, box, 1)
        if S0 is None or S1 is None: continue
        sides = [S0[0], S1[0]]; t, rr, u, n_ = S0[1], S0[2], S0[4], S0[5]
        if min(sides[0].sum(), sides[1].sum()) < P['x_min']: continue
        # the line must run on from the box on both sides: ink along it on x_cov of the first x_run px out of the box
        # (a run of crossings of other lines, scattered along a slant, is not a line)
        if min(coverage(S0[0], S0[3]), coverage(S1[0], S1[3])) < P['x_cov']: continue
        # robust fit: the median offset in each 1 px step along the line (a line crossing near the box adds many px at a
        # few steps only), a straight line through those medians, both sides together and each side alone
        fit = robust_fit([(t[sd], rr[sd]) for sd in sides])
        if fit is None: continue
        a, b, res, sides_ab, w = fit
        # the two sides in line with each other (at the box), each side running the same way
        offs = [(a2 + b2 * tc) - (a + b * tc) for (a2, b2), tc in zip(sides_ab, (S0[6], S1[7]))]
        if max(abs(o) for o in offs) > P['x_col']: continue
        if max(abs(np.degrees(np.arctan(b2) - np.arctan(b))) for a2, b2 in sides_ab) > P['x_ang']: continue
        if w > P['x_maxw'] or res > max(P['x_rms'], 0.45 * w): continue
        d = u + b * n_; d = d / np.linalg.norm(d); c = n_ * a
        lines.append(dict(p=c, u=d, w=float(w), n=[int(sides[0].sum()), int(sides[1].sum())], rms=float(res)))
    return lines


def robust_fit(sides):
    """sides: list of (t, r) arrays (position along a trial direction, offset across it) of the px near a trial line.
    Per 1 px step of t, the median r; a least-squares line r = a + b t through the medians of all sides, and of each side
    alone. Returns (a, b, rms of the medians about the line, [(a, b) per side], width = px per step) or None"""
    T_, R_, per = [], [], []; npx = 0; nst = 0
    for t, r in sides:
        if len(t) < 3: return None
        k = np.floor(t).astype(int); o = np.argsort(k); k, rr = k[o], r[o]; uk, st = np.unique(k, return_index=True)
        med = np.array([np.median(x) for x in np.split(rr, st[1:])])
        if len(uk) < 4: return None
        bb, aa = np.polyfit(uk + 0.5, med, 1); per.append((aa, bb)); T_.append(uk + 0.5); R_.append(med); npx += len(t); nst += len(uk)
    T_ = np.concatenate(T_); R_ = np.concatenate(R_); b, a = np.polyfit(T_, R_, 1)
    res = float(np.sqrt(((R_ - (a + b * T_)) ** 2).mean()))
    return a, b, res, per, npx / max(1, nst)


def stub_lines(LBw, box, ink, lines):
    """lines that come in from ONE side of the box (a lot line ending at a block line inside a figure, a line ending at the
    figure, two lines that meet a figure offset from each other). Fitted from the line ink on that side only (as in
    cross_lines: a run of ink on x_cov of the first x_run px out of the box, straight), then followed into the box along
    the fitted line while there is ink within 1 px of it (a paper gap of 2 px ends it). Returns dict(p, u, w, s0, s1): the
    line and the stretch (s0..s1 along u) it covers inside the box"""
    x0, y0, x1, y1 = box; g = P['x_out']; H, W = LBw.shape
    out_ = LBw.copy(); out_[max(0, y0 - g):y1 + g, max(0, x0 - g):x1 + g] = 0
    ys, xs = np.nonzero(out_)
    if len(xs) < P['x_min']: return []
    pts = np.c_[xs + 0.5, ys + 0.5]; out = []
    for sc, side, th, r in line_cands(pts, box, False):
        S = side_px(pts, th, r, box, side)
        if S is None: continue
        sd, t, rr, dist, u, n_, ta, tb = S
        if sd.sum() < P['x_min'] or coverage(sd, dist) < P['x_cov']: continue
        fit = robust_fit([(t[sd], rr[sd])])
        if fit is None: continue
        a, b, res, _, w = fit
        if abs(np.degrees(np.arctan(b))) > 4: continue
        if w > P['x_maxw'] or res > max(P['x_rms'], 0.45 * w): continue
        tm = float(t[sd].mean()); d = u + b * n_; d = d / np.linalg.norm(d); c = tm * u + (a + b * tm) * n_; nn = np.array([-d[1], d[0]])
        # the same as a crossing line?
        if any(np.degrees(np.arccos(min(1.0, abs(float(d @ L_['u']))))) <= 3 and abs(float((c - L_['p']) @ np.array([-L_['u'][1], L_['u'][0]]))) <= 3 for L_ in lines): continue
        q = pts[sd]; sq = (q - c) @ d
        # walk into the box from the near end of the outside stretch, to the far end of the box at most
        if side == 0: s_from, step, s_lim = sq.max(), 1.0, (tb + g) - tm
        else: s_from, step, s_lim = sq.min(), -1.0, (ta - g) - tm
        s_cur = s_from; miss = 0; last = s_from
        while (s_cur - s_lim) * step < 0:
            s_cur += step; p_ = c + d * s_cur; hit = False
            for o in (-1.0, 0.0, 1.0):
                qq = p_ + nn * o; qx, qy = int(qq[0]), int(qq[1])
                if 0 <= qx < W and 0 <= qy < H and ink[qy, qx]: hit = True; break
            if hit: miss = 0; last = s_cur
            else:
                miss += 1
                if miss >= 2: break
        out.append(dict(p=c, u=d, w=float(w), s0=float(min(s_from, last)), s1=float(max(s_from, last)), side=side))
    return out


def carries_on(Q, i, lineref):
    """is piece i elongated (el_ratio x as long as thick) with line ink (lineref, not the piece) along its axis beyond
    either end, at co_hits or more of the probe steps 2-14 px out (a line crossing the end at a right angle is hit at 2-3
    steps only)"""
    x, y, w, h = int(Q['x'][i]), int(Q['y'][i]), int(Q['w'][i]), int(Q['h'][i])
    ys, xs = np.nonzero(Q['lb'][y:y + h, x:x + w] == i); xs = xs + x + 0.5; ys = ys + y + 0.5
    c = np.c_[xs, ys]; m = c.mean(0); cv = np.cov((c - m).T); ev, V = np.linalg.eigh(cv)
    L = np.sqrt(12 * ev[1] + 1); T_ = np.sqrt(12 * max(ev[0], 0) + 1)
    u = V[:, 1]; nn = np.array([-u[1], u[0]]); t = (c - m) @ u; H, W = lineref.shape
    own = Q['lb'] == i
    if L < P['el_ratio'] * T_:
        # a short heavy bar between two lines that run on past the same end along both its edges: the fill of a
        # double line (a streetcar track's heavy dash next to a letter), not a figure part
        if L < 1.2 * T_: return False
        for end, sgn in ((t.max(), 1), (t.min(), -1)):
            both = True
            for side_ in (-1, 1):
                hits = 0
                for d in range(2, 15, 2):
                    hit = False
                    for o in (T_ / 2 - 3, T_ / 2 - 2, T_ / 2 - 1, T_ / 2):
                        q = m + u * (end + sgn * d) + nn * o * side_; qx, qy = int(q[0]), int(q[1])
                        if 0 <= qx < W and 0 <= qy < H and lineref[qy, qx] and not own[qy, qx]: hit = True; break
                    hits += hit
                both &= hits >= P['co_hits'] * 7
            if both: return True
        return False
    offs = np.arange(-T_ / 2, T_ / 2 + 0.01, 1.5) if T_ > 3 else np.array([-1.5, 0, 1.5])   # across the whole bar
    for end, sgn in ((t.max(), 1), (t.min(), -1)):
        steps = range(2, 15, 2); hits = 0
        for d in steps:
            hit = False
            for o in offs:
                q = m + u * (end + sgn * d) + nn * o; qx, qy = int(q[0]), int(q[1])
                if 0 <= qx < W and 0 <= qy < H and lineref[qy, qx] and not own[qy, qx]: hit = True; break
            hits += hit
        if hits >= P['co_hits'] * len(steps): return True
    return False


def dash_like(Q, i, ink):
    """piece i is elongated (el_ratio x as long as thick, at most 70 px long), slanted more than 12 deg from upright, and
    beyond a gap of 3 px or more past either end there is a run of 8 px or more of ink along its axis (within 1.5 px)
    within 45 px: a dash of a dashed line (block figures stand upright; a figure 1 is never this)"""
    x, y, w, h = int(Q['x'][i]), int(Q['y'][i]), int(Q['w'][i]), int(Q['h'][i])
    ys, xs = np.nonzero(Q['lb'][y:y + h, x:x + w] == i); c = np.c_[xs + x + 0.5, ys + y + 0.5]; m = c.mean(0)
    ev, V = np.linalg.eigh(np.cov((c - m).T)); L = np.sqrt(12 * ev[1] + 1); T_ = np.sqrt(12 * max(ev[0], 0) + 1)
    if L < P['el_ratio'] * T_ or L > 70: return False
    u = V[:, 1]
    if abs(u[0]) < np.sin(np.radians(12)): return False
    nn = np.array([-u[1], u[0]]); t = (c - m) @ u; H, W = ink.shape; own = Q['lb'] == i
    for end, sgn in ((t.max(), 1), (t.min(), -1)):
        hits = []
        for d in range(1, 46):
            hit = False
            for o in (-1.5, 0, 1.5):
                q = m + u * (end + sgn * d) + nn * o; qx, qy = int(q[0]), int(q[1])
                if 0 <= qx < W and 0 <= qy < H and ink[qy, qx] and not own[qy, qx]: hit = True; break
            hits.append(hit)
        hits = np.array(hits); k = 0
        while k < len(hits) and hits[k]: k += 1          # ink right at the end (a joined line or letter): not a gap
        gap = 0
        while k < len(hits) and not hits[k]: k += 1; gap += 1
        run = 0
        while k < len(hits) and hits[k]: k += 1; run += 1
        if gap >= 3 and run >= 8: return True
    return False


def is_curve(Q, members, extra):
    """the word is ONE connected stroke (its pieces joined across the crossing strips) whose stroke length (area / stroke
    width) is less than curve_r x its larger side, and it is not an upright bar (a figure 1): an arc or a bent stretch of a
    heavy line. A figure or a letter turns more (2, 3, 5, C, S: 2 x or more; L, V, T about 1.7-2)"""
    m = np.isin(Q['lb'], members).astype(np.uint8); ys, xs = np.nonzero(m)
    # one group: the pieces joined across gaps of 6 px or less (a crossing strip is 3-5 px wide)
    n, gl = cv2.connectedComponents(cv2.dilate(m, np.ones((7, 7), np.uint8)), connectivity=8)
    if n - 1 != 1: return False
    ext = max(xs.max() - xs.min() + 1, ys.max() - ys.min() + 1)
    A = float(sum(Q['A'][i] for i in members)); sw = float(np.average([Q['sw'][i] for i in members], weights=[Q['A'][i] for i in members]))
    if A / max(sw, 1) >= P['curve_r'] * ext: return False
    c = np.c_[xs, ys].astype(float); cm = c.mean(0); ev, V = np.linalg.eigh(np.cov((c - cm).T)); u = V[:, 1]
    upright_bar = abs(u[0]) <= np.sin(np.radians(10)) and np.sqrt(12 * ev[1] + 1) >= 3 * np.sqrt(12 * max(ev[0], 0) + 1)
    return not upright_bar


def ring_groups(Q, members, extra):
    """the members that make up a round symbol: pieces grouped by touching within 3 px, each group tested by is_ring"""
    if not members: return []
    m = np.isin(Q['lb'], members).astype(np.uint8)
    n, gl = cv2.connectedComponents(cv2.dilate(m | (extra > 0).astype(np.uint8), np.ones((7, 7), np.uint8)), connectivity=8)
    grp = {}
    for i in members:
        ys, xs = np.nonzero(Q['lb'] == i); grp.setdefault(int(gl[ys[0], xs[0]]), []).append(i)
    out = []
    for g_, mem in grp.items():
        if is_ring(Q, mem, extra & (gl == g_)): out += mem
    return out


def is_ring(Q, members, extra, ar=None):
    """a round symbol (manhole or sewer circle, alarm circle): the word's pieces (with the crossing strips' core between
    them) close round a hole of ring_hole or more of the outline's area, outline about circular (hull 4 pi A / P^2 >=
    0.8, width / height within 1 / ring_ar .. ring_ar), ring_min px or more across. Bold figures 0, 6, 8, 9 are taller than
    wide (about 1.4-1.7)"""
    ar_ = ar; m = (np.isin(Q['lb'], members) | (extra > 0)).astype(np.uint8)
    ys, xs = np.nonzero(np.isin(Q['lb'], members))
    if not len(xs): return False
    x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1; m = m[y0:y1, x0:x1]
    if max(x1 - x0, y1 - y0) < P['ring_min']: return False
    ar = (x1 - x0) / max(1, (y1 - y0))
    if not (1 / (ar_ or P['ring_ar']) <= ar <= (ar_ or P['ring_ar'])): return False
    cs, _ = cv2.findContours(np.pad(m, 2), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if not cs: return False
    c = max(cs, key=cv2.contourArea); hull = cv2.convexHull(c); ha = cv2.contourArea(hull); hp = cv2.arcLength(hull, True)
    if 4 * np.pi * ha / max(1, hp * hp) < 0.8: return False
    return (ha - m.sum()) >= P['ring_hole'] * ha


def free_figures(Q, members, extra, nonstrip, FC0, Q0, off):
    """a figure word that finder3 found nowhere (no anchor) is taken only when it looks like bold upright figures standing
    free of lines once the crossing lines are taken out: height free_H, stroke free_sw, not a round symbol, 1 to 3
    figures (columns of ink) each free_full or more of the word's height and free_ar or more as tall as wide (a lone bar
    is a figure 1: upright within 8 deg, touching no line ink, and no like bar on its axis within 300 px: a dash of a
    dashed line or a streetcar track), and free_contacts or fewer places where it touches line ink other than the
    crossing lines (a block line junction or a wall corner touches lines all round). Returns (ok, why, features)"""
    m = np.array(members); wm = np.isin(Q['lb'], m)
    ys, xs = np.nonzero(wm); x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1; H = y1 - y0
    sw = float(np.average(Q['sw'][m], weights=Q['A'][m])); ff = {}
    if not (P['free_H'][0] <= H <= P['free_H'][1]): return False, 'height', ff
    if not (P['free_sw'][0] <= sw <= P['free_sw'][1]): return False, 'stroke', ff
    if is_ring(Q, members, extra, ar=P['free_ring_ar']): return False, 'ring', ff
    colp = wm[y0:y1, x0:x1].any(0); cols = []; c0 = None
    for i, v in enumerate(np.r_[colp, False]):
        if v and c0 is None: c0 = i
        if not v and c0 is not None: cols.append((c0, i)); c0 = None
    figs = []
    for a, b in cols:
        if b - a < 4: continue
        yy = np.nonzero(wm[y0:y1, x0 + a:x0 + b].any(1))[0]; figs.append((b - a, yy.max() - yy.min() + 1))
    ff['figs'] = [[int(w_), int(h_)] for w_, h_ in figs]
    if not (1 <= len(figs) <= 3): return False, 'figures', ff
    if any(h_ < P['free_full'] * H for w_, h_ in figs): return False, 'figure_height', ff
    bars = [w_ <= 0.35 * h_ for w_, h_ in figs]
    if any(h_ < P['free_ar'] * w_ for w_, h_ in figs): return False, 'figure_shape', ff
    near = cv2.dilate(wm.astype(np.uint8), E(5)) > 0
    nc = cv2.connectedComponents((near & nonstrip & ~wm).astype(np.uint8), connectivity=8)[0] - 1; ff['contacts'] = int(nc)
    if nc > P['free_contacts']: return False, 'contacts', ff
    if len(figs) == 1 and bars[0]:
        if nc > 0: return False, 'bar_contact', ff
        c = np.c_[xs, ys].astype(float); cm = c.mean(0); _, V = np.linalg.eigh(np.cov((c - cm).T)); u = V[:, 1]
        if abs(u[0]) > np.sin(np.radians(8)): return False, 'bar_slant', ff
        # like bars on the same vertical within 300 px (whole-plate pieces of the core less long lines)
        gx = cm[0] + off[0]; gy = cm[1] + off[1]
        cx = Q0['x'] + Q0['w'] / 2; cy = Q0['y'] + Q0['h'] / 2
        like = (np.abs(cx - gx) <= 6) & (np.abs(cy - gy) >= H) & (np.abs(cy - gy) <= 300) & (Q0['h'] >= 0.5 * H) & (Q0['w'] <= 0.5 * Q0['h'])
        if like.any(): return False, 'bar_row', ff
    return True, 'free', ff


def accept(Q, members, f0=None):
    """is this group of pieces a bold upright figure word? Returns (ok, why, features)"""
    m = np.array(members)
    x0 = Q['x'][m].min(); y0 = Q['y'][m].min(); x1 = (Q['x'][m] + Q['w'][m]).max(); y1 = (Q['y'][m] + Q['h'][m]).max()
    H, W = int(y1 - y0), int(x1 - x0); A = Q['A'][m].sum()
    anc = float((Q['txt'][m] * Q['A'][m]).sum() / max(A, 1))
    sw = float(np.average(Q['sw'][m], weights=Q['A'][m]))
    f = dict(fbox=[int(x0), int(y0), int(x1), int(y1)], H=H, W=W, A=int(A), anchor=round(anc, 3), sw=round(sw, 2),
             dens=round(A / max(1, H * W), 3), n=int(len(m)))
    if not (P['H'][0] <= H <= P['H'][1]): return False, 'height', f
    if W > P['WH'] * H: return False, 'wide', f
    if not (P['dens'][0] <= f['dens'] <= P['dens'][1]): return False, 'density', f
    if not (P['sw'][0] <= sw <= P['sw'][1]): return False, 'stroke', f
    if anc >= P['anchor']: return True, 'anchor', f
    return False, 'no_anchor', f


def apply(N, codes, gray=None, scale_ft=None, debug=None, return_info=False, **opts):
    """The post-step. codes: finder3's code image (uint8 0-5, whole plate or a window). gray: the scan's Lab L channel
    (not used: ink is codes > 0, which equals L < 140 on the paper; checked by the CLI). scale_ft: from scale_table.json
    (recorded; the rules are the same at every scale). opts: any key of P. Returns the new codes (uint8, codes 0-5), or
    (new codes, info) with return_info=True."""
    keep = dict(P); P.update(opts)
    try: out, info = _apply(N, codes, scale_ft, debug)
    finally: P.clear(); P.update(keep)
    return (out, info) if return_info else out


def _apply(N, codes, scale_ft, debug):
    t0 = time.time(); T = {}
    ink = (codes > 0).astype(np.uint8)
    core = cv2.morphologyEx(ink, cv2.MORPH_OPEN, E(P['core_d'])); T['core'] = time.time() - t0
    LB = straight(ink, P['band_len'], P['band_angles']); T['band'] = time.time() - t0
    # streetcar dashes: heavy straight bars with another such bar in line within 280 px (finder2.heavy_bars, grown 9 px)
    bars = finder2.heavy_bars(ink) if P['bars'] else np.zeros_like(ink); T['bars'] = time.time() - t0
    FC0 = (core & (1 - LB)).astype(np.uint8)
    Q0 = pieces(FC0, codes); T['pieces'] = time.time() - t0
    # rough words are made of substantial pieces only (small core bits at line junctions and of lot figures stay out)
    keep = Q0['A'] >= P['join_A']; keep[0] = False
    uf = group(Q0, keep)
    rough = {}
    for i in np.nonzero(keep)[0]: rough.setdefault(uf.f(i), []).append(int(i))
    out = codes.copy(); Hh, Ww = codes.shape; changes = []; whys = {}; done = np.zeros(codes.shape, bool)
    for r_, mem in rough.items():
        m = np.array(mem)
        x0 = Q0['x'][m].min(); y0 = Q0['y'][m].min(); x1 = (Q0['x'][m] + Q0['w'][m]).max(); y1 = (Q0['y'][m] + Q0['h'][m]).max()
        if not (P['rough_H'][0] <= y1 - y0 <= P['rough_H'][1]) or (x1 - x0) > 1.5 * P['WH'] * (y1 - y0):
            whys['rough'] = whys.get('rough', 0) + 1; continue
        if (Q0['txt'][m] * Q0['A'][m]).sum() < 1 and False: continue
        x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
        g = P['pad']; X0, Y0, X1, Y1 = max(0, x0 - g), max(0, y0 - g), min(Ww, x1 + g), min(Hh, y1 + g)
        bx = (int(x0 - X0), int(y0 - Y0), int(x1 - X0), int(y1 - Y0))
        s_ink = ink[Y0:Y1, X0:X1]; s_core = core[Y0:Y1, X0:X1]; s_LB = LB[Y0:Y1, X0:X1]; s_codes = codes[Y0:Y1, X0:X1]
        s_src = ((s_LB > 0) | (s_codes == 1)).astype(np.uint8) if P['src_code1'] else s_LB
        lines = cross_lines(s_src, bx)
        strip = np.zeros_like(s_ink); hh, ww = s_ink.shape
        yy, xx = np.mgrid[0:hh, 0:ww]; pc = np.c_[xx.ravel() + 0.5, yy.ravel() + 0.5]
        for L_ in lines:
            nn = np.array([-L_['u'][1], L_['u'][0]]); d = np.abs((pc - L_['p']) @ nn).reshape(hh, ww)
            strip |= (d <= L_['w'] / 2 + P['strip_m']).astype(np.uint8)
        # lines that come in from one side: their thin ink inside the box (not the core: a stroke they run into stays
        # the figure's) is line ink too
        stub = np.zeros_like(s_ink); stubs = stub_lines(s_src, bx, s_ink, lines) if P['stubs'] else []
        for L_ in stubs:
            nn = np.array([-L_['u'][1], L_['u'][0]]); rel = pc - L_['p']; d = np.abs(rel @ nn).reshape(hh, ww); sa = (rel @ L_['u']).reshape(hh, ww)
            stub |= ((d <= L_['w'] / 2 + P['strip_m']) & (sa >= L_['s0'] - 2) & (sa <= L_['s1'] + 1)).astype(np.uint8)
        # (a heavy stub, as wide as a stroke, is cut out of the core too: a heavy line stopping at a figure, a track
        # end under a letter)
        heavy = np.zeros_like(s_ink)
        for L_ in stubs:
            if L_['w'] < P['stub_heavy']: continue
            nn = np.array([-L_['u'][1], L_['u'][0]]); rel = pc - L_['p']; d = np.abs(rel @ nn).reshape(hh, ww); sa = (rel @ L_['u']).reshape(hh, ww)
            heavy |= ((d <= L_['w'] / 2 + P['strip_m']) & (sa >= L_['s0'] - 2) & (sa <= L_['s1'] + 1)).astype(np.uint8)
        stub = (stub & (1 - s_core)) | heavy
        strip = strip | heavy
        gb = P['box_g']; inbox = np.zeros_like(s_ink); inbox[max(0, bx[1] - gb):bx[3] + gb, max(0, bx[0] - gb):bx[2] + gb] = 1
        # the line ink that stays line: crossing strips, stubs, and the long lines outside the box
        lineish = (strip > 0) | (stub > 0) | ((s_LB > 0) & (inbox == 0))
        # the figure core: the rough word's pieces, the other pieces of the core less the long lines inside the box, and
        # long-line core within near_d px of the word's pieces (a thick stroke that a tilted long line ran through), less
        # the crossing strips
        s_FC0 = FC0[Y0:Y1, X0:X1]; wlab = Q0['lb'][Y0:Y1, X0:X1]
        word = np.isin(wlab, m).astype(np.uint8)
        nd = P['near_d']; near = cv2.dilate(word, E(2 * nd + 1)); near[:max(0, bx[1]), :] = 0; near[bx[3]:, :] = 0; near[:, :max(0, bx[0])] = 0; near[:, bx[2]:] = 0
        # (only bits of it that stay inside the box: a thick line running out of the box between two figures is a line)
        nb_ = (s_core & s_LB & near & inbox & (1 - strip)).astype(np.uint8)
        if nb_.any():
            k_, kl = cv2.connectedComponents(nb_, connectivity=8)
            rim = inbox - cv2.erode(inbox, np.ones((3, 3), np.uint8)); bad = np.unique(kl[(rim > 0) & (kl > 0)])
            nb_[np.isin(kl, bad)] = 0
        FC = (s_core & inbox & (1 - strip) & (s_FC0 | nb_)).astype(np.uint8)
        Q = pieces(FC, s_codes)
        mem2 = [i for i in range(1, Q['n']) if Q['A'][i] >= P['min_area']]
        # a piece that is not text yet and carries on a line along its own axis is a piece of that line (a heavy stretch
        # of a line, a wall stub), not a figure
        # (a crossing line's own strip does not count: a figure 1 standing along a lot line is left beside the strip, and
        # the line runs on along its axis above and below)
        lineref = (((s_LB > 0) | (s_codes == 1)) & ~(cv2.dilate(strip, E(5)) > 0)).astype(np.uint8)
        s_bars = bars[Y0:Y1, X0:X1]
        inb = np.bincount(Q['lb'][(s_bars > 0) & (Q['lb'] > 0)], minlength=Q['n']) / np.maximum(Q['A'], 1)
        dropped = [i for i in mem2 if Q['txt'][i] < P['own_anchor'] and (inb[i] >= 0.5 or carries_on(Q, i, lineref))]
        # ... nor a heavy dash with another stroke in line with it beyond a gap (a dashed line), unless upright
        inkx = (s_ink & ~(cv2.dilate(strip, E(5)) > 0)).astype(np.uint8)
        dropped += [i for i in mem2 if i not in dropped and Q['txt'][i] < P['own_anchor'] and dash_like(Q, i, inkx)]
        mem2 = [i for i in mem2 if i not in dropped]
        # round symbols (manhole, sewer and alarm circles) among the pieces are taken out, group by group
        rings = ring_groups(Q, mem2, strip & s_core); mem2 = [i for i in mem2 if i not in rings]
        if not mem2: whys['empty'] = whys.get('empty', 0) + 1; continue
        # pieces not yet text must lie in the band of the pieces that are (the figures stand in one row)
        anc_p = [i for i in mem2 if Q['txt'][i] >= P['band_anchor']]
        # (a figure cut by a line has its other part above or below: the pieces stacked on a text piece join the band)
        for _ in range(2):
            for j in mem2:
                if j in anc_p: continue
                for i in list(anc_p):
                    hov = min(Q['x'][i] + Q['w'][i], Q['x'][j] + Q['w'][j]) - max(Q['x'][i], Q['x'][j])
                    vg = max(Q['y'][i], Q['y'][j]) - min(Q['y'][i] + Q['h'][i], Q['y'][j] + Q['h'][j])
                    if hov >= 0.5 * min(Q['w'][i], Q['w'][j]) and vg <= P['stack_gap']: anc_p.append(j); break
        if anc_p and P['band']:
            ya0 = min(Q['y'][i] for i in anc_p); ya1 = max(Q['y'][i] + Q['h'][i] for i in anc_p); Ha = ya1 - ya0
            xa0 = min(Q['x'][i] for i in anc_p); xa1 = max(Q['x'][i] + Q['w'][i] for i in anc_p); tb_ = P['band_tol'] * Ha
            out_band = [i for i in mem2 if i not in anc_p and not (Q['y'][i] >= ya0 - tb_ and Q['y'][i] + Q['h'][i] <= ya1 + tb_
                        and Q['x'][i] >= xa0 - P['band_x'] * Ha and Q['x'][i] + Q['w'][i] <= xa1 + P['band_x'] * Ha)]
            mem2 = [i for i in mem2 if i not in out_band]
        else: out_band = []
        if not mem2: whys['empty'] = whys.get('empty', 0) + 1; continue
        ok, why, f = accept(Q, mem2)
        f['dropped_line_pieces'] = len(dropped); f['ring_pieces'] = len(rings); f['out_of_band'] = len(out_band)
        # one smooth heavy stroke (a curved street or curb line, an arc), not a group of figures
        if why in ('anchor', 'no_anchor') and P['curve'] and is_curve(Q, mem2, strip & s_core): ok, why = False, 'curve'
        if not ok and why == 'no_anchor' and P['free']:
            nonstrip = ((s_LB > 0) | (s_codes == 1)) & ~(cv2.dilate(strip, E(7)) > 0)
            ok, why2, ff = free_figures(Q, mem2, strip & s_core, nonstrip, FC0, Q0, (X0, Y0))
            f.update(ff); why = 'free' if ok else 'free_' + why2
        f['box'] = [int(x0), int(y0), int(x1), int(y1)]; f['lines'] = [dict(w=round(L_['w'], 1), n=L_['n'], ang=round(float(np.degrees(np.arctan2(L_['u'][1], L_['u'][0]))) % 180, 1)) for L_ in lines]; f['stubs'] = len(stubs)
        f['fbox'] = [f['fbox'][0] + X0, f['fbox'][1] + Y0, f['fbox'][2] + X0, f['fbox'][3] + Y0]
        whys[why] = whys.get(why, 0) + 1
        if debug is not None: debug.setdefault('words', []).append(dict(f, ok=ok, why=why, win=[X0, Y0, X1, Y1], strip=strip, lb=Q['lb'], members=mem2))
        if not ok: continue
        thin = s_ink & (1 - s_core)
        ts = straight(thin, P['ts_len'], P['ts_angles'])
        allow = ((s_ink > 0) & ~lineish & (ts == 0)).astype(np.uint8)
        if P['grow_noLB']: allow &= (1 - s_LB)   # never grow into long-line ink (in the box too); the core seeds keep theirs
        seed = np.isin(Q['lb'], mem2).astype(np.uint8); reg = seed.copy()
        for _ in range(P['grow']): reg = (cv2.dilate(reg, np.ones((3, 3), np.uint8)) & allow) | seed
        sub = out[Y0:Y1, X0:X1]; old = s_codes
        new = (reg > 0) & np.isin(old, (1, 4, 5)) & ~done[Y0:Y1, X0:X1] & (s_bars == 0)   # never a streetcar dash
        stay = lineish | (ts > 0) | ((old == 1) & (reg == 0))
        touch = new & (cv2.dilate(stay.astype(np.uint8), np.ones((2 * P['touch_r'] + 1, 2 * P['touch_r'] + 1), np.uint8)) > 0)
        sub[new] = CODE['sure']; sub[touch] = CODE['shared']; done[Y0:Y1, X0:X1] |= reg > 0
        ch = dict(f, to_text=int((new & ~touch).sum()), to_shared=int(touch.sum()),
                  from_codes={str(v): int((new & (old == v)).sum()) for v in (1, 4, 5)})
        if ch['to_text'] or ch['to_shared']: changes.append(ch)
    T['words'] = time.time() - t0
    info = dict(plate=N, scale_ft=scale_ft, params=dict(P), rough_words=len(rough), why=whys, changed_words=len(changes),
                px_to_text=int(sum(c['to_text'] for c in changes)), px_to_shared=int(sum(c['to_shared'] for c in changes)),
                seconds={k: round(v, 1) for k, v in T.items()}, changes=changes)
    if debug is not None: debug.update(LB=LB, core=core)
    return out, info


def scale_of(N):
    try: return int(json.load(open('scale_table.json', encoding='utf8'))[N]['ft_per_inch'])
    except Exception: return None


def load_gray(N):
    im = cv2.imread(f'cufp/22-{N}.jpg'); H, W = im.shape[:2]
    al = np.load(f'cufp/{N}/png_alpha_s4.npy'); paper = cv2.resize(al.astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST) > 0
    return cv2.cvtColor(im, cv2.COLOR_BGR2LAB)[..., 0], paper


def main():
    a = sys.argv; N = a[1]
    src = a[a.index('--in') + 1]; dst = a[a.index('--out') + 1]
    win = tuple(int(v) for v in a[a.index('--win') + 1:a.index('--win') + 5]) if '--win' in a else None
    opts = {}
    for i, v in enumerate(a):
        if v == '--set':
            k, val = a[i + 1].split('=', 1); opts[k] = json.loads(val)
    t0 = time.time()
    codes = cv2.imread(os.path.join(src, f'{N}_text.png'), cv2.IMREAD_UNCHANGED)
    gray, paper = load_gray(N)
    ink = (gray < 140) & paper
    if not np.array_equal(ink, codes > 0): print(f'warning: plate {N}: codes > 0 differs from the ink (L < 140 on paper) at {int((ink != (codes > 0)).sum())} px', flush=True)
    if win:
        x0, y0, x1, y1 = win; codes = codes[y0:y1, x0:x1]; gray = gray[y0:y1, x0:x1]
    out, info = apply(N, codes, gray, scale_of(N), return_info=True, **opts)
    info['win'] = win; info['input'] = os.path.abspath(os.path.join(src, f'{N}_text.png')); info['total_s'] = round(time.time() - t0, 1)
    info['px_in'] = {str(v): int((codes == v).sum()) for v in range(6)}; info['px_out'] = {str(v): int((out == v).sum()) for v in range(6)}
    os.makedirs(dst, exist_ok=True)
    cv2.imwrite(os.path.join(dst, f'{N}_text.png'), out)
    with open(os.path.join(dst, f'{N}_text.json'), 'w', encoding='utf8', newline='\n') as f: json.dump(info, f, indent=1)
    print(f"blockfix {N}: rough words {info['rough_words']} {info['why']} | changed {info['changed_words']} words, +{info['px_to_text']} px text, +{info['px_to_shared']} px shared | {info['total_s']} s", flush=True)


if __name__ == '__main__':
    main()
