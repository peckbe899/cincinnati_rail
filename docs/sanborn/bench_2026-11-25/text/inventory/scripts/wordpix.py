"""The text pixels of one word, by the same rules as build_truth.py (kept in step by hand: same snap margins, same line
kernel, same 2 px line edge), and the glyph measurements used by measure.py.

word_pixels(ink, off, geo, flags) -> dict(cx, cy, L, h, ang, text, line, box, sub)   (local window arrays)
glyph_stats(text, line, cx, cy, ang, reading) -> dict of measurements (see measure.py's docstring)"""
import math
import numpy as np, cv2
from common import line_mask


def in_rect(xs, ys, cx, cy, L, h, ang):
    a = math.radians(ang); u = (math.cos(a), math.sin(a)); v = (-math.sin(a), math.cos(a))
    dx, dy = xs - cx, ys - cy; al = dx * u[0] + dy * u[1]; ac = dx * v[0] + dy * v[1]
    return (np.abs(al) <= L / 2) & (np.abs(ac) <= h / 2), al, ac


def word_pixels(ink, off, geo, flags=()):
    """ink: bool array of a window whose top-left is off=(wx0, wy0) in plate px; geo: x1 y1 x2 y2 h (plate px)"""
    wx0, wy0 = off; hh, ww = ink.shape
    x1, y1, x2, y2, h = geo; ang = math.degrees(math.atan2(y2 - y1, x2 - x1)); L = math.hypot(x2 - x1, y2 - y1)
    cx, cy = (x1 + x2) / 2 - wx0, (y1 + y2) / 2 - wy0
    Lline = int(max(41, round(1.5 * h))) | 1
    R = int(L / 2 + h + Lline + 10)
    bx0, by0, bx1, by1 = max(0, int(cx - R)), max(0, int(cy - R)), min(ww, int(cx + R)), min(hh, int(cy + R))
    sub_ink = ink[by0:by1, bx0:bx1]; sub_ln = line_mask(sub_ink, Lline, nang=72)
    yy, xx = np.mgrid[by0:by1, bx0:bx1].astype(float)
    mg_a, mg_c = 0.15 * h + 4, 0.15 * h + 3; snapped = False
    if 'nosnap' not in flags:
        cand = sub_ink & ~(cv2.dilate(sub_ln.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0)
        n, lb, st, _ = cv2.connectedComponentsWithStats(cand.astype(np.uint8), connectivity=8)
        inw, al, ac = in_rect(xx, yy, cx, cy, L + 2 * mg_a, h + 2 * mg_c, ang)
        tot = np.bincount(lb.ravel(), minlength=n); ins = np.bincount(lb.ravel(), inw.ravel(), minlength=n)
        ok = (ins >= 0.7 * tot) & (tot >= 3); ok[0] = False
        sel = ok[lb] & inw
        if sel.sum() >= 8:
            a1, c1 = al[sel], ac[sel]
            lo, hi, clo, chi = a1.min(), a1.max(), c1.min(), c1.max()
            s_a, s_c = 0.25 * h, 0.2 * h
            lo, hi = min(lo, -L / 2 + s_a), max(hi, L / 2 - s_a); clo, chi = min(clo, -h / 2 + s_c), max(chi, h / 2 - s_c)
            a = math.radians(ang); u = np.array([math.cos(a), math.sin(a)]); v = np.array([-math.sin(a), math.cos(a)])
            ctr = np.array([cx, cy]) + u * (lo + hi) / 2 + v * (clo + chi) / 2
            cx, cy = ctr; L = hi - lo + 2; h = chi - clo + 2; snapped = True
    inw, al, ac = in_rect(xx, yy, cx, cy, L + 3, h + 3, ang)
    n, lb, st, _ = cv2.connectedComponentsWithStats(sub_ln.astype(np.uint8), connectivity=8)
    outside = np.bincount(lb.ravel(), (~in_rect(xx, yy, cx, cy, L + 8, h + 8, ang)[0]).ravel(), minlength=n) > 0; outside[0] = False
    lpx = (cv2.dilate(outside[lb].astype(np.uint8), np.ones((5, 5), np.uint8)) > 0) & sub_ink
    t = sub_ink & inw & ~lpx
    return dict(cx=cx - bx0, cy=cy - by0, L=L, h=h, ang=ang, text=t, line=lpx, inbox=inw, sub=(bx0, by0, bx1, by1), snapped=snapped,
                plate_box=(cx + wx0, cy + wy0, L, h, ang))


def glyph_stats(text, line, cx, cy, ang, reading, lab=None, inbox=None):
    """text, line: local bool masks; (cx, cy) word centre in local px; lab: local Lab image (uint8, OpenCV scale)"""
    out = dict(text_px=int(text.sum()))
    if text.sum() < 10: return out
    ys, xs = np.nonzero(text)
    a = math.radians(ang); u = (math.cos(a), math.sin(a)); v = (-math.sin(a), math.cos(a))
    n, lb, st, _ = cv2.connectedComponentsWithStats(text.astype(np.uint8), connectivity=8)
    l = lb[ys, xs]; ac = (xs - cx) * v[0] + (ys - cy) * v[1]; al = (xs - cx) * u[0] + (ys - cy) * u[1]
    H = np.zeros(n); W = np.zeros(n); A = np.bincount(l, minlength=n)
    for k in range(1, n):
        m = l == k
        if m.sum(): H[k] = ac[m].max() - ac[m].min() + 1; W[k] = al[m].max() - al[m].min() + 1
    big = (A >= 12); big[0] = False
    if big.sum():
        ref = np.percentile(H[big], 90); full = big & (H >= 0.55 * ref)
        out['glyph_h'] = float(np.median(H[full])); out['n_glyph_comps'] = int(full.sum())
        out['glyph_w'] = float(np.median(W[full]))
    dt = cv2.distanceTransform(text.astype(np.uint8), cv2.DIST_L2, 5)
    sk = text & (dt >= cv2.dilate(dt, np.ones((3, 3), np.uint8)) - 1e-6)   # ridge of the distance transform: the stroke centre line
    if sk.sum(): out['stroke_w'] = float(2 * np.median(dt[sk]) - 1)
    nch = sum(ch.isalnum() for ch in reading)
    out['n_chars'] = int(nch)
    if nch and 'n_glyph_comps' in out: out['comps_per_char'] = round(out['n_glyph_comps'] / nch, 2)
    if line is not None:
        out['touches_line'] = bool((cv2.dilate(text.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0)[line].any())
        # share of glyph components joined to line ink
        if big.sum():
            near = cv2.dilate(line.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
            touch = np.bincount(lb.ravel(), near.ravel(), minlength=n) > 0
            out['glyphs_touching_line'] = round(float((touch & big).sum() / big.sum()), 3)
    if lab is not None:
        L_, A_, B_ = lab[..., 0][text], lab[..., 1][text], lab[..., 2][text]
        out['L'] = round(float(np.median(L_)) * 100 / 255, 1); out['a'] = round(float(np.median(A_)) - 128, 1); out['b'] = round(float(np.median(B_)) - 128, 1)
        core = text & (cv2.erode(text.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0)   # stroke centres: less blur from the paper
        if core.sum() >= 5:
            out['L_core'] = round(float(np.median(lab[..., 0][core])) * 100 / 255, 1); out['a_core'] = round(float(np.median(lab[..., 1][core])) - 128, 1)
            out['b_core'] = round(float(np.median(lab[..., 2][core])) - 128, 1)
    return out
