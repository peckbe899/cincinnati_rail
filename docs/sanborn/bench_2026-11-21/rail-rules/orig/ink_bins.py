"""A first, rule-based sorting of a plate's black ink into bins, for Ben to look at in the line editor (17 November 2026).

    cd data/sanborn
    python ../../tools/sanborn/unet/ink_bins.py N [--win X0 Y0 X1 Y1] [--pic OUT.jpg] [--no-ben] [--save OUT.png]

Ben, 17 November 2026: "yes, try binning them and showing them in the plate editor so i can see". This is a rough first
guess made by rules at full size, not a trained classifier and not ground truth. It needs the plate's street map
(streetmap/22-N.json, street_map.py). Every dark pixel on the paper gets one bin:

  1 block line        ink on one of Ben's street-map lines
  2 lot line          other line ink in block ground
  3 building outline  ink on the edge of a pink or yellow fill
  4 railroad          a line crossed by a row of ticks (hatched), as along Vandalia on plate 44; see railroad()
  5 streetcar         heavy dashes that follow one another along a line, as down Hamilton on plate 44
  6 water pipe        a solid line in street ground that is not a block line (labelled "W. PIPE" on the print)
  7 sewer             thin dashes in street ground (labelled "SEWER" on the print)
  8 text and numbers  small separate marks
  9 not sorted        line ink where the ground is not known

Ben, same day: pipes and sewers are black, not coloured ("the sewage usually is a black line that says 'W. PIPE'"),
the coloured bands are not identified, and rail is two kinds ("the railroads (hatched lines like on Vandalia) and the
street cars (dashes like on Hamilton)"). So nothing here uses colour to tell one black line from another; colour only
finds the building fills.

How: marks are the connected pieces of ink. Small compact pieces are text; thin straight short pieces are dashes
(sewer in the street, dashed lot line in a block); thick straight short pieces are streetcar dashes. The railroad tracks are
found first, from their rows of ticks, and taken out. From the big connected network the block lines and building
outlines are then taken out, which lets the rest fall apart into separate lines: pipe (street ground) or lot line
(block ground). A hatched line is railroad even where one of Ben's street-map lines runs along it. Ground is: inside a shape of the street map that closes = block; elsewhere the old area label
(unet_data/N_label.png, 0 street, 1 block, 255 not known), which was made from the reader's lines, not Ben's.
Writes unet_data/N_bins.png (the bin of every pixel) and unet_data/N_bins.json (counts).

Ben, 18 November 2026: "i need to tell you where they are, you're missing a lot" (the railroad). He draws the tracks in
the line editor (R railroad, S streetcar), saved in picks22_guided/22-N/rail_ben.json. Where that file exists, the ink
within BEN_RAIL px of one of his tracks is that kind, whatever the rules say, and the run prints how much of his
railroad the tick rule had found by itself and how much railroad the rule found away from every track of his.
Ben, same day, asked whether his tracks on plate 44 are all the rail there: "Yes, only mine". Where rail_ben.json says
complete (the tick box in the editor's bins box), rail on that plate is only the ink on his tracks: what the rules call
railroad or streetcar anywhere else goes back to be sorted as other ink (a heavy bar by itself is then a letter stroke).
"""
import json, os, sys, time
import numpy as np
import cv2
from scipy.spatial import cKDTree
NAMES = {1: 'block line', 2: 'lot line', 3: 'building outline', 4: 'railroad', 5: 'streetcar', 6: 'water pipe', 7: 'sewer', 8: 'text and numbers', 9: 'not sorted'}
COL = {1: (0, 150, 0), 2: (255, 140, 0), 3: (20, 70, 120), 4: (0, 0, 230), 5: (0, 150, 255), 6: (160, 0, 0), 7: (160, 170, 0), 8: (255, 0, 255), 9: (120, 120, 120)}   # BGR: green, light blue, brown, red, orange, navy, teal, magenta, grey
INK_L = 140      # darker than this (Lab L, 0..255) is ink
BEN_RAIL = 10     # ink this near (px) a track Ben drew is that track: the ticks reach some 10 px each side of the line
RAIL = dict(clear=(5, 6.0), row=4, faint=(3, 4.0), faint_row=10, even=0.12, grow=0.2, span=150, block_row=6, reach=120, reach2=175, along=0.4, follow=(3000, 400, 10), spur=2, faint_in=1, off=(19.0, 26.0))   # a clear tick: stroke ends of 5 px or more, 6 px or more apart; 4 in a row. A faint one: 3 px, 4 px apart; 10 in a row and evenly spaced (gaps within 12%)
CAR = dict(row=True, street=False)   # a streetcar dash is one of a row of heavy bars that follow one another along a line. Scored on plate 44 against Ben's
# tracks (18 November 2026): any heavy bar in street ground found 79.7% of his streetcar with 12,698 px of false ink (big lettering, thick strokes by pipe
# labels); bars in a row, in any ground, find 85.1% with 1,086 px. The street-ground test cost the line that crosses blocks on the Ludlow viaduct
TEXT_MAX = 130   # a compact mark no bigger than this is text (street-name letters are about 90 px tall on plate 44)

def shape(lab, n):
    """every piece's area, bounding box, length and thickness (from its second moments, as for a straight bar)"""
    ys, xs = np.nonzero(lab); l = lab[ys, xs]; A = np.bincount(l, minlength=n).astype(float); A[A == 0] = 1
    mx = np.bincount(l, xs, n) / A; my = np.bincount(l, ys, n) / A; dx = xs - mx[l]; dy = ys - my[l]
    sxx = np.bincount(l, dx * dx, n) / A; syy = np.bincount(l, dy * dy, n) / A; sxy = np.bincount(l, dx * dy, n) / A
    t = (sxx + syy) / 2; d = np.sqrt(np.maximum(((sxx - syy) / 2) ** 2 + sxy ** 2, 0))
    return A, np.sqrt(12 * (t + d) + 1), np.sqrt(12 * np.maximum(t - d, 0) + 1), mx, my, 0.5 * np.arctan2(2 * sxy, sxx - syy)

def small_kinds(A, long_, thick, ext):
    """0 leave, 8 text, 7 thin dash, 5 streetcar dash, -1 a big piece"""
    k = np.full(len(A), -1, np.int8); fill = A / (long_ * thick)
    k[ext <= TEXT_MAX] = 8
    k[(thick <= 7.5) & (long_ >= 8) & (long_ <= 75) & (long_ / thick >= 3) & (fill >= 0.6) & (fill <= 1.5)] = 7
    k[(thick >= 8) & (thick <= 24) & (long_ >= 35) & (long_ <= 220) & (long_ / thick >= 3) & (fill >= 0.75) & (fill <= 1.4)] = 5
    k[(long_ >= 60) & (thick <= 12) & (long_ / thick >= 6)] = -1   # a straight piece of a broken line is a line, not text
    k[A < 6] = 0
    return k

def line_kernel(length, ang):
    k = np.zeros((length, length), np.uint8); c = length // 2; d = np.array([np.cos(ang), np.sin(ang)]) * c
    cv2.line(k, tuple(np.round(c - d).astype(int).tolist()), tuple(np.round(c + d).astype(int).tolist()), 1, 1); return k

def railroad(ink, closed, paper=None):
    """Railroad ink: a line crossed by a row of short ticks (Ben: "the railroads (hatched lines like on Vandalia)").

    The first rule judged each connected piece of ink by how many short strokes it carried. That failed both ways: a track
    is joined at every street crossing to the pipe lines, so it was one small part of a plate-wide piece with few ticks for
    its length (most of the Vandalia tracks were missed), and a lot line or pipe line with figures touching it passed.
    This one works from the ticks themselves:
      a tick  = two short strokes on opposite sides of a long line (a figure touching a line is on one side only, so it
                is not a tick), not beside a streetcar's heavy dashes
      a track = ticks in a row: each within 120 px of the next and no more than 19 px (26 on a tight curve) off the line
                through the other, with ink joining them. The line's direction is read where a 61 px straight line fits
                the ink (a 35 px one on a tight curve).
    A row must run 150 px or more. One lying mostly inside a closed block (a siding, or a lot line with marks on it) needs
    6 clear ticks, and faint ticks inside a closed block do not count at all.
    Two kinds of row count. Clear ticks (stroke ends of 5 px or more, 6 px or more apart): 4 or more in a row. Faint ticks
    (3 px, 4 px apart: thin tracks drawn close together, as along the south of plate 44): 10 or more in a row, and evenly
    spaced: each tick midway between its neighbours (the two gaps within 12% of each other).
    Tracks on one plate are drawn with different gaps, so there is no single gap to test against.
    A row found either way is then carried on along its own line: a faint tick joins it if it lies one of that row's gaps
    (within 20%), or two where a tick is missing, from a tick already in the row.
    The ink within 7 px of the line through such a row is railroad.

    18 November 2026: Ben drew every track of plate 44 himself ("i need to tell you where they are, you're missing a lot"),
    and the rule is now scored against his tracks (score_rail.py) instead of judged by eye. It found 85.2% of his railroad's
    length, with 2,162 px of ink called railroad away from his tracks. Four changes took that to 98.8% and 2,365 px (of
    which 1,705 px is a real spur he did not draw, and the figures at its end):
      - a straight line must run under a link (ink that a 61 px line fits, under 40% of it or more). The false rows were
        rows of lot numbers, one to a lot: spaced like ticks, ink enough to pass for a line, and no line there at all
      - a link may span one missing tick, if it is twice the gap next to it (doubles)
      - from each end of a row the line is walked on through the stretches that carry no ticks (follow)
      - a short row is a spur if its line runs into a found track (see below)
    Tried and dropped: shorter rows (3 ticks, or 4 in a block) by themselves: 0.5 to 1.4 points more track for two to four
    times the false ink. Still missed on plate 44: a siding drawn as a double line with ticks (track 14, north end)."""
    h, w = ink.shape; r8 = ink.astype(np.uint8); short = np.zeros((h, w), np.uint8); long_ = np.zeros((h, w), np.uint8); long61 = np.zeros((h, w), np.uint8)
    ori = np.full((h, w), -1, np.int8); ori2 = np.full((h, w), -1, np.int8)   # which way the line under a pixel runs: where a 61 px line fits (within about 5 degrees), else where a 35 px one does (a tight curve)
    # a thin track (2 to 3 px) drawn a few degrees off the 24 directions tried has no room for a straight 35 px line inside
    # it, and came out as a string of short strokes with no ticks to tell from it. So the long-line tests run on the ink
    # grown by 1 px; a tick, 16 to 24 px long, is still far too short to pass
    fat = cv2.dilate(r8, np.ones((3, 3), np.uint8))
    for i in range(24):
        ang = np.pi * i / 24
        short |= cv2.morphologyEx(r8, cv2.MORPH_OPEN, line_kernel(9, ang)); l35 = cv2.morphologyEx(fat, cv2.MORPH_OPEN, line_kernel(35, ang)) & r8; long_ |= l35
        ori2[cv2.dilate(l35, np.ones((13, 13), np.uint8)) > 0] = i
        l61 = cv2.morphologyEx(fat, cv2.MORPH_OPEN, line_kernel(61, ang)); long61 |= l61
        ori[cv2.dilate(l61, np.ones((13, 13), np.uint8)) > 0] = i   # read up to 6 px off the line: a faint track often breaks at each tick
    near61 = cv2.dilate(long61 & r8, np.ones((7, 7), np.uint8))   # within 3 px of ink that a 61 px straight line fits
    stub = short & (1 - long_) & cv2.dilate(long_, np.ones((7, 7), np.uint8))   # ticks on plate 44 run 16 to 24 px, so 'long' is 35 px
    ns, ls, ss, cs = cv2.connectedComponentsWithStats(stub, connectivity=8); M = np.zeros((h, w), np.uint8); info = dict(clear=0, faint=0, chained=0, T=np.zeros((0, 2)), E=[])
    onlong = cv2.dilate(long_, np.ones((13, 13), np.uint8)); near = cv2.dilate(r8, np.ones((9, 9), np.uint8))
    EL = lambda k: cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))   # the dashes print mottled, so close the ink before asking how thick it is
    nh, lh, sh, _ = cv2.connectedComponentsWithStats(cv2.morphologyEx(cv2.morphologyEx(r8, cv2.MORPH_CLOSE, EL(5)), cv2.MORPH_OPEN, EL(9)), connectivity=8)
    bars = np.zeros(nh, bool)                             # a streetcar dash is a straight bar some 12 by 100 px, and the dashes follow one another along a line.
    if nh > 1:                                            # The strokes of a big letter are as thick, but a track often runs right beside a street's name
        _, lg, tk, bx, by, ba = shape(lh, nh); bars = (sh[:, 4] >= 300) & (tk >= 7) & (tk <= 26) & (lg >= 35) & (lg <= 240) & (lg / tk >= 2.5); bars[0] = False
        b = np.nonzero(bars)[0]; row = np.zeros(len(b), bool); Pb = np.c_[bx[b], by[b]]
        for i, js in enumerate(cKDTree(Pb).query_ball_point(Pb, 280) if len(b) else []):
            d = np.array([np.cos(ba[b[i]]), np.sin(ba[b[i]])])
            for j in js:
                v = Pb[j] - Pb[i]
                if j != i and abs(v[0] * d[1] - v[1] * d[0]) <= 15 and abs(((ba[b[j]] - ba[b[i]] + np.pi / 2) % np.pi) - np.pi / 2) <= 0.25: row[i] = True; break
        bars[b[~row]] = False
    heavy = cv2.dilate(bars[lh].astype(np.uint8), np.ones((25, 25), np.uint8))
    info_car = cv2.dilate(bars[lh].astype(np.uint8), np.ones((9, 9), np.uint8)) > 0   # the heavy dashes that follow one another along a line
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components

    def ticks(minarea, dmin, blocks=False):
        """ticks made of stroke ends of minarea px or more, dmin px or more apart: where they are, which way their line runs, how far off it the next may be"""
        ok = (ss[:, 4] >= minarea) & (ss[:, 4] <= 150); ok[0] = False; C = cs[ok]
        if len(C) < 8: return np.zeros((0, 2)), np.zeros((0, 2)), np.zeros(0), np.zeros(0, bool)
        P = np.array(sorted(cKDTree(C).query_pairs(24)), int).reshape(-1, 2); d = np.hypot(*(C[P[:, 0]] - C[P[:, 1]]).T); m = (C[P[:, 0]] + C[P[:, 1]]) / 2
        keep = (d >= dmin) & (onlong[np.clip(m[:, 1].round().astype(int), 0, h - 1), np.clip(m[:, 0].round().astype(int), 0, w - 1)] > 0)
        P, d, m = P[keep], d[keep], m[keep]; used = np.zeros(len(C), bool); sel = []
        for k in np.argsort(d):                           # each stroke end belongs to one tick: the nearest partner
            a, b = P[k]
            if not used[a] and not used[b]: used[a] = used[b] = True; sel.append(k)
        T = m[sel]; t = C[P[sel, 0]] - C[P[sel, 1]]; t /= np.hypot(*t.T)[:, None]
        ty, tx = np.clip(T[:, 1].round().astype(int), 0, h - 1), np.clip(T[:, 0].round().astype(int), 0, w - 1)
        oi = ori[ty, tx]; tol = np.where(oi >= 0, RAIL['off'][0], RAIL['off'][1]); oi = np.where(oi >= 0, oi, ori2[ty, tx]); u = np.c_[np.cos(np.pi * oi / 24), np.sin(np.pi * oi / 24)]
        real = (oi >= 0) & (np.abs((t * u).sum(1)) <= 0.7)    # the two stroke ends must lie across the line, not along it
        inb = closed[ty, tx] > 0                              # inside a block that closes: a siding, or a lot line with marks on it
        if not blocks: real &= ~inb
        real &= heavy[ty, tx] == 0                            # the corners of a streetcar's heavy dashes stick out of its thin line like ticks
        return T[real], u[real], tol[real], inb[real]

    def links(T, u, tol, reach):
        """every pair of ticks that could be neighbours on one line: no further apart than `reach`, neither more than its
        tolerance off the line through the other, ink joining them, and not running along a streetcar's heavy dashes"""
        E = []
        if len(T) < 2: return np.zeros((0, 2), int)
        for i, j in cKDTree(T).query_pairs(reach):
            v = T[j] - T[i]; L = np.hypot(*v)
            if L < 25 or abs(v[0] * u[i][1] - v[1] * u[i][0]) > tol[i] or abs(v[0] * u[j][1] - v[1] * u[j][0]) > tol[j]: continue
            q = (T[i][None] + np.linspace(0, 1, 24)[:, None] * v[None]).round().astype(int); qy, qx = np.clip(q[:, 1], 0, h - 1), np.clip(q[:, 0], 0, w - 1)
            if near[qy, qx].mean() < 0.8 or heavy[qy, qx].mean() >= 0.3: continue
            # a straight line must run under the link: a row of lot numbers, one to a lot, is spaced like ticks and its
            # figures are ink enough to pass the test above, but there is no line along it (three such rows on plate 44)
            if near61[qy, qx].mean() >= RAIL['along']: E.append((i, j))
        return np.array(E, int).reshape(-1, 2)

    def doubles(T, E, one):
        """a link longer than `one` stands for a missing tick: it is kept only if it is twice (within 15%) a shorter link
        at one of its two ends. Scored on plate 44 against Ben's tracks: a tick is missed about one time in six"""
        if not len(E): return E
        L = np.hypot(*(T[E[:, 0]] - T[E[:, 1]]).T); short = {}
        for (i, j), l in zip(E, L):
            if l <= one: short.setdefault(i, []).append(l); short.setdefault(j, []).append(l)
        keep = L <= one
        for e in np.nonzero(~keep)[0]: keep[e] = any(abs(L[e] - 2 * s_) <= 0.15 * L[e] for k in E[e] for s_ in short.get(k, []))
        return E[keep]

    def rows(T, u, E, need, even, inb=None):
        """the links of the rows of `need` ticks or more"""
        if not len(E): return E
        if even:   # a tick of a track sits midway between its two neighbours
            V = T[E[:, 1]] - T[E[:, 0]]; Ls = np.hypot(*V.T); kp = np.zeros(len(E), bool); nb = {}
            for e, (i, j) in enumerate(E):
                nb.setdefault(i, []).append((e, Ls[e], np.sign(V[e] @ u[i]))); nb.setdefault(j, []).append((e, Ls[e], np.sign(-V[e] @ u[j])))
            for lst in nb.values():
                for a in range(len(lst)):
                    for b in range(a + 1, len(lst)):
                        lo, hi = sorted((lst[a][1], lst[b][1]))
                        if lst[a][2] * lst[b][2] < 0 and hi - lo <= even * hi: kp[lst[a][0]] = kp[lst[b][0]] = True
            E = E[kp]
            if not len(E): return E
        nc, lab = connected_components(coo_matrix((np.ones(len(E)), (E[:, 0], E[:, 1])), shape=(len(T), len(T))), directed=False)
        keep = np.zeros(nc, bool)
        for c in np.unique(lab[E[:, 0]]):
            p = np.unique(E[lab[E[:, 0]] == c]); n = len(p); span = np.hypot(*(T[p].max(0) - T[p].min(0)))
            keep[c] = n >= need and span >= RAIL['span'] and (inb is None or inb[p].mean() < 0.5 or n >= RAIL['block_row'])
        return E[keep[lab[E[:, 0]]]]

    Tc, uc, tolc, inbc = ticks(*RAIL['clear'], blocks=True); Lc_all = doubles(Tc, links(Tc, uc, tolc, RAIL['reach2']), RAIL['reach']); Ec = rows(Tc, uc, Lc_all, RAIL['row'], 0, inbc); info['clear'] = len(Tc)
    # 19 November 2026, plate 43 (the first plate tried after 44): its ticks south-west of Hoffner are 13 px long where
    # plate 44's are 16 to 24, so most pass only as faint ticks, and faint ticks inside a block used to be dropped. The four
    # tracks were found for 400 px and lost for the next 2,500. Faint ticks inside a block now count for carrying a found
    # row on and for the walk along the line; a row of faint ticks still may not start inside a block. Plate 44's score
    # did not move (98.8%, 2,365 px away). Tried and dropped: shorter stroke ends (7 px for 9): 119,479 px away on plate 44
    Tf, uf, tolf, inbf = ticks(*RAIL['faint'], blocks=bool(RAIL['faint_in'])); Lf = links(Tf, uf, tolf, 175); info['faint'] = len(Tf)
    info['Tc'], info['Tf'] = Tc, Tf   # every tick, in a row or not (for score_rail.py and debugging)
    Ef = rows(Tf, uf, Lf[(np.hypot(*(Tf[Lf[:, 0]] - Tf[Lf[:, 1]]).T) <= 120) & ~inbf[Lf[:, 0]] & ~inbf[Lf[:, 1]]] if len(Lf) else Lf, RAIL['faint_row'], RAIL['even'])   # a row of faint ticks does not start inside a block
    # carry each found row on along its own line: a faint tick joins a row if it is one of the row's gaps (or two, where a
    # tick is missing) from a tick already in it. This fills the stretches where a clear row breaks off, without starting
    # any row that the two rules above did not find
    grown = np.zeros((0, 2), int)
    if len(Ec) and len(Lf):
        gap = np.full(len(Tf), np.nan); _, lab = connected_components(coo_matrix((np.ones(len(Ec)), (Ec[:, 0], Ec[:, 1])), shape=(len(Tc), len(Tc))), directed=False)
        Lc = np.hypot(*(Tc[Ec[:, 0]] - Tc[Ec[:, 1]]).T); med = {c: np.median(Lc[lab[Ec[:, 0]] == c]) for c in np.unique(lab[Ec[:, 0]])}
        dd, ii = cKDTree(Tf).query(Tc[np.unique(Ec)], distance_upper_bound=5)      # the same tick, found by both rules
        for k, c in zip(ii, lab[np.unique(Ec)]):
            if k < len(Tf): gap[k] = med[c]
        adj = {}
        for e, (i, j) in enumerate(Lf): adj.setdefault(i, []).append((j, e)); adj.setdefault(j, []).append((i, e))
        Ll = np.hypot(*(Tf[Lf[:, 0]] - Tf[Lf[:, 1]]).T); todo = list(np.nonzero(~np.isnan(gap))[0]); took = []
        while todo:
            i = todo.pop(); g = gap[i]
            for j, e in adj.get(i, []):
                if abs(Ll[e] - g) <= RAIL['grow'] * g or abs(Ll[e] - 2 * g) <= RAIL['grow'] * g:
                    took.append(e)
                    if np.isnan(gap[j]): gap[j] = g; todo.append(j)
        grown = Lf[np.unique(took)] if took else grown
    offsheet = np.zeros((h, w), np.uint8) if paper is None else cv2.dilate((~paper).astype(np.uint8), np.ones((61, 61), np.uint8))   # within 30 px of the sheet's edge
    allT = cKDTree(np.vstack([Tc, Tf])) if len(Tc) + len(Tf) else None; ends = []; MC = np.zeros((h, w), np.uint8)

    def follow(p, e, M0):
        """Walk on along the line from the last tick of a row, 3 px at a step, keeping to the ink (up to 3 px to either
        side, 10 px across a break) and turning with it. A track runs on without ticks where it nears a switch (130 to
        230 px on plate 44), and a row breaks off where two ticks in a row were missed. The walk goes on while ticks, in
        a row or not, keep coming; it stops where the ink ends, where it meets a track already found, or 400 px after
        the last tick. What was walked is kept whole only if it met a found track or ran off the sheet's edge. Otherwise
        only 40 px past the last tick are kept: on plate 44 a walk left the end of a spur across a dimension figure and
        ran 300 px down a lot line."""
        path = [np.array(p, float)]; gap = 0; quiet = 0; last = 0; onm = 0; why = 'far'; p = path[0]
        for step in range(RAIL['follow'][0] // 3):
            if len(path) >= 8: d = path[-1] - path[-8]; e = d / max(1e-6, np.hypot(*d))
            q = p + 3 * e; n = np.array([-e[1], e[0]]); hit = None
            if not (3 <= q[0] < w - 3 and 3 <= q[1] < h - 3): why = 'edge'; break
            for o in (0, 1, -1, 2, -2, 3, -3):
                c = q + o * n
                if r8[int(round(c[1])), int(round(c[0]))]: hit = c; break
            if hit is None:
                gap += 3; p = q
                if gap > RAIL['follow'][2]: why = 'edge' if offsheet[int(round(q[1])), int(round(q[0]))] else 'end'; break
                continue
            gap = 0; p = hit; path.append(hit); quiet += 3
            if allT is not None and allT.query_ball_point(hit, 8): quiet = 0; last = len(path) - 1
            if quiet > RAIL['follow'][1]: why = 'quiet'; break
            onm = onm + 1 if step >= 12 and M0[int(round(hit[1])), int(round(hit[0]))] else 0
            if onm >= 4: why = 'met'; break
        return (path if why in ('met', 'edge') else path[:last + 14]), why

    for T, E in ((Tc, Ec), (Tf, np.vstack([Ef, grown]) if len(Ef) or len(grown) else Ef)):
        if not len(E): continue
        E = np.unique(np.sort(E, axis=1), axis=0); deg = np.bincount(E.ravel(), minlength=len(T)); info['chained'] += int((deg > 0).sum())
        info['E'] = info['E'] + [(a + len(info['T']), b + len(info['T'])) for a, b in E]; info['T'] = np.vstack([info['T'], T])
        for i, j in E:
            for m_, wd in ((M, 15), (MC, 5)): cv2.line(m_, tuple(T[i].round().astype(int).tolist()), tuple(T[j].round().astype(int).tolist()), 1, wd)
        nbr = {}
        for a, b in E: nbr.setdefault(a, []).append(b); nbr.setdefault(b, []).append(a)
        for i, js in nbr.items():                         # the last tick of a row: every tick it is linked to lies to one side of it (a tick is
            d = T[js] - T[i]; d /= np.hypot(*d.T)[:, None]    # often linked to the next and the one after, so counting links does not find the ends)
            if (d @ d[0] > 0).all(): e = -d.mean(0); ends.append((T[i], e / np.hypot(*e)))
    M0 = MC.copy(); info['walked'] = 0   # 'a track already found' is its centre line, 5 px wide: tracks run side by side as little as 15 px apart
    for p, e in ends:
        path, _ = follow(p, e, M0); info['walked'] += 3 * (len(path) - 1)
        if len(path) >= 2:
            for m_, wd in ((M, 15), (MC, 5)): cv2.polylines(m_, [np.round(np.array(path)).astype(np.int32)], False, 1, wd)
        else: cv2.line(M, tuple(p.round().astype(int).tolist()), tuple((p + 35 * e).round().astype(int).tolist()), 1, 15)
    # Spurs and sidings: a row too short to stand by itself (RAIL['spur'] clear ticks or more, where a row needs 4, or 6 in
    # a block) is still a track if the line it lies on, walked on from one of its ends, runs into a track already found. On plate
    # 44 the sidings of the fan at the west edge carry two or three ticks each
    info['spurs'] = 0
    if len(Lc_all):
        took = {(min(a, b), max(a, b)) for a, b in Ec}; R = np.array([l for l in Lc_all if (min(l), max(l)) not in took], int).reshape(-1, 2)
        if len(R):
            nc, lab = connected_components(coo_matrix((np.ones(len(R)), (R[:, 0], R[:, 1])), shape=(len(Tc), len(Tc))), directed=False); M0 = MC.copy()
            for c in np.unique(lab[R[:, 0]]):
                Ek = R[lab[R[:, 0]] == c]; pk = np.unique(Ek)
                if len(pk) < RAIL['spur'] or MC[tuple(Tc[pk].round().astype(int)[:, ::-1].T)].mean() > 0.5: continue   # too few ticks, or it lies on a track already found
                nbr = {}; walks = []; met = False
                for a, b in Ek: nbr.setdefault(a, []).append(b); nbr.setdefault(b, []).append(a)
                for i, js in nbr.items():
                    d = Tc[js] - Tc[i]; d /= np.hypot(*d.T)[:, None]
                    if (d @ d[0] > 0).all():
                        e = -d.mean(0); path, why = follow(Tc[i], e / np.hypot(*e), M0); walks.append(path); met |= why == 'met'
                if not met: continue
                info['spurs'] += 1
                for m_, wd in ((M, 15), (MC, 5)):
                    for a, b in Ek: cv2.line(m_, tuple(Tc[a].round().astype(int).tolist()), tuple(Tc[b].round().astype(int).tolist()), 1, wd)
                    for path in walks:
                        if len(path) >= 2: cv2.polylines(m_, [np.round(np.array(path)).astype(np.int32)], False, 1, wd)
    info['grown'] = int(len(grown))
    info['carrow'] = info_car
    return (M > 0) & ink, info

def main():
    N = sys.argv[1]; t0 = time.time()
    if '--rail' in sys.argv: RAIL.update(json.loads(sys.argv[sys.argv.index('--rail') + 1]))   # for trying settings, e.g. --rail '{"faint_row": 8}'
    im = cv2.imread(f'cufp/22-{N}.jpg'); H, W = im.shape[:2]
    x0, y0, x1, y1 = (int(v) for v in sys.argv[sys.argv.index('--win') + 1:sys.argv.index('--win') + 5]) if '--win' in sys.argv else (0, 0, W, H)
    win = '--win' in sys.argv; im = im[y0:y1, x0:x1]; h, w = im.shape[:2]
    lab = cv2.cvtColor(im, cv2.COLOR_BGR2LAB); L = lab[..., 0]
    al = np.load(f'cufp/{N}/png_alpha_s4.npy'); paper = cv2.resize(al, (W, H), interpolation=cv2.INTER_NEAREST)[y0:y1, x0:x1] > 0
    ink = (L < INK_L) & paper
    # building fills by colour (pink brick, yellow frame); an opening drops the narrow coloured bands, which are not buildings
    a = cv2.medianBlur(lab[..., 1], 5).astype(np.int16) - 128; b = cv2.medianBlur(lab[..., 2], 5).astype(np.int16) - 128
    fill = (((a >= 7) & (b <= 26)) | (b >= 32)) & (L >= INK_L) & paper
    fill = cv2.morphologyEx(cv2.morphologyEx(fill.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)), cv2.MORPH_OPEN, np.ones((15, 15), np.uint8))
    near_fill = cv2.dilate(fill, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))) > 0
    deep_fill = cv2.erode(fill, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (19, 19))) > 0   # well inside a fill: a number printed on a building
    # ground and the block lines, from the street map
    # A plate without a street map (only plate 44 has one, 19 November 2026) still runs: the blocks are then the old
    # label's, there are no block lines, and the result says so. That is enough to try the rail rules on another plate;
    # the other bins of such a run are not to be trusted
    smf = f'streetmap/22-{N}.json'; NOMAP = not os.path.exists(smf)
    SM = dict(lines=[], blocks=[]) if NOMAP else json.load(open(smf, encoding='utf8')); off = np.array([x0, y0])
    truth = np.zeros((h, w), np.uint8); closed = np.zeros((h, w), np.uint8)
    for l in SM['lines']: cv2.line(truth, tuple(np.round(np.array(l['a']) - off).astype(int).tolist()), tuple(np.round(np.array(l['b']) - off).astype(int).tolist()), 1, 13)
    for bl in SM['blocks']: cv2.fillPoly(closed, [np.round(np.array(bl['ring']) - off).astype(np.int32)], 1)
    lf = f'unet_data/{N}_label.png'   # the old street / block label; a plate that was never placed has none, and all its ground is then 'not known'
    old = cv2.resize(cv2.imread(lf, 0), (W, H), interpolation=cv2.INTER_NEAREST)[y0:y1, x0:x1] if os.path.exists(lf) else np.full((h, w), 255, np.uint8)
    if NOMAP: closed = (old == 1).astype(np.uint8); print(f'plate {N} has no street map (streetmap/22-{N}.json): blocks from the old label' + ('' if os.path.exists(lf) else ' (and there is no old label: no blocks at all)') + ', no block lines. Only the rail bins of this run mean anything')
    ground = np.where(closed == 1, 1, np.where(old == 0, 0, np.where(old == 1, 1, 2))).astype(np.uint8)   # 0 street, 1 block, 2 not known
    out = np.zeros((h, w), np.uint8)
    rr, RAILINFO = railroad(ink, closed, paper); ink0 = ink; carrow = RAILINFO['carrow']
    if '--car' in sys.argv: CAR.update(json.loads(sys.argv[sys.argv.index('--car') + 1]))
    # the tracks Ben drew himself: his word, over the rules
    bf = f'picks22_guided/22-{N}/rail_ben.json'; BJ = json.load(open(bf, encoding='utf8')) if os.path.exists(bf) and '--no-ben' not in sys.argv else {}; BEN = BJ.get('tracks', []); ONLY = bool(BJ.get('complete'))   # ONLY: his tracks are all the rail on this plate
    ben = {k: np.zeros((h, w), np.uint8) for k in ('railroad', 'streetcar')}; benlen = dict(railroad=0.0, streetcar=0.0); samp = []
    for t in BEN:
        p = np.array(t['pts'], float) - off; cv2.polylines(ben[t['kind']], [np.round(p).astype(np.int32)], False, 1, 2 * BEN_RAIL + 1)
        for q0, q1 in zip(p[:-1], p[1:]):
            L = np.hypot(*(q1 - q0)); benlen[t['kind']] += L
            if t['kind'] == 'railroad': samp.append(q0[None] + np.linspace(0, 1, max(2, int(L / 5) + 1))[:, None] * (q1 - q0)[None])
    bensay = ''
    if BEN:
        nr = sum(t['kind'] == 'railroad' for t in BEN); bensay = f"Your rail: {nr} railroad track{'' if nr == 1 else 's'} ({benlen['railroad']:,.0f} px), {len(BEN) - nr} streetcar ({benlen['streetcar']:,.0f} px)."
        if samp:   # how much of Ben's railroad the tick rule had found, and what the rule found away from his tracks
            q = np.vstack(samp).round().astype(int); ok = (q[:, 0] >= 0) & (q[:, 0] < w) & (q[:, 1] >= 0) & (q[:, 1] < h); q = q[ok]
            got = cv2.dilate(rr.astype(np.uint8), np.ones((2 * BEN_RAIL + 1, 2 * BEN_RAIL + 1), np.uint8))[q[:, 1], q[:, 0]].mean() if len(q) else 0.0
            far = int((rr & (cv2.dilate(ben['railroad'], np.ones((31, 31), np.uint8)) == 0)).sum())
            bensay += f" The tick rule had found {100 * got:.0f}% of your railroad's length by itself, and {far:,} px of what it calls railroad lies more than 25 px from every track of yours."
        rr = ((rr & (ben['streetcar'] == 0)) if not ONLY else np.zeros_like(rr)) | (ink & (ben['railroad'] > 0))
        if ONLY: bensay += ' Only your tracks count as rail on this plate.'
    car = ink & (ben['streetcar'] > 0) & ~rr
    out[rr] = 4; out[car] = 5; ink = ink & ~rr & ~car     # the tracks come out first, so they no longer tie the pipe lines together

    def small_pass(mask):
        """sort the small pieces of mask; returns what is left (the big pieces)"""
        n, lb, st, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), connectivity=8)
        A, lg, th, mx, my, an = shape(lb, n); ext = np.maximum(st[:, 2], st[:, 3]); k = small_kinds(A, lg, th, ext); k[0] = 0
        g = ground[np.clip(my.round().astype(int), 0, h - 1), np.clip(mx.round().astype(int), 0, w - 1)]
        k[(k == 7) & (g == 1)] = 2; k[(k == 7) & (g == 2)] = 9          # a thin dash in a block is a dashed lot line
        # a sewer is a row of dashes end to end. A thin stroke in the street with no other dash carrying on its line is a
        # figure 1 or a hyphen of a house number
        d = np.nonzero((k == 7) & (g == 0))[0]
        if len(d):
            P = np.c_[mx[d], my[d]]; T = cKDTree(P); chained = np.zeros(len(d), bool)
            for i, js in enumerate(T.query_ball_point(P, 160)):
                u = np.array([np.cos(an[d[i]]), np.sin(an[d[i]])])
                for j in js:
                    if j == i: continue
                    v = P[j] - P[i]; along = abs(v @ u); across = abs(v[0] * -u[1] + v[1] * u[0]); da = abs(((an[d[j]] - an[d[i]] + np.pi / 2) % np.pi) - np.pi / 2)
                    if across <= 7 and da <= 0.2 and along <= (lg[d[i]] + lg[d[j]]) / 2 + 45: chained[i] = True; break
            k[d[~chained]] = 8
        k[(k == 5) & (((g != 0) & CAR['street']) | ONLY)] = 8                              # a heavy bar off the street is a figure 1 of a block number; so is any, where Ben's tracks are all the rail
        if CAR['row']: k[(k == 5) & ~(np.bincount(lb.ravel(), carrow.ravel(), n) > 0)] = 8   # and so is a bar with no other bar carrying on its line
        kk = k[lb]; sel = mask & (kk > 0); out[sel] = kk[sel]; return mask & (kk == -1)

    big = small_pass(ink)
    blk = big & (truth == 1); out[blk] = 1
    bld = big & ~blk & near_fill; out[bld] = 3
    rest = small_pass(big & ~blk & ~bld)
    # text printed on a building is cut off from the page by its outline: a small piece that is all near a fill reads as outline. Put it back
    n, lb, st, _ = cv2.connectedComponentsWithStats((out == 3).astype(np.uint8), connectivity=8); A = st[:, 4].astype(float)
    indeep = np.bincount(lb.ravel(), deep_fill.ravel(), n) / np.maximum(A, 1); ext = np.maximum(st[:, 2], st[:, 3])
    txt = (ext <= TEXT_MAX) & (indeep >= 0.5); txt[0] = False; out[txt[lb] & (out == 3)] = 8
    # streetcar dashes that touch the thin line beside them: the parts of what is left that are 9 px thick or more
    # and letters that a line runs through (a street name crossed by a pipe line): thick, but not a bar
    E = lambda k: cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
    th = cv2.morphologyEx(cv2.morphologyEx(rest.astype(np.uint8), cv2.MORPH_CLOSE, E(5)), cv2.MORPH_OPEN, E(7))
    n, lb, st, _ = cv2.connectedComponentsWithStats(th, connectivity=8)
    if n > 1:
        A, lg, tk, mx, my, _ = shape(lb, n); g = ground[np.clip(my.round().astype(int), 0, h - 1), np.clip(mx.round().astype(int), 0, w - 1)]
        bar = (tk >= 9) & (tk <= 24) & (lg >= 40) & (lg <= 220) & (lg / tk >= 3) & ((g == 0) | (not CAR['street'])); bar[0] = False
        if CAR['row']: bar &= np.bincount(lb.ravel(), carrow.ravel(), n) > 0
        let = ~bar & (np.maximum(st[:, 2], st[:, 3]) <= 200) & (np.maximum(st[:, 2], st[:, 3]) >= 25) & (A >= 150); let[0] = False
        for sel, kind in ((bar, 5), (let, 8))[ONLY:]:                    # where Ben's tracks are all the rail, a bar on a line stays line ink
            m = (cv2.dilate(sel[lb].astype(np.uint8), E(7)) > 0) & rest; out[m] = kind; rest &= ~m
    out[rest & (ground == 0)] = 6; out[rest & (ground == 1)] = 2; out[rest & (ground == 2)] = 9
    cnt = {NAMES[k]: int((out == k).sum()) for k in NAMES}; ink = ink0; tot = int(ink.sum())
    print(f'plate {N} window {x0},{y0}-{x1},{y1}: ink {tot} px, {100 * tot / max(1, paper.sum()):.1f}% of the paper | {time.time() - t0:.0f} s')
    for k in NAMES: print(f'  {k} {NAMES[k]:17s} {cnt[NAMES[k]]:9d} px  {100 * cnt[NAMES[k]] / max(1, tot):5.1f}%')
    print('  railroad: clear ticks', RAILINFO['clear'], 'faint ticks', RAILINFO['faint'], 'ticks in rows', RAILINFO['chained'], 'links added by carrying rows on', RAILINFO.get('grown'), '| ground of the ink: street', int((ink & (ground == 0)).sum()), 'block', int((ink & (ground == 1)).sum()), 'not known', int((ink & (ground == 2)).sum()))
    if bensay: print('  ' + bensay)
    if '--pic' in sys.argv:
        c = (im * 0.35 + 255 * 0.65).astype(np.uint8)
        for k in NAMES: c[out == k] = COL[k]
        if '--ticks' in sys.argv:   # debug: stroke ends (black dots), ticks (blue rings), ticks in a row (red rings), links (black)
            for i, j in RAILINFO.get('E', []): cv2.line(c, tuple(RAILINFO['T'][i].round().astype(int).tolist()), tuple(RAILINFO['T'][j].round().astype(int).tolist()), (0, 0, 0), 1)
            for i, p in enumerate(RAILINFO.get('T', [])): cv2.circle(c, tuple(p.round().astype(int).tolist()), 9, (0, 0, 255), 1)
        cv2.imwrite(sys.argv[sys.argv.index('--pic') + 1], c, [cv2.IMWRITE_JPEG_QUALITY, 92])
    if '--save' in sys.argv: cv2.imwrite(sys.argv[sys.argv.index('--save') + 1], out); return   # the bins to a file of its own (for scoring the rules), leaving the plate's bins alone
    if not win:
        cv2.imwrite(f'unet_data/{N}_bins.tmp.png', out); os.replace(f'unet_data/{N}_bins.tmp.png', f'unet_data/{N}_bins.png')   # the editor may be reading it
        json.dump(dict(plate=N, size=[W, H], note='rule-based first guess, not ground truth' + (' | NO STREET MAP: blocks from the old label, no block lines' if NOMAP else ''), made=int(time.time()), ink_px=tot, ben_rail=bensay, bins={str(k): dict(name=NAMES[k], px=cnt[NAMES[k]], rgb=list(COL[k][::-1])) for k in NAMES}), open(f'unet_data/{N}_bins.json', 'w', encoding='utf8', newline='\n'), indent=1)

if __name__ == '__main__':
    main()
