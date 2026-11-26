"""Character finder v2 (finder2, 25 Nov 2026): which ink on a Sanborn 1922 plate is a letter or a digit?
A copy of text/finder/scripts/finder.py (v1), improved. Writes the hand-off text mask of text_first.md section 6.

    cd data/sanborn
    python -B bench_2026-11-25/text_v1/code/finder2.py N [--win X0 Y0 X1 Y1] [--out DIR] [--pic] [--tag NAME]

Output N_text.png (default DIR: text_v1/finder2/out/final), one code per pixel:
    0 paper, 1 line ink, 2 text sure (glyphs, clusters, big letters), 3 text by context (strokes and dots taken in by a
    glyph, ditto marks, lone figure 1s, the pieces round a big letter), 4 shared ink where a glyph touches a line (owned
    by the line for sorting, not scored in training), 5 other ink, not text (dashes, ticks, hooks, hydrants, specks).
Text for scoring is codes 2 and 3. No truth (street map, rail, lines) is read: only the scan, its paper mask and
scale_table.json.

What is new against v1 (each function's docstring has the rule and its numbers):
  - big_letters: BIG LETTERING with thick strokes (street names, block numbers, adjoining sheet numbers, big owner and
    railroad names), whose stems v1 took as line ink, is rescued from the thick core of the ink once the long lines
    (a straight 121 px line fits) are taken out; streetcar dashes, dots, rings and round symbols, closed boxes, links
    between lines, heavy dashes on thin lines, line ends at the sheet edge and lone bars are refused.
  - context_rescue: round each big letter, its arms and joins that fell apart (strokes, dots, jogs, the 1 px rim, short
    line bits that touch it) become text by context; never a dash, a tick end, a free dash, a filled dot.
  - tick_ends: the two ends of rail ticks (evenly spaced crossings of a line) are never text, not even the tip.
  - shared_ink: code 4 at the touch points between glyphs and lines, 2-3 px; the line keeps every pixel.
  - SCALE: settings by scale from scale_table.json (400 ft: tick rule off, 1 px gaps bridged in small figures).
v1's own description follows.

Character finder, prototype (25 Nov 2026). Which ink on a Sanborn 1922 plate is a letter or a digit?

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
DEBUG = None   # dev pictures: set to a dict to collect intermediate masks
P = dict(ink_L=140, line_len=61, angles=48, thick_d=8, thick_long=131, thick_bar=16, dot_area=12, dot_len=6, glyph_max=140,
         cluster_max=600, cluster_thick=(10, 70), cluster_density=1.8, stroke_thick=(1.6, 3.0), blob_len=11, blob_sw=0.55,
         sw_max=14, chain_ang=12, chain_gap=(30, 0.8), chain_span=50, cont_probe=12, cont_ang=2,
         r_small=9, r_big=15, big_seed=45, rounds=3, lone=(12, 45), lone_sw=7, heavy_sw=8,
         short_line=100, short_probe=48, short_free=8, box_rect=0.9, box_min=15, box_rect2=None, box_min2=12, jog_sw=5.5, jog_win=30, jog_al=0.6, jog_vd=5.0, ring=(0.6, 1.15, 18), bldg=(0.45, 6.0, 20), fill_edge=(0.7, 0.2, 7.0), eq=(5, 22, 3, 12),
         # finder2 (25 Nov 2026): big lettering, shared ink
         long_len=121, long_angles=64, big_core=5, big_ext=(20, 260), big_area=60, big_guard=2, big_grow=3, big_cont=(14, 2), big_box=(0.45, 6.0),
         big_bar=4.0, big_bar_nb=1.3, big_link=1.6, big_link_line=True, big_blob=0, big_circle=60, big_piece=0.5, ctx_glyph=40, ctx_r=0.25, ctx_rr=(4, 20), ctx_in=0.9, ctx_line=40, ctx_tip=12, tick=(18, 28, 220, 40), frag_close=0, share_r=1)
# finder2: settings by scale (data/sanborn/scale_table.json, ft to the inch). Set by eye on windows of plate 49 and 47 only
# (windows listed in finder2/out/windows_looked.json):
#  - 400 ft: the tick rule is off. On the dense lot blocks of 47 it took 300-900 pieces of small rotated lot numbers per
#    800 x 700 px as tick ends (their fragments touch the narrow lots' lines in even rows), and no rail ticks were seen on
#    the 49 railroad window; small figures there are faint and fall apart at the ink threshold, so 1 px gaps are bridged
#    for the shape features (frag_close).
#  (Tried 25 Nov on 47: line_len 45 at 400 ft; it took more of the rotated lot numbers as line ink. Not used.)
SCALE = {400: dict(tick=None, frag_close=3)}
CODE = dict(line=1, glyph=2, taken=3, shared=4, other=5)   # the hand-off codes (text_first.md section 6)
COLOR = {1: (170, 170, 170), 2: (220, 0, 220), 3: (255, 120, 0), 4: (0, 200, 230), 5: (0, 150, 0)}   # BGR: grey, magenta, blue, yellow, green


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


def tick_ends(F, k, line, ori):
    """finder2: the ENDS OF RAIL TICKS and similar cross marks. A tick crosses a line; when the line ink is taken out its
    two ends are left as small pieces (stroke or dot, tick[0] px across or less) touching the line, one on each side.
    Two such pieces (the bigger 4 x the smaller or less), each a dot or a stroke across the line in line with the join
    (within 25 deg: one straight bar cut by the line), whose join is tick[1] px long or less, crosses line ink at its
    middle and runs at 60 deg or more to that line, make a CROSSING. Ticks are evenly spaced: a crossing with crossings on
    the same line (same direction within 2 angle steps, 4 px + 8% of the distance or less off it, tick[3]-tick[2] px away) on
    both sides, the nearer spacing 1.6 x the other or less, is in a row of ticks, and so are those two neighbours; and both ends of each are ticks: never text, not even the
    tip. Then any other small piece touching line ink that lies on that line within the row (between two of its crossings
    or within tick[2] / 2 px of one) and runs across it is a tick end too (a tick whose other end joined a letter).
    Returns a bool per piece"""
    n = len(F['A']); H, W = line.shape; NA = P['angles']; tk = np.zeros(n, bool)
    S = np.nonzero(np.isin(k, ('stroke', 'dot')) & (F['touch'] > 0) & (F['ext'] <= P['tick'][0]))[0]
    if len(S) < 2: return tk
    Pt = np.c_[F['x'][S], F['y'][S]]; pr = cKDTree(Pt).query_pairs(P['tick'][1], output_type='ndarray')
    if not len(pr): return tk
    fl = cv2.dilate(line, np.ones((5, 5), np.uint8))
    m = (Pt[pr[:, 0]] + Pt[pr[:, 1]]) / 2; mx_ = np.clip(np.round(m[:, 0]).astype(int), 0, W - 1); my_ = np.clip(np.round(m[:, 1]).astype(int), 0, H - 1)
    on = fl[my_, mx_] > 0
    # the line's direction near the middle: the most common angle index of line ink in a 7 x 7 window
    ang = np.full(len(pr), -1)
    for t in np.nonzero(on)[0]:
        w = ori[max(0, my_[t] - 3):my_[t] + 4, max(0, mx_[t] - 3):mx_[t] + 4]; w = w[w >= 0]
        if len(w): ang[t] = np.bincount(w, minlength=NA).argmax()
    v = Pt[pr[:, 1]] - Pt[pr[:, 0]]; th = np.pi * np.maximum(ang, 0) / NA; d = np.c_[np.cos(th), np.sin(th)]
    cosv = np.abs((v * d).sum(1)) / np.maximum(np.hypot(v[:, 0], v[:, 1]), 1e-6)
    # both ends about one size, and each a dot or a stroke across the line
    ea, eb = F['ext'][S[pr[:, 0]]], F['ext'][S[pr[:, 1]]]
    va = np.arctan2(v[:, 1], v[:, 0])
    def across(ii):   # a dot, or a stroke across the line and in line with the join (one straight bar cut by the line)
        da = np.abs(((F['ang'][ii] - th + np.pi / 2) % np.pi) - np.pi / 2); dv = np.abs(((F['ang'][ii] - va + np.pi / 2) % np.pi) - np.pi / 2)
        return (F['long'][ii] < 1.5 * F['thick'][ii]) | ((da >= np.radians(60)) & (dv <= np.radians(25)))
    cr = on & (ang >= 0) & (cosv <= np.cos(np.radians(60))) & (np.maximum(ea, eb) <= 4 * np.minimum(ea, eb)) & across(S[pr[:, 0]]) & across(S[pr[:, 1]])
    if cr.sum() < 2: return tk
    C = m[cr]; Ca = ang[cr]; Cp = pr[cr]; Cd = d[cr]; row = np.zeros(len(C), bool)
    T = cKDTree(C)
    # a row: evenly spaced crossings on one line. A crossing with neighbours on both sides along the line at spacings
    # within 1.6 x of each other is in a row; so are its two neighbours
    for a_, js in enumerate(T.query_ball_point(C, P['tick'][2])):
        pos = []
        for b_ in js:
            if b_ == a_: continue
            dd = abs(((Ca[b_] - Ca[a_] + NA // 2) % NA) - NA // 2); w_ = C[b_] - C[a_]; off = abs(w_[0] * Cd[a_][1] - w_[1] * Cd[a_][0])
            dist = np.hypot(*w_)
            if dd <= 2 and off <= 4 + 0.08 * dist and dist >= P['tick'][3]: pos.append((float(w_ @ Cd[a_]), b_))
        lo = [q for q in pos if q[0] < 0]; hi = [q for q in pos if q[0] > 0]
        if lo and hi:
            l_ = max(lo); h_ = min(hi); a1, a2 = -l_[0], h_[0]
            if max(a1, a2) <= 1.6 * min(a1, a2): row[a_] = row[l_[1]] = row[h_[1]] = True
    tk[S[Cp[row].ravel()]] = True
    # single tick ends on the same line, within the row
    R = C[row]; Ra = Ca[row]; Rd = Cd[row]
    if len(R):
        T2 = cKDTree(R); rest = np.setdiff1d(S, S[Cp[row].ravel()])
        for i in rest:
            q = np.array([F['x'][i], F['y'][i]])
            for j in T2.query_ball_point(q, P['tick'][2] / 2):
                w_ = q - R[j]; along = abs(w_ @ Rd[j]); off = abs(w_[0] * Rd[j][1] - w_[1] * Rd[j][0])
                da = abs(((F['ang'][i] - np.pi * Ra[j] / NA + np.pi / 2) % np.pi) - np.pi / 2)
                if off <= P['tick'][1] / 2 and (da >= np.radians(60) or F['long'][i] < 1.5 * F['thick'][i]) and along >= 3:
                    tk[i] = True; break
    return tk


def long_ink(ink, L):
    """ink that a straight L px line fits, tried at long_angles angles on the ink grown by 1 px, and which way it runs
    (angle index of long_angles). These are the long, sure lines: no letter stroke is this long except in the adjoining
    sheet numbers. (Tried 25 Nov: the ink grown by 2 px, at 48 angles: in dense blocks it took whole block numbers, '28' on
    plate 5, as long-line ink)"""
    A = P['long_angles']; fat = cv2.dilate(ink, np.ones((3, 3), np.uint8)); o = np.zeros_like(ink); ori = np.full(ink.shape, -1, np.int8)
    for i in range(A):
        oi = cv2.morphologyEx(fat, cv2.MORPH_OPEN, line_kernel(L, np.pi * i / A)) & ink
        ori[(oi > 0) & (o == 0)] = i; o |= oi
    return o, ori


def ll_contacts(lab, ids, st, LL, r):
    """for each piece id in ids: how many separate bits of long-line ink lie within r px of it"""
    out = np.zeros(len(ids), int); H, W = lab.shape; ker = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))
    for t, i in enumerate(ids):
        x0, y0, bw, bh = st[i, 0], st[i, 1], st[i, 2], st[i, 3]; X0, Y0, X1, Y1 = max(0, x0 - r), max(0, y0 - r), min(W, x0 + bw + r), min(H, y0 + bh + r)
        z = cv2.dilate((lab[Y0:Y1, X0:X1] == i).astype(np.uint8), ker) & LL[Y0:Y1, X0:X1]
        if z.any(): out[t] = cv2.connectedComponents(z, connectivity=8)[0] - 1
    return out


def line_contacts(lab, ids, st, mask, r0, r1):
    """for each piece id in ids: how many separate bits of mask lie in the band r0-r1 px round it (not touching the piece's
    own edge)"""
    out = np.zeros(len(ids), int); H, W = lab.shape
    k1 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r1 + 1, 2 * r1 + 1)); k0 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r0 + 1, 2 * r0 + 1))
    for t, i in enumerate(ids):
        x0, y0, bw, bh = st[i, 0], st[i, 1], st[i, 2], st[i, 3]; X0, Y0, X1, Y1 = max(0, x0 - r1), max(0, y0 - r1), min(W, x0 + bw + r1), min(H, y0 + bh + r1)
        me = (lab[Y0:Y1, X0:X1] == i).astype(np.uint8)
        z = (cv2.dilate(me, k1) & ~cv2.dilate(me, k0) & 1) & mask[Y0:Y1, X0:X1]
        if z.any(): out[t] = cv2.connectedComponents(z.astype(np.uint8), connectivity=8)[0] - 1
    return out


def ends_continue(lab, i, st, thin):
    """does thin ink carry on from BOTH ends of piece i? (a heavy dash on a thin line, curved or straight; a thick stretch
    where two lines merge). The ends are the piece's pixels within 6 px of its two extremes along its axis. An end carries
    on when 6 px or more of THIN ink (ink outside the thick core) or long-line ink lie within 3-8 px of it. A letter's free stroke end has
    paper there, and a neighbouring big letter is thick ink, not thin"""
    H, W = lab.shape; x0, y0, bw, bh = st[i, 0], st[i, 1], st[i, 2], st[i, 3]; r = 8
    X0, Y0, X1, Y1 = max(0, x0 - r), max(0, y0 - r), min(W, x0 + bw + r), min(H, y0 + bh + r)
    me = (lab[Y0:Y1, X0:X1] == i); ys, xs = np.nonzero(me)
    if len(xs) < 10: return False
    c = np.c_[xs, ys].astype(float); c -= c.mean(0); w, v = np.linalg.eigh(c.T @ c); pr = c @ v[:, 1]
    near = cv2.dilate(me.astype(np.uint8), np.ones((7, 7), np.uint8)) > 0; cnt = 0
    for ext_ in (pr.min(), pr.max()):
        e = np.zeros(me.shape, np.uint8); sel = np.abs(pr - ext_) <= 6; e[ys[sel], xs[sel]] = 1
        ring = (cv2.dilate(e, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))) > 0) & ~near & (thin[Y0:Y1, X0:X1] > 0)
        cnt += int(ring.sum()) >= 6
    return cnt == 2


def big_letters(ink, LL, LLori, bars, edge, line=None):
    """finder2: BIG LETTERING with thick strokes (street names, block numbers, adjoining sheet numbers, big owner and
    railroad names). Their stems are long enough for a 61 px line to fit, so step 2 takes them as line ink, and what is left
    of them falls apart into strokes and odd pieces.
      core   the ink opened with a big_core px disk: strokes big_core px wide or more. Small lettering (house and lot numbers,
             dimensions, story figures: strokes 2-4 px) is not in it; big lettering, heavy lines, streetcar dashes and
             hydrant dots are.
      The long lines (long_ink: a straight long_len px line fits) and big_guard px round them are taken out of the core,
      so a letter standing on a heavy street line comes apart from it. Each piece of what is left is a letter when
        - it is big_ext px across (20-260) and has big_area px or more;
        - it is not a streetcar dash (half of it or more in heavy_bars), nor a dot (round, filling 60% of its box
          or more, under 32 px);
        - it does not carry on a long line: an elongated piece (3 x as long as thick) with long-line ink of the same
          direction (within 2 angle steps) within big_cont px beyond either end along its axis is a piece of that line;
        - it is not a closed box with straight sides (hole big_box[0] of its outline area or more, big_box[1] corners or
          fewer per 100 px of outline): a small heavy building;
        - it is not a round ring (hole 60% of its outline area or more, 1.15 or less as long as wide), nor a big round
          symbol, closed or broken by a line (big_circle px or more across, convex hull circular, 1.12 or less as long as
          wide, 90% of its pixels in the outer 45% of the radius, going 270 deg or more round);
        (Filled dots, where a big_blob px disk fits, are taken out of the core first.)
        - it is not a LINK between lines: one stroke (area / (stroke width x length) big_link or less, no hole) with long
          lines near it at 2 or more separate places (within big_guard + 3 px), or line ink of any length at 2 or more
          separate places 3-6 px out (big_link_line): a short heavy line between two bends, a hydrant arc on a wall, the
          notch of a block line; unless it joins (within 9 px, across the line) an accepted letter piece at least 0.6 x its size;
        - it is not one stroke (as above) with thin ink carrying on from both its ends (ends_continue): a heavy dash of a curved streetcar track, a thick stretch where two lines merge; with the same
          exception;
        - it is not elongated (3 x as long as thick) and within 6 px of the paper's edge: a line cut by the sheet edge;
        - a straight bar (big_bar x as long as thick: an I, a 1, or a short heavy wall) needs another accepted piece that
          is not a bar, half to twice its size, within big_bar_nb x its length.
    The letter is grown back over the ink by big_grow px (to its thin edges and joins). Long-line ink inside it stays line
    ink. Returns the letter mask, its core, and counts"""
    E = lambda k: cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
    core = cv2.morphologyEx(ink, cv2.MORPH_OPEN, E(P['big_core']))
    # filled dots (hydrants: a big_blob px disk fits in them; no letter stroke is that wide) are taken out of the core, so a
    # dot joined to a letter by a short line does not make it bigger or ride along with it
    blob = cv2.dilate(cv2.morphologyEx(ink, cv2.MORPH_OPEN, E(P['big_blob'])), E(5)) if P.get('big_blob') else np.zeros_like(ink)
    g = P['big_guard']; cand = ((core > 0) & (blob == 0) & ~(cv2.dilate(LL, np.ones((2 * g + 1, 2 * g + 1), np.uint8)) > 0)).astype(np.uint8)
    n, lb, st, _ = cv2.connectedComponentsWithStats(cand, connectivity=8)
    info = dict(core_pieces=int(n - 1))
    if n <= 1: return np.zeros_like(ink), np.zeros_like(ink), info
    A, lg, th, mx, my, an = shape(lb, n)
    ext = np.maximum(st[:, 2], st[:, 3])
    ok = (ext >= P['big_ext'][0]) & (ext <= P['big_ext'][1]) & (st[:, 4] >= P['big_area']); ok[0] = False
    r = {}
    inbar = np.bincount(lb[(bars > 0) & (cand > 0)], minlength=n) / np.maximum(A, 1); r['bar'] = ok & (inbar >= 0.5); ok &= ~r['bar']
    r['dot'] = ok & (lg < 1.6 * th) & (ext < 32) & (st[:, 4] >= 0.6 * st[:, 2] * st[:, 3]); ok &= ~r['dot']   # a filled round dot (hydrant)
    # carries on a long line
    H, W = ink.shape; b = np.nonzero(ok & (lg >= 3 * th))[0]; cont = np.zeros(n, bool)
    if len(b):
        Pt = np.c_[mx[b], my[b]]; u = np.c_[np.cos(an[b]), np.sin(an[b])]; nrm = np.c_[-u[:, 1], u[:, 0]]
        NA = P['long_angles']; ai = np.round(((an[b] % np.pi) / np.pi) * NA).astype(int) % NA; hit = np.zeros(len(b), bool)
        for s_ in (-1, 1):
            for d in range(2, P['big_cont'][0] + 1, 2):
                for o in (-2, 0, 2):
                    q = Pt + s_ * u * (lg[b][:, None] / 2 + d) + o * nrm
                    qx = np.clip(np.round(q[:, 0]).astype(int), 0, W - 1); qy = np.clip(np.round(q[:, 1]).astype(int), 0, H - 1)
                    oo = LLori[qy, qx].astype(int); dd = np.abs(((oo - ai + NA // 2) % NA) - NA // 2)
                    hit |= (oo >= 0) & (dd <= P['big_cont'][1])
        cont[b[hit]] = True
    r['cont'] = ok & cont; ok &= ~cont
    # closed boxes with straight sides
    holes = np.round(1 - euler8(lb, n)).astype(int); box = np.zeros(n, bool)
    for i in np.nonzero(ok & (holes >= 1))[0]:
        x0, y0, bw, bh = st[i, 0], st[i, 1], st[i, 2], st[i, 3]
        m = np.zeros((bh + 4, bw + 4), np.uint8); m[2:-2, 2:-2] = lb[y0:y0 + bh, x0:x0 + bw] == i
        cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE); c = max(cs, key=len); ca = cv2.contourArea(c)
        ap = cv2.approxPolyDP(c, 2.0, True); vd = 100.0 * len(ap) / max(1.0, cv2.arcLength(ap, True))
        box[i] = (ca - A[i]) >= P['big_box'][0] * ca and vd <= P['big_box'][1]
    r['box'] = ok & box; ok &= ~box
    # round rings
    ring = np.zeros(n, bool)
    for i in np.nonzero(ok & (holes >= 1))[0]:
        x0, y0, bw, bh = st[i, 0], st[i, 1], st[i, 2], st[i, 3]
        m = np.zeros((bh + 4, bw + 4), np.uint8); m[2:-2, 2:-2] = lb[y0:y0 + bh, x0:x0 + bw] == i
        cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE); c = max(cs, key=len); ca = cv2.contourArea(c); _, (rw, rh), _ = cv2.minAreaRect(c)
        ring[i] = (ca - A[i]) >= 0.6 * ca and max(rw, rh) <= 1.15 * min(rw, rh)
    # big round symbols, closed or broken by a line: outline circular (4 pi area / perimeter^2 >= 0.8), 1.12 or less as long
    # as wide, big_circle px across or more (a lettering O of that size is taller than wide)
    for i in np.nonzero(ok & (ext >= P['big_circle']))[0]:
        x0, y0, bw, bh = st[i, 0], st[i, 1], st[i, 2], st[i, 3]
        m = np.zeros((bh + 4, bw + 4), np.uint8); m[2:-2, 2:-2] = lb[y0:y0 + bh, x0:x0 + bw] == i
        cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE); c = max(cs, key=len); ca = cv2.contourArea(c); _, (rw, rh), _ = cv2.minAreaRect(c)
        hull = cv2.convexHull(c); ha = cv2.contourArea(hull); hp = cv2.arcLength(hull, True)
        if not (4 * np.pi * ha / max(hp * hp, 1) >= 0.8 and max(rw, rh) <= 1.12 * min(rw, rh)): continue
        (cx, cy), R = cv2.minEnclosingCircle(c); ys, xs = np.nonzero(m); d = np.hypot(xs - cx, ys - cy)
        band = (d >= 0.55 * R).mean(); cover = len(np.unique((np.degrees(np.arctan2(ys - cy, xs - cx)) // 10).astype(int)))
        ring[i] |= band >= 0.9 and cover >= 27   # nearly all of it on the rim, round 270 deg or more
    r['ring'] = ok & ring; ok &= ~ring
    # links between lines
    dt = cv2.distanceTransform(cand, cv2.DIST_L2, 3); ridge = (dt > 0) & (dt >= cv2.dilate(dt, np.ones((3, 3), np.uint8)))
    sw = np.maximum(2 * np.bincount(lb[ridge], dt[ridge], n) / np.maximum(np.bincount(lb[ridge], minlength=n), 1), 1.0)
    li = np.nonzero(ok & (holes == 0) & (A / (sw * lg) <= P['big_link']))[0]
    link = np.zeros(n, bool)
    if len(li):
        link[li[ll_contacts(lb, li, st, LL, g + 3) >= 2]] = True
        if line is not None and P.get('big_link_line'):   # ... or line ink of any length at 2 or more places, 3-6 px out
            lm = ((line > 0) | (LL > 0)).astype(np.uint8); rest = li[~link[li]]
            if len(rest): link[rest[line_contacts(lb, rest, st, lm, 3, 6) >= 2]] = True
    # pieces of a line: one stroke with thin ink carrying on from both its ends (a heavy dash of a curved streetcar track)
    thin = (ink & (core == 0)) | LL; onl = np.zeros(n, bool)   # thin ink, or long-line ink of any width
    for i in li:
        if not link[i]: onl[i] = ends_continue(lb, i, st, thin)
    link |= onl
    # ... unless it joins an accepted letter of about its size or bigger (the tail of a 9 crossed by a line)
    lk = np.nonzero(ok & link)[0]
    if len(lk):
        acc0 = (ok & ~link)[lb].astype(np.uint8); near = cv2.dilate(acc0 * lb.astype(np.int32).astype(np.float32), np.ones((19, 19), np.uint8))
        for i in lk:
            x0, y0, bw, bh = st[i, 0], st[i, 1], st[i, 2], st[i, 3]; js = np.unique(near[y0:y0 + bh, x0:x0 + bw][lb[y0:y0 + bh, x0:x0 + bw] == i]).astype(int)
            js = js[js > 0]
            if len(js) and np.any(ext[js] >= 0.6 * ext[i]): link[i] = False
    r['online'] = ok & link & onl; r['link'] = ok & link & ~onl; ok &= ~link
    # lines cut by the sheet edge
    r['edge'] = ok & (lg >= 3 * th) & (np.bincount(lb[(edge > 0) & (lb > 0)], minlength=n) > 0); ok &= ~r['edge']
    # straight bars need a neighbour
    bar = ok & (lg >= P['big_bar'] * th); nb = ok & ~bar
    if bar.any():
        bi = np.nonzero(bar)[0]; ni = np.nonzero(nb)[0]; keep = np.zeros(len(bi), bool)
        if len(ni):
            T = cKDTree(np.c_[mx[ni], my[ni]])
            for t, i in enumerate(bi):
                js = ni[T.query_ball_point([mx[i], my[i]], P['big_bar_nb'] * lg[i])]
                keep[t] = bool(np.any((ext[js] >= 0.5 * ext[i]) & (ext[js] <= 2.0 * ext[i])))
        r['lonebar'] = np.zeros(n, bool); r['lonebar'][bi[~keep]] = True; ok[bi[~keep]] = False
    info.update({k: int(v.sum()) for k, v in r.items()}); info['letters'] = int(ok.sum())
    if DEBUG is not None:   # why each core piece was refused (dev pictures only)
        why = np.zeros(n, np.uint8); why[1:] = 20; why[ok] = 1
        for c_, nm in enumerate(('bar', 'dot', 'cont', 'box', 'lonebar', 'ring', 'link', 'edge', 'online'), 2):
            if nm in r: why[r[nm]] = c_
        DEBUG['big_why'] = why[lb]; DEBUG['LL'] = LL
    acc = ok[lb].astype(np.uint8)
    grown = acc.copy()
    for _ in range(P['big_grow']): grown = cv2.dilate(grown, np.ones((3, 3), np.uint8)) & ink
    letter = grown & ~LL
    return letter, acc, info


def context_rescue(code, ink, LL, LLori, letter, lb, F, k, isdash, edge):
    """finder2: TEXT BY CONTEXT round big letters. Big lettering written over lines comes apart when the line ink is taken
    out: arms and joins of its letters become strokes, dots, jogs or the 1 px rim next to the line, and short straight
    strokes stay line ink. Round each big letter (a letter of big_letters, or a glyph piece 40 px or more across and not
    long and thin) a zone of ctx_r x its size (ctx_rr[0]-ctx_rr[1] px) is drawn. Inside a zone:
      - a piece of step 3 that is not text (stroke, dot, blob, jog, the rim), not part of a dashed line or a tick, and not
        a free stroke 12 px or longer touching no line (a dash of a dashed line broken by the letter, as in -18- on 1A),
        nor a bit ctx_tip px across or less touching a line (it may be the tip of a rail tick: on plate 44 the lower end
        of a VANDALIA tick, next to the D, was taken here), lying ctx_in or more inside the zone, becomes text by context;
      - line ink that is not long-line ink (no straight long_len px line fits it), in a piece ctx_line px across or less
        lying ctx_in or more inside the zone, becomes text by context, unless it is a link between lines (long-line ink within 3 px of it at 2 or more
        separate places) or touches the sheet edge; it must touch text and must not touch a tick end or a dash (the 1 px
        rim between a rail tick and its line is never text). A line that crosses the letter and runs on is long-line ink and stays
        line ink.
    Returns the new code image and counts"""
    n = len(F['A']); E = lambda r: cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))
    nodes = np.zeros(ink.shape, np.uint8); zone = np.zeros(ink.shape, np.uint8)
    ln, llb, lst, _ = cv2.connectedComponentsWithStats(letter, connectivity=8)
    gl = ((k == 'glyph') | (k == 'cluster')) & (F['ext'] >= P['ctx_glyph']) & (F['thick'] >= 0.4 * F['long']); gl[0] = False
    sizes = [(llb, np.maximum(lst[:, 2], lst[:, 3]), ln), (lb, F['ext'], n)]
    for lab, ext, nn in sizes:
        sel = np.zeros(nn, bool)
        if lab is llb: sel[1:] = ext[1:] >= P['ctx_glyph']
        else: sel = gl
        rr = np.clip(np.round(P['ctx_r'] * ext).astype(int), P['ctx_rr'][0], P['ctx_rr'][1])
        for r in np.unique(rr[sel]):
            m = (sel & (rr == r))[lab].astype(np.uint8); zone |= cv2.dilate(m, E(int(r)))
    info = {}
    if not zone.any(): return code, dict(zone_px=0)
    # pieces of step 3
    cand = np.isin(k, ('stroke', 'dot', 'jog')) & ~isdash & ~((k == 'stroke') & (F['touch'] == 0) & (F['long'] >= 12))
    cand &= ~((F['touch'] > 0) & (F['ext'] <= P['ctx_tip'])); cand[0] = False   # a small bit on a line: maybe a tick's tip
    inz = np.bincount(lb[(zone > 0) & (lb > 0)], minlength=n) / np.maximum(np.bincount(lb[lb > 0], minlength=n), 1)
    pc = cand & (inz >= P['ctx_in'])
    sel = pc[lb] & (code == CODE['other']); out = code.copy(); out[sel] = CODE['taken']; info['pieces'] = int(pc.sum())
    # short line ink and the rim (ink that is neither line nor in a piece)
    sl = (((out == CODE['line']) & (LL == 0)) if P['ctx_line'] else np.zeros(ink.shape, bool)) | ((out == CODE['other']) & (lb == 0))
    m2, l2, s2, _ = cv2.connectedComponentsWithStats(sl.astype(np.uint8), connectivity=8)
    in2 = np.bincount(l2[(zone > 0) & (l2 > 0)], minlength=m2) / np.maximum(s2[:, 4], 1); ok2 = (in2 >= P['ctx_in']) & (np.maximum(s2[:, 2], s2[:, 3]) <= P['ctx_line']); ok2[0] = False
    # ... but not a link between two lines, nor a piece at the sheet edge
    ok2 &= ~(np.bincount(l2[(edge > 0) & (l2 > 0)], minlength=m2) > 0)
    b2 = np.nonzero(ok2 & (s2[:, 4] >= 15))[0]
    if len(b2): ok2[b2[ll_contacts(l2, b2, s2, LL, 3) >= 2]] = False
    # ... and only when it touches text, and touches no tick end or dash (the rim between a tick end and its line)
    k3 = np.ones((3, 3), np.uint8); tx = cv2.dilate(np.isin(out, (CODE['glyph'], CODE['taken'])).astype(np.uint8), k3) > 0
    bad = cv2.dilate((np.isin(k, ('tick',)) | isdash)[lb].astype(np.uint8) & (lb > 0), k3) > 0
    ok2 &= np.bincount(l2[tx & (l2 > 0)], minlength=m2) > 0; ok2 &= ~(np.bincount(l2[bad & (l2 > 0)], minlength=m2) > 0)
    sel2 = ok2[l2] & sl; out[sel2] = CODE['taken']; info['line_bits'] = int(ok2.sum()); info['line_px'] = int(((code == CODE['line']) & sel2).sum())
    info['zone_px'] = int(zone.sum())
    return out, info


def shared_ink(code, ink):
    """finder2: where a glyph touches line ink, the ink they share becomes code 4 (both own it: ink sorting gives it to the
    line, training does not score it, the reader adds it back). The touch points are text ink (2, 3) next to line ink (1),
    and other ink (5) next to both (the 1 px rim left between a glyph and the line it touches). Text and other ink within
    share_r px of a touch point and of the line becomes 4. A glyph that runs beside a line without touching it keeps all
    its ink. The line keeps every pixel it had (code 1 is never changed), so it keeps its full width.
    (Tried 25 Nov: every text pixel within 2 px of line ink in an ink piece holding both: on truth v2 T1-T7 three quarters of
    those pixels were text, mostly along figures written beside a line, e.g. 103.96 on plate 5)"""
    r = P['share_r']; E = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1)); k3 = np.ones((3, 3), np.uint8)
    t = np.isin(code, (CODE['glyph'], CODE['taken'])).astype(np.uint8); ln = (code == CODE['line']).astype(np.uint8); o5 = code == CODE['other']
    nl = cv2.dilate(ln, k3) > 0; nt = cv2.dilate(t, k3) > 0
    touch_r = o5 & nl & nt; S0 = ((t > 0) & nl) | touch_r
    sh = (((t > 0) | o5) & (cv2.dilate(S0.astype(np.uint8), E) > 0) & (cv2.dilate(ln, E) > 0)) | touch_r
    out = code.copy(); out[sh] = CODE['shared']; return out, int(sh.sum())


def scale_of(N):
    try: return int(json.load(open('scale_table.json', encoding='utf8'))[N]['ft_per_inch'])
    except Exception: return None


def run(N, win=None, out=None, pic=False, tag=None, verbose=True, scale='table'):
    """scale: 'table' reads the plate's scale from scale_table.json and applies SCALE's settings for it (restored after
    the run); None applies none"""
    ft = scale_of(N) if scale == 'table' else scale; keep = dict(P); P.update(SCALE.get(ft, {}))
    try: return _run(N, win, out, pic, tag, verbose, ft)
    finally: P.clear(); P.update(keep)


def _run(N, win, out, pic, tag, verbose, ft):
    t0 = time.time(); T = {}
    im, ink, paper, (W, H) = load(N, win); T['load'] = time.time() - t0
    line, ori = line_ink(ink); T['line'] = time.time() - t0
    res = (ink & ~(cv2.dilate(line, np.ones((3, 3), np.uint8)) > 0)).astype(np.uint8)
    resf = fill_pinholes(res)   # pinholes (4 px or less) filled for the shape features only
    if P.get('frag_close'):     # finder2, 400 ft plates: faint small figures fall apart at the ink threshold; bridge 1 px gaps
        resf = cv2.morphologyEx(resf, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (P['frag_close'], P['frag_close']))) & cv2.dilate(res, np.ones((3, 3), np.uint8))
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
    # finder2: rail ticks and other cross marks on a line are never text
    tick = tick_ends(F, k, line, ori) if P.get('tick') else np.zeros(n, bool)
    k[tick & np.isin(k, ('stroke', 'dot', 'eq', 'jog', 'blob'))] = 'tick'; isdash |= tick; T['ticks'] = time.time() - t0
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
    cl = np.zeros(n, np.uint8); cl[seed] = CODE['glyph']; cl[taken | eqm | lone] = CODE['taken']
    m = (lb > 0) & (res > 0); cc = cl[lb]; sel = m & (cc > 0); code[sel] = cc[sel]
    # finder2: big lettering with thick strokes
    big = dict()
    if P.get('big_core'):
        LL, LLori = long_ink(ink, P['long_len']); T['long'] = time.time() - t0
        edge = cv2.dilate((paper == 0).astype(np.uint8), np.ones((13, 13), np.uint8))   # 6 px from the paper's edge
        letter, acc, big = big_letters(ink, LL, LLori, bars, edge, line); T['big'] = time.time() - t0
        code[letter > 0] = CODE['glyph']
        # the pieces of step 3 that lie mostly inside a big letter (its arms and joins cut off by the line ink)
        if P.get('big_piece'):
            zone = cv2.dilate(letter, np.ones((5, 5), np.uint8)) > 0
            share = np.bincount(lb[zone & (lb > 0)], minlength=n) / np.maximum(np.bincount(lb[lb > 0], minlength=n), 1)
            pin = (share >= P['big_piece']) & ~seed & ~taken & ~eqm & ~lone; pin[0] = False
            sel = pin[lb] & (res > 0) & (code == CODE['other']); code[sel] = CODE['glyph']; big['pieces_taken'] = int(pin.sum())
        if P.get('ctx_r'):
            code, big['context'] = context_rescue(code, ink, LL, LLori, letter, lb, F, k, isdash, edge); T['context'] = time.time() - t0
    code, nsh = shared_ink(code, ink); T['shared'] = time.time() - t0
    cnt = {name: int((code == v).sum()) for name, v in CODE.items()}
    kc = {kk: int((k == kk).sum()) for kk in ('glyph', 'cluster', 'stroke', 'dot', 'blob', 'long', 'box', 'ring', 'jog', 'eq', 'bar', 'bldg', 'tick')}
    rec = dict(plate=N, win=win, size=[W, H], ft_per_inch=ft, params=dict(P), ink_px=int(ink.sum()), px=cnt, pieces=kc, big=big,
               strokes=dict(total=int(len(st)), dash=int(dash.sum()), carries_line=int(cont.sum()), heavy=int(heavy.sum())),
               text_pieces=dict(seed=int(seed.sum()), taken=int(taken.sum()), eq=int(eqm.sum()), lone=int(lone.sum())),
               seconds={kk: round(v, 1) for kk, v in T.items()}, made=time.strftime('%Y-%m-%d %H:%M'))
    if out:
        os.makedirs(out, exist_ok=True); stem = os.path.join(out, f'{N}_text' + (f'_{tag}' if tag else ''))
        cv2.imwrite(stem + '.png', code)
        json.dump(rec, open(stem + '.json', 'w', encoding='utf8', newline='\n'), indent=1)
        if pic:
            c = overlay(im, code); cv2.imwrite(stem + '.jpg', c if win else cv2.resize(c, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 88])
    if verbose:
        print(f'plate {N} {win or "whole"}: ink {rec["ink_px"]:,} px; text {cnt["glyph"] + cnt["taken"]:,} px '
              f'(sure {cnt["glyph"]:,}, by context {cnt["taken"]:,}); shared {cnt["shared"]:,}; line {cnt["line"]:,}; other {cnt["other"]:,} | big {big} | {T}', flush=True)
    return code, rec, (n, lb, F, k)


def overlay(im, code):
    c = (im * 0.25 + 255 * 0.75).astype(np.uint8)
    for v, col in COLOR.items(): c[code == v] = col
    return c


if __name__ == '__main__':
    a = sys.argv; N = a[1]
    win = tuple(int(v) for v in a[a.index('--win') + 1:a.index('--win') + 5]) if '--win' in a else None
    out = a[a.index('--out') + 1] if '--out' in a else os.path.join(HERE, '..', 'finder2', 'out', 'final')
    tag = a[a.index('--tag') + 1] if '--tag' in a else None
    run(N, win, out, '--pic' in a, tag)
