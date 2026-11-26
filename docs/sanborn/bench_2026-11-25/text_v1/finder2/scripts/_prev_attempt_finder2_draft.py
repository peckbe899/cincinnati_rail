"""Character finder, prototype (25 Nov 2026). Which ink on a Sanborn 1922 plate is a letter or a digit?

    cd data/sanborn
    python -B <this> N [--win X0 Y0 X1 Y1] [--out DIR] [--pic] [--tag NAME]

Rule-based, no download, no training, nothing fitted. Runs on the system python (cv2 4.13, numpy, scipy).
Reads only cufp/22-N.jpg and cufp/N/png_alpha_s4.npy. Writes only into --out (default: the finder folder's out/).

How (all sizes in full-size scan px, about 300 dpi; the lettering is the same size on 100, 200 and 400 ft plates):
  1. ink = Lab L < 140 on the paper (the same ink as ink_bins.py).
  2. LINE INK = ink that a straight 61 px line fits, at 48 angles (3.75 deg apart), tried on the ink grown by 1 px so a
     line a little off the angle still fits (as ink_bins.railroad does). The longest straight stroke of a house number
     or lot figure is about 30 px, of a street name about 50 px, so letters are mostly not line ink. Thick strokes
     (8 px or more across) that are line ink only for less than 131 px are given back: the stems of big lettering.
  3. The rest of the ink (less line ink grown by 1 px) falls apart into PIECES: separate glyphs, glyphs cut off the
     lines they touched, dashes, ticks, curve pieces, dots.
  4. Each piece gets shape features: area, length and thickness of the equivalent bar (second moments), stroke width
     (2 x distance to the paper along the ridge), holes (Euler number), stroke length (area / stroke width), how much of
     it touches line ink.
  5. Kinds:
       glyph    a 2-D shape of strokes (thicker than its stroke), 8-140 px long: a letter, a digit, or a few that touch
       cluster  a longer piece that is dense with strokes (stroke length 1.8 x its length or more): touching letters
       stroke   a straight bar as thin as its stroke: a figure 1, an I, a hyphen, a dash, a tick, a piece of a line
       blob     a filled dot 11 px or more (valves, hydrants)
       dot      under 12 px of ink or under 6 px long: full stops, primes, scan specks
       long     anything else over 140 px: line pieces, curves
  6. Strokes that chain end to end along their own axis (3 or more, or 2 spanning 50 px or more), or that carry on a
     line of line ink along their axis, are DASHES or LINE PIECES, never text.
  7. Text = glyphs and clusters (seeds), plus the strokes, dots and heavy bars that lie within 9 px of a seed (15 px of
     a big one); three rounds, so a row of figure 1s next to a digit is taken in. A lone thin stroke 12-45 px long that
     touches no line ink and is not a dash is a figure 1 or story mark ('lone', lower confidence).

Outputs (in --out): N_finder.png (one code per pixel, below), N_finder.json (counts, parameters, timings),
N_pieces.npz (every piece's features and kind), and with --pic a picture N_finder.jpg (half size).
Pixel codes: 0 paper, 1 line ink, 2 text: glyph/cluster, 3 text: stroke/dot taken in by a glyph, 4 text: lone stroke,
5 other ink not text (dashes, line pieces, ticks, blobs, curves, specks).
"""
import json, os, sys, time
import numpy as np
import cv2
from scipy.spatial import cKDTree
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

HERE = os.path.dirname(os.path.abspath(__file__))
P = dict(ink_L=140, line_len=61, angles=48, thick_d=8, thick_long=131, thick_bar=16, dot_area=12, dot_len=6, glyph_max=140,
         cluster_max=600, cluster_thick=(10, 70), cluster_density=1.8, stroke_thick=(1.6, 3.0), blob_len=11, blob_sw=0.55,
         sw_max=14, chain_ang=12, chain_gap=(30, 0.8), chain_span=50, cont_probe=12, cont_ang=2,
         r_small=9, r_big=15, big_seed=45, rounds=3, lone=(12, 45), lone_sw=7, heavy_sw=8,
         short_line=100, short_probe=48, short_free=8, box_rect=0.9, box_min=15, box_rect2=None, box_min2=12, jog_sw=5.5, jog_win=30, jog_al=0.6, jog_vd=5.0, ring=(0.6, 1.15, 18), bldg=(0.45, 6.0, 20), fill_edge=(0.7, 0.2, 7.0), eq=(5, 22, 3, 12),
         clus_r=4, clus_long=121, clus_ext=260)
CODE = dict(line=1, glyph=2, taken=3, lone=4, other=5)
COLOR = {1: (170, 170, 170), 2: (220, 0, 220), 3: (255, 120, 0), 4: (0, 160, 255), 5: (0, 150, 0)}   # BGR: grey, magenta, blue, orange, green


def line_kernel(length, ang):
    k = np.zeros((length, length), np.uint8); c = length // 2; d = np.array([np.cos(ang), np.sin(ang)]) * c
    cv2.line(k, tuple(np.round(c - d).astype(int).tolist()), tuple(np.round(c + d).astype(int).tolist()), 1, 1); return k


def load(N, win=None):
    im = cv2.imread(f'cufp/22-{N}.jpg'); H, W = im.shape[:2]
    al = np.load(f'cufp/{N}/png_alpha_s4.npy'); paper = cv2.resize(al.astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST) > 0
    x0, y0, x1, y1 = win or (0, 0, W, H)
    im = im[y0:y1, x0:x1]; paper = paper[y0:y1, x0:x1]
    L = cv2.cvtColor(im, cv2.COLOR_BGR2LAB)[..., 0]
    ink = ((L < P['ink_L']) & paper).astype(np.uint8)
    return im, ink, paper, (W, H)


def line_ink(ink):
    """ink that a straight line_len px line fits (on the ink grown 1 px), and which way (angle index) it runs"""
    fat = cv2.dilate(ink, np.ones((3, 3), np.uint8)); line = np.zeros_like(ink); ori = np.full(ink.shape, -1, np.int8)
    for i in range(P['angles']):
        o = cv2.morphologyEx(fat, cv2.MORPH_OPEN, line_kernel(P['line_len'], np.pi * i / P['angles'])) & ink
        ori[(o > 0) & (line == 0)] = i; line |= o
    # thick strokes (a thick_d disk fits) that are line ink for less than thick_long px: stems of big lettering, given back
    E = lambda k: cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
    thick = cv2.dilate(cv2.morphologyEx(ink, cv2.MORPH_OPEN, E(P['thick_d'])), E(3)) & ink
    tl = line & thick
    n, lb, st, _ = cv2.connectedComponentsWithStats(tl, connectivity=8)
    if n > 1:
        A, lg, th, mx, my, an = shape(lb, n)
        # only a single straight bar (as thin across as a stroke) that touches no thin line ink: a corner of a heavy wall
        # (plate 1A's brick buildings) is L-shaped, and a heavy line runs on as thin line ink. (Tried 25 Nov: 'no thin line
        # ink along its axis' only, so that a street name crossed by a pipe line keeps its stems: Ben's line ink called
        # text rose from 0.27-0.46% to 0.43-1.25% on 44, 1A, 5; dropped)
        back = (lg < P['thick_long']) & (th <= P['thick_bar']); back[0] = False
        thin = (line > 0) & (tl == 0); H, W = line.shape; g = 3
        for i in np.nonzero(back)[0]:
            x0, y0, bw, bh = st[i, 0], st[i, 1], st[i, 2], st[i, 3]; X0, Y0, X1, Y1 = max(0, x0 - g), max(0, y0 - g), min(W, x0 + bw + g), min(H, y0 + bh + g)
            if (cv2.dilate((lb[Y0:Y1, X0:X1] == i).astype(np.uint8), np.ones((2 * g + 1, 2 * g + 1), np.uint8)) & thin[Y0:Y1, X0:X1]).any(): back[i] = False
        m = back[lb] & (tl > 0); line[m] = 0; ori[m] = -1
    # a short piece of line ink on its own (less than short_line px, joined to no other line ink): a long stroke of a big
    # figure (block numbers are drawn some 70 px tall) or a short loose line; given back to be judged as a piece
    n, lb, st, _ = cv2.connectedComponentsWithStats(line, connectivity=8)
    if n > 1 and P.get('short_line'):
        A, lg, th, mx, my, an = shape(lb, n)
        back = (lg < P['short_line']) & (np.maximum(st[:, 2], st[:, 3]) < P['short_line'] + 10); back[0] = False
        # ... unless it lines up with other line ink beyond either end (a line broken by lettering or a gap)
        b = np.nonzero(back)[0]; H, W = line.shape
        if len(b):
            Pt = np.c_[mx[b], my[b]]; u = np.c_[np.cos(an[b]), np.sin(an[b])]; nrm = np.c_[-u[:, 1], u[:, 0]]
            ai = np.round(((an[b] % np.pi) / np.pi) * P['angles']).astype(int) % P['angles']; hit = np.zeros(len(b), bool)
            for s in (-1, 1):
                for d in range(4, P['short_probe'] + 1, 4):
                    for o in (-2, 0, 2):
                        q = Pt + s * u * (lg[b][:, None] / 2 + d) + o * nrm
                        qx = np.clip(np.round(q[:, 0]).astype(int), 0, W - 1); qy = np.clip(np.round(q[:, 1]).astype(int), 0, H - 1)
                        oo = ori[qy, qx].astype(int); dd = np.abs(((oo - ai + P['angles'] // 2) % P['angles']) - P['angles'] // 2)
                        hit |= (oo >= 0) & (lb[qy, qx] != b) & (dd <= 2)
            back[b[hit]] = False
            # ... or if any other line ink lies within short_free px of it (a short side between two lines it nearly meets)
            g = P['short_free']; ker = np.ones((2 * g + 1, 2 * g + 1), np.uint8)
            for i in np.nonzero(back)[0]:
                x0, y0, bw, bh = st[i, 0], st[i, 1], st[i, 2], st[i, 3]; X0, Y0 = max(0, x0 - g), max(0, y0 - g); X1, Y1 = min(W, x0 + bw + g), min(H, y0 + bh + g)
                sub = lb[Y0:Y1, X0:X1]; zone = cv2.dilate((sub == i).astype(np.uint8), ker)
                if ((zone > 0) & (sub > 0) & (sub != i)).any(): back[i] = False
        m = back[lb] & (line > 0); line[m] = 0; ori[m] = -1
    if P.get('clus_r'):
        line, ori = cluster_giveback(ink, fat, line, ori)
    return line, ori


def long_ink(fat, line, L):
    """line ink that a straight L px line fits (on the ink grown 1 px): the long, sure lines"""
    o = np.zeros_like(line)
    for i in range(P['angles']): o |= cv2.morphologyEx(fat, cv2.MORPH_OPEN, line_kernel(L, np.pi * i / P['angles']))
    return o & line


def cluster_giveback(ink, fat, line, ori):
    """finder2 (25 Nov 2026), BIG LETTERING. A big letter (street names 50-100 px, block numbers 50-85 px, adjoining sheet
    numbers 130-175 px) has strokes that a 61 px line fits, so step 2 takes them as line ink. v1 gave back only a short
    piece with no other line ink within 8 px, but a big letter's line ink comes in several pieces (the stem, the bowl, specks
    where a 61 px line just fits through two strokes), so that test failed on most big letters.
    Here the line ink is grouped into CLUSTERS (pieces within 2 clus_r px of each other). A cluster is given back, to be
    judged as pieces like any other ink, when
      - none of it is LONG line ink (a straight clus_long px line fits it: no letter stroke is that long), and
      - none of its pieces carries on a line beyond its ends (up to short_probe px along its axis: long line ink in the same
        direction, or a straight bar outside the cluster in the same direction: a dashed or broken line), and
      - the cluster is letter-sized (clus_ext px or less across).
    A cluster with long line ink in it (a letter touching a line, a building) stays line ink here."""
    H, W = line.shape
    lng = long_ink(fat, line, P['clus_long'])
    r = P['clus_r']
    cl_n, cl_lb, cl_st, _ = cv2.connectedComponentsWithStats(cv2.dilate(line, np.ones((2 * r + 1, 2 * r + 1), np.uint8)), connectivity=8)
    haslong = np.bincount(cl_lb[lng > 0], minlength=cl_n) > 0
    ext = np.maximum(cl_st[:, 2], cl_st[:, 3]) - 2 * r
    cand = ~haslong & (ext <= P['clus_ext']); cand[0] = False
    if not cand.any(): return line, ori
    n, lb, st, _ = cv2.connectedComponentsWithStats(line, connectivity=8)
    A, lg, th, mx, my, an = shape(lb, n)
    ys, xs = st[:, 1], st[:, 0]
    # cluster of each line piece (any pixel of it)
    pc = np.zeros(n, np.int64); yy, xx = np.nonzero(line); pc[lb[yy, xx]] = cl_lb[yy, xx]
    b = np.nonzero(cand[pc] & (np.arange(n) > 0))[0]
    if not len(b): return line, ori
    bar = (lg >= 30) & (lg >= 4 * th)
    Pt = np.c_[mx[b], my[b]]; u = np.c_[np.cos(an[b]), np.sin(an[b])]; nrm = np.c_[-u[:, 1], u[:, 0]]
    ai = np.round(((an[b] % np.pi) / np.pi) * P['angles']).astype(int) % P['angles']; hit = np.zeros(len(b), bool)
    straight = lg[b] >= 3 * th[b]     # only a straight piece can carry on a line
    for s in (-1, 1):
        for d in range(4, P['short_probe'] + 1, 4):
            for o in (-2, 0, 2):
                q = Pt + s * u * (lg[b][:, None] / 2 + d) + o * nrm
                qx = np.clip(np.round(q[:, 0]).astype(int), 0, W - 1); qy = np.clip(np.round(q[:, 1]).astype(int), 0, H - 1)
                oo = ori[qy, qx].astype(int); dd = np.abs(((oo - ai + P['angles'] // 2) % P['angles']) - P['angles'] // 2)
                j = lb[qy, qx]; other = (j > 0) & (pc[j] != pc[b])
                da = np.abs(((an[j] - an[b] + np.pi / 2) % np.pi) - np.pi / 2)
                hit |= straight & (((lng[qy, qx] > 0) & (dd <= 2)) | (other & bar[j] & (da <= np.radians(10))))
    keep_cl = np.zeros(cl_n, bool); keep_cl[pc[b[hit]]] = True
    back = cand & ~keep_cl
    m = back[cl_lb] & (line > 0)
    line = line.copy(); ori = ori.copy(); line[m] = 0; ori[m] = -1
    return line, ori


def fill_outline(im, ink, paper, F, idx, lbl):
    """Glyph pieces that are building outlines: most of the piece (fill_edge[0] or more) lies in the 6 px just OUTSIDE a
    building's colour fill, little (fill_edge[1] or less) inside it, and its outline has straight sides (fill_edge[2] or
    fewer corners per 100 px at 2 px). The fill is found as ink_bins.py finds it (pink brick, yellow frame; closed 5 px,
    opened 15 px), so the figures printed inside a building are inside the fill, not round it"""
    lab = cv2.cvtColor(im, cv2.COLOR_BGR2LAB); L = lab[..., 0]
    a = cv2.medianBlur(lab[..., 1], 5).astype(np.int16) - 128; b = cv2.medianBlur(lab[..., 2], 5).astype(np.int16) - 128
    fill = ((((a >= 7) & (b <= 26)) | (b >= 32)) & (L >= P['ink_L']) & paper).astype(np.uint8)
    fill = cv2.morphologyEx(cv2.morphologyEx(fill, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)), cv2.MORPH_OPEN, np.ones((15, 15), np.uint8))
    ring_ = (cv2.dilate(fill, np.ones((13, 13), np.uint8)) > 0) & (fill == 0)
    n = len(F['A']); inr = np.bincount(lbl[ring_ & (lbl > 0)], minlength=n) / np.maximum(F['A'], 1); inf = np.bincount(lbl[(fill > 0) & (lbl > 0)], minlength=n) / np.maximum(F['A'], 1)
    out = np.zeros(len(idx), bool)
    for t, i in enumerate(idx):
        if inr[i] < P['fill_edge'][0] or inf[i] > P['fill_edge'][1]: continue
        x0, y0, bw, bh = int(F['bx'][i]), int(F['by'][i]), int(F['bw'][i]), int(F['bh'][i])
        m = np.zeros((bh + 4, bw + 4), np.uint8); m[2:-2, 2:-2] = lbl[y0:y0 + bh, x0:x0 + bw] == i
        cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE); c = max(cs, key=len)
        ap = cv2.approxPolyDP(c, 2.0, True); out[t] = 100.0 * len(ap) / max(1.0, cv2.arcLength(ap, True)) <= P['fill_edge'][2]
    return out


def heavy_bars(ink):
    """streetcar dashes: heavy straight bars (closed with a 5 px disk, opened with a 9 px one: area 300 px or more, 7-26 px
    thick, 35-240 px long, 2.5 times as long as thick) with another such bar on the same line within 280 px (ink_bins.py's
    rule for the streetcar's heavy dashes). Big lettering has strokes as heavy, but its strokes stand side by side"""
    E = lambda k: cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
    nh, lh, sh, _ = cv2.connectedComponentsWithStats(cv2.morphologyEx(cv2.morphologyEx(ink, cv2.MORPH_CLOSE, E(5)), cv2.MORPH_OPEN, E(9)), connectivity=8)
    if nh <= 1: return np.zeros_like(ink)
    _, lg, tk, bx, by, ba = shape(lh, nh); bars = (sh[:, 4] >= 300) & (tk >= 7) & (tk <= 26) & (lg >= 35) & (lg <= 240) & (lg / tk >= 2.5); bars[0] = False
    b = np.nonzero(bars)[0]; row = np.zeros(len(b), bool); Pb = np.c_[bx[b], by[b]]
    for i, js in enumerate(cKDTree(Pb).query_ball_point(Pb, 280) if len(b) else []):
        d = np.array([np.cos(ba[b[i]]), np.sin(ba[b[i]])])
        for j in js:
            v = Pb[j] - Pb[i]
            if j != i and abs(v[0] * d[1] - v[1] * d[0]) <= 15 and abs(((ba[b[j]] - ba[b[i]] + np.pi / 2) % np.pi) - np.pi / 2) <= 0.25: row[i] = True; break
    bars[b[~row]] = False
    return cv2.dilate(bars[lh].astype(np.uint8), np.ones((9, 9), np.uint8))


def rect_tests(F, idx, lbl, ori, line):
    """for glyph pieces, from the outer contour:
    (box)  a closed outline that fills its rotated rectangle (outer contour area / rectangle 0.9 or more, sides 15 px or
           more): a small shed, a crossed box. (Tried 25 Nov and switched off, box_rect2=None: 'straight sides, 6 corners or
           fewer at 2.5 px, 0.8 of its rectangle, sides 12 px or more', for the tiny house boxes of the 400 ft plates. It took
           0.6 points of text recall on truth crop T1 and found 1 box in a 1200 x 800 window of plate 47)
    (bldg) a closed outline with straight sides: hole 45% or more of the outline's area, 6 corners or fewer per 100 px of
           outline (approximated to 2 px), 20 px or more across: a house drawn on its own in its lot (plate 90), its story
           figure inside or touching. Counted as box. Figures with holes have smaller holes and 8 or more corners per 100 px
    (ring) a thin round ring (one hole of 60% or more of the outline's area, width / height 1.15 or less, 18 px or more):
           a circle symbol. A street name's O is thicker; a figure 0 is italic and long
    (jog)  a thin piece (stroke 5.5 px or less, no hole) that touches line ink and whose outline runs along or across the
           nearby lines' direction (contour approximated to 2 px: 60% or more of its length within 8 deg), or is made of
           few straight sides (5 vertices or fewer per 100 px of outline): a building's jog or porch, a T where lot lines
           meet, cut off from the long sides. Italic figures touching a line score 0.45 or less and 8 or more vertices
    Returns bool arrays box, ring, jog over idx and the aligned share, vertex density and rectangularity"""
    h, w = lbl.shape; box = np.zeros(len(idx), bool); ring = np.zeros(len(idx), bool); jog = np.zeros(len(idx), bool); bldg = np.zeros(len(idx), bool)
    al = np.full(len(idx), np.nan); vd = np.full(len(idx), np.nan); rect = np.zeros(len(idx))
    for t, i in enumerate(idx):
        x0, y0, bw, bh = int(F['bx'][i]), int(F['by'][i]), int(F['bw'][i]), int(F['bh'][i])
        m = np.zeros((bh + 4, bw + 4), np.uint8); m[2:-2, 2:-2] = lbl[y0:y0 + bh, x0:x0 + bw] == i
        cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        c = max(cs, key=len); ca = cv2.contourArea(c); (cx, cy), (rw, rh), _ = cv2.minAreaRect(c)
        rect[t] = ca / max(1.0, rw * rh)
        if F['holes'][i] >= 1:
            nv = len(cv2.approxPolyDP(c, 2.5, True))   # a hand-drawn box has straight sides: 4 to 6 corners at 2.5 px
            box[t] = (rect[t] >= P['box_rect'] and min(rw, rh) >= P['box_min']) or (P['box_rect2'] is not None and nv <= 6 and rect[t] >= P['box_rect2'] and min(rw, rh) >= P['box_min2'])
            ap = cv2.approxPolyDP(c, 2.0, True); per = max(1.0, cv2.arcLength(ap, True)); vdo = 100.0 * len(ap) / per
            bldg[t] = (ca - F['A'][i]) >= P['bldg'][0] * ca and vdo <= P['bldg'][1] and min(rw, rh) >= P['bldg'][2]
            ring[t] = F['holes'][i] == 1 and (ca - F['A'][i]) >= P['ring'][0] * ca and max(rw, rh) <= P['ring'][1] * min(rw, rh) and min(rw, rh) >= P['ring'][2]
        if F['touch'][i] > 0 and F['sw'][i] <= P['jog_sw'] and F['holes'][i] == 0:
            g = P['jog_win']; X0, Y0, X1, Y1 = max(0, x0 - g), max(0, y0 - g), min(w, x0 + bw + g), min(h, y0 + bh + g)
            o = ori[Y0:Y1, X0:X1]; o = o[o >= 0]
            ap = cv2.approxPolyDP(c, 2.0, True)[:, 0, :].astype(float); e = np.roll(ap, -1, 0) - ap; L = np.hypot(*e.T); per = max(1.0, L.sum())
            vd[t] = 100.0 * len(ap) / per
            if len(o) >= 20:
                th = np.pi * int(np.bincount(o, minlength=P['angles']).argmax()) / P['angles']
                an = np.arctan2(e[:, 1], e[:, 0]); dd = np.abs(((an - th + np.pi / 4) % (np.pi / 2)) - np.pi / 4)
                al[t] = L[dd <= np.radians(8)].sum() / per
            jog[t] = (al[t] >= P['jog_al']) or (vd[t] <= P['jog_vd'])
    return box | bldg, ring, jog, al, vd, rect


def shape(lab, n):
    """every piece's area, length and thickness of the equivalent bar (second moments), centre and angle (ink_bins.shape)"""
    ys, xs = np.nonzero(lab); l = lab[ys, xs]; A = np.bincount(l, minlength=n).astype(float); A[A == 0] = 1
    mx = np.bincount(l, xs, n) / A; my = np.bincount(l, ys, n) / A; dx = xs - mx[l]; dy = ys - my[l]
    sxx = np.bincount(l, dx * dx, n) / A; syy = np.bincount(l, dy * dy, n) / A; sxy = np.bincount(l, dx * dy, n) / A
    t = (sxx + syy) / 2; d = np.sqrt(np.maximum(((sxx - syy) / 2) ** 2 + sxy ** 2, 0))
    return A, np.sqrt(12 * (t + d) + 1), np.sqrt(12 * np.maximum(t - d, 0) + 1), mx, my, 0.5 * np.arctan2(2 * sxy, sxx - syy)


def fill_pinholes(m, maxa=4):
    inv = (m == 0).astype(np.uint8); n, lb, st, _ = cv2.connectedComponentsWithStats(inv, connectivity=4)
    small = st[:, 4] <= maxa; small[0] = False
    out = m.copy(); out[small[lb]] = 1; return out


def euler8(lab, n):
    """Euler number of every piece (8-connected ink) by bit quads: (C1 - C3 - 2 CD) / 4. Two 8-connected pieces never share
    a 2x2 window, so every window belongs to at most one piece"""
    b = (lab > 0)
    a, bb, c, d = b[:-1, :-1], b[:-1, 1:], b[1:, :-1], b[1:, 1:]
    s = a.astype(np.int8) + bb + c + d
    lw = np.maximum(np.maximum(lab[:-1, :-1], lab[:-1, 1:]), np.maximum(lab[1:, :-1], lab[1:, 1:]))
    c1 = np.bincount(lw[s == 1], minlength=n); c3 = np.bincount(lw[s == 3], minlength=n)
    diag = (s == 2) & (((a & d) & ~bb & ~c) | ((bb & c) & ~a & ~d))
    cd = np.bincount(lw[diag], minlength=n)
    return (c1 - c3 - 2 * cd) / 4.0


def features(res, line):
    n, lb, st, _ = cv2.connectedComponentsWithStats(res, connectivity=8)
    A, lg, th, mx, my, an = shape(lb, n)
    dt = cv2.distanceTransform(res, cv2.DIST_L2, 3)
    ridge = (dt > 0) & (dt >= cv2.dilate(dt, np.ones((3, 3), np.uint8)))
    rl = lb[ridge]; rc = np.bincount(rl, minlength=n).astype(float)
    sw = 2 * np.bincount(rl, dt[ridge], n) / np.maximum(rc, 1); sw = np.maximum(sw, 1.0)
    dtmax = np.zeros(n); np.maximum.at(dtmax, rl, dt[ridge])
    holes = np.round(1 - euler8(lb, n)).astype(int)
    near = cv2.dilate(line, np.ones((5, 5), np.uint8)) > 0
    touch = np.bincount(lb[near & (res > 0)], minlength=n)
    ext = np.maximum(st[:, 2], st[:, 3])
    F = dict(A=A, long=lg, thick=th, x=mx, y=my, ang=an, sw=sw, dtmax=dtmax, holes=holes, touch=touch, ext=ext,
             bx=st[:, 0], by=st[:, 1], bw=st[:, 2], bh=st[:, 3])
    F['slen'] = A / sw
    return n, lb, F


def kinds(F):
    n = len(F['A']); k = np.array(['long'] * n, dtype=object)
    A, lg, th, sw = F['A'], F['long'], F['thick'], F['sw']
    stroke = th <= np.maximum(P['stroke_thick'][0] * sw, sw + P['stroke_thick'][1])
    blob = (sw >= P['blob_sw'] * th) & (lg / th < 2) & (lg >= P['blob_len'])
    glyph = (~stroke) & (lg <= P['glyph_max']) & (sw <= P['sw_max']) & (A >= 20)
    cluster = (~stroke) & (lg > P['glyph_max']) & (lg <= P['cluster_max']) & (th >= P['cluster_thick'][0]) & (th <= P['cluster_thick'][1]) & (F['slen'] >= P['cluster_density'] * lg) & (sw <= P['sw_max'])
    k[glyph] = 'glyph'; k[cluster] = 'cluster'; k[stroke & (lg <= P['glyph_max'])] = 'stroke'; k[blob] = 'blob'
    k[(A < P['dot_area']) | (lg < P['dot_len'])] = 'dot'; k[0] = 'bg'
    return k


def chains(F, idx, ori, line):
    """strokes that are dashes of a dashed line or pieces of a broken line: chained end to end along their axis, or carrying on
    a line of line ink. Returns a bool per index in idx"""
    if not len(idx): return np.zeros(0, bool)
    x, y, an, lg, sw = F['x'][idx], F['y'][idx], F['ang'][idx], F['long'][idx], F['sw'][idx]
    Pt = np.c_[x, y]; u = np.c_[np.cos(an), np.sin(an)]
    T = cKDTree(Pt); pairs = T.query_pairs(r=float(lg.max() + P['chain_gap'][0] + 5) if len(lg) else 1, output_type='ndarray')
    E = []
    if len(pairs):
        i, j = pairs[:, 0], pairs[:, 1]; v = Pt[j] - Pt[i]
        da = np.abs(((an[j] - an[i] + np.pi / 2) % np.pi) - np.pi / 2)
        along = np.abs((v * u[i]).sum(1)); across_i = np.abs(v[:, 0] * u[i, 1] - v[:, 1] * u[i, 0]); across_j = np.abs(v[:, 0] * u[j, 1] - v[:, 1] * u[j, 0])
        gap = along - (lg[i] + lg[j]) / 2
        tol = 3 + np.maximum(sw[i], sw[j]) / 2
        ok = (da <= np.radians(P['chain_ang'])) & (across_i <= tol) & (across_j <= tol) & (gap >= -3) & (gap <= np.maximum(P['chain_gap'][0], P['chain_gap'][1] * (lg[i] + lg[j]) / 2))
        E = pairs[ok]
    dash = np.zeros(len(idx), bool)
    if len(E):
        nc, lab = connected_components(coo_matrix((np.ones(len(E)), (E[:, 0], E[:, 1])), shape=(len(idx), len(idx))), directed=False)
        size = np.bincount(lab, minlength=nc)
        # span of each chain
        lo = np.full(nc, np.inf); hi = np.full(nc, -np.inf)
        # project on the chain's first member's axis
        first = np.full(nc, -1);
        for m in range(len(idx)):
            if first[lab[m]] < 0: first[lab[m]] = m
        ax = u[first[lab]]; proj = (Pt * ax).sum(1)
        np.minimum.at(lo, lab, proj - lg / 2); np.maximum.at(hi, lab, proj + lg / 2)
        span = hi - lo
        dash = (size[lab] >= 3) | ((size[lab] == 2) & (span[lab] >= P['chain_span']))
    # carries on a line: line ink of about the same direction within cont_probe px beyond either end, along the axis
    h, w = line.shape; cont = np.zeros(len(idx), bool)
    ai = np.round(((an % np.pi) / np.pi) * P['angles']).astype(int) % P['angles']
    for s in (-1, 1):
        for d in range(3, P['cont_probe'] + 1, 3):
            q = Pt + s * u * (lg[:, None] / 2 + d)
            qx = np.clip(np.round(q[:, 0]).astype(int), 0, w - 1); qy = np.clip(np.round(q[:, 1]).astype(int), 0, h - 1)
            o = ori[qy, qx].astype(int)
            dd = np.abs(((o - ai + P['angles'] // 2) % P['angles']) - P['angles'] // 2)
            cont |= (o >= 0) & (dd <= P['cont_ang'])
    return dash | cont, dash, cont


def run(N, win=None, out=None, pic=False, tag=None, verbose=True):
    t0 = time.time(); T = {}
    im, ink, paper, (W, H) = load(N, win); T['load'] = time.time() - t0
    line, ori = line_ink(ink); T['line'] = time.time() - t0
    res = (ink & ~(cv2.dilate(line, np.ones((3, 3), np.uint8)) > 0)).astype(np.uint8)
    resf = fill_pinholes(res)   # pinholes (4 px or less) filled for the shape features only
    n, lb, F = features(resf, line); T['features'] = time.time() - t0
    k = kinds(F)
    bars = heavy_bars(ink); inbar = np.bincount(lb[(bars > 0) & (resf > 0)], minlength=n) / np.maximum(F['A'], 1)
    k[(inbar >= 0.5) & np.isin(k, ('glyph', 'cluster', 'stroke', 'long', 'blob'))] = 'bar'
    gi = np.nonzero(k == 'glyph')[0]
    if P.get('fill_edge'):   # a building outline drawn round a coloured fill, cut off from the lines (see fill_outline)
        fo = fill_outline(im, ink, paper, F, gi, lb); k[gi[fo]] = 'bldg'; gi = gi[~fo]
    box, ring, jog, al, vd, rect = rect_tests(F, gi, lb, ori, line)
    k[gi[box]] = 'box'; k[gi[ring & ~box]] = 'ring'; k[gi[jog & ~box & ~ring]] = 'jog'
    for nm, v in (('aligned', al), ('vdens', vd), ('rect', rect)): F[nm] = np.full(n, np.nan); F[nm][gi] = v
    T['rect'] = time.time() - t0
    st = np.nonzero(k == 'stroke')[0]
    bad, dash, cont = chains(F, st, ori, line)
    isdash = np.zeros(n, bool); isdash[st[bad]] = True
    # '=' marks (ditto): two short strokes side by side, parallel, of about one length, with no third
    sm = np.nonzero(((k == 'stroke') | (k == 'dot')) & ~isdash & (F['long'] >= P['eq'][0]) & (F['long'] <= P['eq'][1]))[0]
    if len(sm) > 1:
        Pt = np.c_[F['x'][sm], F['y'][sm]]; pr = cKDTree(Pt).query_pairs(P['eq'][3], output_type='ndarray')
        if len(pr):
            i, j = sm[pr[:, 0]], sm[pr[:, 1]]; u = np.c_[np.cos(F['ang'][i]), np.sin(F['ang'][i])]; v = Pt[pr[:, 1]] - Pt[pr[:, 0]]
            da = np.abs(((F['ang'][j] - F['ang'][i] + np.pi / 2) % np.pi) - np.pi / 2); al = np.abs((v * u).sum(1)); ac = np.abs(v[:, 0] * u[:, 1] - v[:, 1] * u[:, 0])
            ok = (da <= np.radians(15)) & (al <= 4) & (ac >= P['eq'][2]) & (np.maximum(F['long'][i], F['long'][j]) <= 1.6 * np.minimum(F['long'][i], F['long'][j]))
            pr = pr[ok]; deg = np.bincount(pr.ravel(), minlength=len(sm)) if len(pr) else np.zeros(len(sm), int)
            for a_, b_ in pr:
                if deg[a_] == 1 and deg[b_] == 1: k[sm[a_]] = 'eq'; k[sm[b_]] = 'eq'
    T['chains'] = time.time() - t0
    seed = (k == 'glyph') | (k == 'cluster'); eqm = k == 'eq'
    heavy = (k == 'stroke') & (F['sw'] >= P['heavy_sw'])
    accept_ok = ((k == 'stroke') | (k == 'dot')) & ~isdash
    text = seed.copy(); taken = np.zeros(n, bool)
    E = lambda r: cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))
    big = seed & (F['long'] > P['big_seed'])
    cur_small = seed & ~big; cur_big = big
    for rnd in range(P['rounds']):
        zone = cv2.dilate((cur_small[lb]).astype(np.uint8), E(P['r_small']))
        if cur_big.any(): zone |= cv2.dilate((cur_big[lb]).astype(np.uint8), E(P['r_big']))
        hit = np.bincount(lb[(zone > 0) & (lb > 0)], minlength=n) > 0
        new = hit & accept_ok & ~text
        if not new.any(): break
        text |= new; taken |= new; cur_small = new; cur_big = np.zeros(n, bool)
    text |= eqm
    lone = (k == 'stroke') & ~isdash & ~text & (F['long'] >= P['lone'][0]) & (F['long'] <= P['lone'][1]) & (F['touch'] == 0) & (F['sw'] <= P['lone_sw'])
    T['group'] = time.time() - t0
    code = np.zeros(ink.shape, np.uint8)
    code[ink > 0] = CODE['other']; code[line > 0] = CODE['line']
    cl = np.zeros(n, np.uint8); cl[seed] = CODE['glyph']; cl[taken | eqm] = CODE['taken']; cl[lone] = CODE['lone']
    m = (lb > 0) & (res > 0); cc = cl[lb]; sel = m & (cc > 0); code[sel] = cc[sel]
    cnt = {name: int((code == v).sum()) for name, v in CODE.items()}
    kc = {kk: int((k == kk).sum()) for kk in ('glyph', 'cluster', 'stroke', 'dot', 'blob', 'long', 'box', 'ring', 'jog', 'eq', 'bar', 'bldg')}
    rec = dict(plate=N, win=win, size=[W, H], params=P, ink_px=int(ink.sum()), px=cnt, pieces=kc,
               strokes=dict(total=int(len(st)), dash=int(dash.sum()), carries_line=int(cont.sum()), heavy=int(heavy.sum())),
               text_pieces=dict(seed=int(seed.sum()), taken=int(taken.sum()), eq=int(eqm.sum()), lone=int(lone.sum())),
               seconds={kk: round(v, 1) for kk, v in T.items()}, made=time.strftime('%Y-%m-%d %H:%M'))
    if out:
        os.makedirs(out, exist_ok=True); stem = os.path.join(out, f'{N}_finder' + (f'_{tag}' if tag else ''))
        cv2.imwrite(stem + '.png', code)
        json.dump(rec, open(stem + '.json', 'w', encoding='utf8', newline='\n'), indent=1)
        np.savez_compressed(stem.replace('_finder', '_pieces') + '.npz', kind=k.astype(str), dash=isdash, text=text, lone=lone, taken=taken,
                            **{kk: np.asarray(v) for kk, v in F.items()})
        if pic:
            c = overlay(im, code); cv2.imwrite(stem + '.jpg', c if win else cv2.resize(c, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 88])
    if verbose:
        print(f'plate {N} {win or "whole"}: ink {rec["ink_px"]:,} px; text {cnt["glyph"] + cnt["taken"] + cnt["lone"]:,} px '
              f'(glyph {cnt["glyph"]:,}, taken {cnt["taken"]:,}, lone {cnt["lone"]:,}); line {cnt["line"]:,}; other {cnt["other"]:,} | pieces {kc} | {rec["strokes"]} | {T}')
    return code, rec, (n, lb, F, k)


def overlay(im, code):
    c = (im * 0.25 + 255 * 0.75).astype(np.uint8)
    for v, col in COLOR.items(): c[code == v] = col
    return c


if __name__ == '__main__':
    a = sys.argv; N = a[1]
    win = tuple(int(v) for v in a[a.index('--win') + 1:a.index('--win') + 5]) if '--win' in a else None
    out = a[a.index('--out') + 1] if '--out' in a else os.path.join(HERE, '..', 'out')
    tag = a[a.index('--tag') + 1] if '--tag' in a else None
    run(N, win, out, '--pic' in a, tag)
