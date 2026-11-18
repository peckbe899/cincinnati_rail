"""A first, rule-based sorting of a plate's black ink into bins, for Ben to look at in the line editor (17 November 2026).

    cd data/sanborn
    python ../../tools/sanborn/unet/ink_bins.py N [--win X0 Y0 X1 Y1] [--pic OUT.jpg]

Ben, 17 November 2026: "yes, try binning them and showing them in the plate editor so i can see". This is a rough first
guess made by rules at full size, not a trained classifier and not ground truth. It needs the plate's street map
(streetmap/22-N.json, street_map.py). Every dark pixel on the paper gets one bin:

  1 block line        ink on one of Ben's street-map lines
  2 lot line          other line ink in block ground
  3 building outline  ink on the edge of a pink or yellow fill
  4 railroad          a line crossed by a row of ticks (hatched), as along Vandalia on plate 44; see railroad()
  5 streetcar         heavy dashes, as down Hamilton on plate 44
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
"""
import json, sys, time
import numpy as np
import cv2
from scipy.spatial import cKDTree
NAMES = {1: 'block line', 2: 'lot line', 3: 'building outline', 4: 'railroad', 5: 'streetcar', 6: 'water pipe', 7: 'sewer', 8: 'text and numbers', 9: 'not sorted'}
COL = {1: (0, 150, 0), 2: (255, 140, 0), 3: (20, 70, 120), 4: (0, 0, 230), 5: (0, 150, 255), 6: (160, 0, 0), 7: (160, 170, 0), 8: (255, 0, 255), 9: (120, 120, 120)}   # BGR: green, light blue, brown, red, orange, navy, teal, magenta, grey
INK_L = 140      # darker than this (Lab L, 0..255) is ink
RAIL = dict(clear=(5, 6.0), row=4, faint=(3, 4.0), faint_row=10, even=0.12, grow=0.2)   # a clear tick: stroke ends of 5 px or more, 6 px or more apart; 4 in a row. A faint one: 3 px, 4 px apart; 10 in a row and evenly spaced (gaps within 12%)
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

def railroad(ink, closed):
    """Railroad ink: a line crossed by a row of short ticks (Ben: "the railroads (hatched lines like on Vandalia)").

    The first rule judged each connected piece of ink by how many short strokes it carried. That failed both ways: a track
    is joined at every street crossing to the pipe lines, so it was one small part of a plate-wide piece with few ticks for
    its length (most of the Vandalia tracks were missed), and a lot line or pipe line with figures touching it passed.
    This one works from the ticks themselves:
      a tick  = two short strokes on opposite sides of a long line (a figure touching a line is on one side only, so it
                is not a tick), outside every closed block and not beside heavy ink (a streetcar's dashes, a big letter)
      a track = ticks in a row: each within 120 px of the next and no more than 14 px (22 on a tight curve) off the line
                through the other, with ink joining them. The line's direction is read where a 61 px straight line fits
                the ink (a 35 px one on a tight curve).
    Two kinds of row count. Clear ticks (stroke ends of 5 px or more, 6 px or more apart): 4 or more in a row. Faint ticks
    (3 px, 4 px apart: thin tracks drawn close together, as along the south of plate 44): 10 or more in a row, and evenly
    spaced: each tick midway between its neighbours (the two gaps within 12% of each other).
    Tracks on one plate are drawn with different gaps, so there is no single gap to test against.
    A row found either way is then carried on along its own line: a faint tick joins it if it lies one of that row's gaps
    (within 20%), or two where a tick is missing, from a tick already in the row.
    The ink within 7 px of the line through such a row is railroad, with 35 px carried on past each end."""
    h, w = ink.shape; r8 = ink.astype(np.uint8); short = np.zeros((h, w), np.uint8); long_ = np.zeros((h, w), np.uint8)
    ori = np.full((h, w), -1, np.int8); ori2 = np.full((h, w), -1, np.int8)   # which way the line under a pixel runs: where a 61 px line fits (within about 5 degrees), else where a 35 px one does (a tight curve)
    for i in range(24):
        ang = np.pi * i / 24
        short |= cv2.morphologyEx(r8, cv2.MORPH_OPEN, line_kernel(9, ang)); l35 = cv2.morphologyEx(r8, cv2.MORPH_OPEN, line_kernel(35, ang)); long_ |= l35
        ori2[cv2.dilate(l35, np.ones((13, 13), np.uint8)) > 0] = i
        ori[cv2.dilate(cv2.morphologyEx(r8, cv2.MORPH_OPEN, line_kernel(61, ang)), np.ones((13, 13), np.uint8)) > 0] = i   # read up to 6 px off the line: a faint track often breaks at each tick
    stub = short & (1 - long_) & cv2.dilate(long_, np.ones((7, 7), np.uint8))   # ticks on plate 44 run 16 to 24 px, so 'long' is 35 px
    ns, ls, ss, cs = cv2.connectedComponentsWithStats(stub, connectivity=8); M = np.zeros((h, w), np.uint8); info = dict(clear=0, faint=0, chained=0, T=np.zeros((0, 2)), E=[])
    onlong = cv2.dilate(long_, np.ones((13, 13), np.uint8)); near = cv2.dilate(r8, np.ones((9, 9), np.uint8))
    EL = lambda k: cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))   # the dashes print mottled, so close the ink before asking how thick it is
    nh, lh, sh, _ = cv2.connectedComponentsWithStats(cv2.morphologyEx(cv2.morphologyEx(r8, cv2.MORPH_CLOSE, EL(5)), cv2.MORPH_OPEN, EL(9)), connectivity=8)
    bars = sh[:, 4] >= 300; bars[0] = False               # heavy ink: a streetcar dash (some 12 by 100 px) or a big letter. Where a tick crosses a thick-drawn track the blob is far smaller
    heavy = cv2.dilate(bars[lh].astype(np.uint8), np.ones((25, 25), np.uint8))
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components

    def ticks(minarea, dmin):
        """ticks made of stroke ends of minarea px or more, dmin px or more apart: where they are, which way their line runs, how far off it the next may be"""
        ok = (ss[:, 4] >= minarea) & (ss[:, 4] <= 150); ok[0] = False; C = cs[ok]
        if len(C) < 8: return np.zeros((0, 2)), np.zeros((0, 2)), np.zeros(0)
        P = np.array(sorted(cKDTree(C).query_pairs(24)), int).reshape(-1, 2); d = np.hypot(*(C[P[:, 0]] - C[P[:, 1]]).T); m = (C[P[:, 0]] + C[P[:, 1]]) / 2
        keep = (d >= dmin) & (onlong[np.clip(m[:, 1].round().astype(int), 0, h - 1), np.clip(m[:, 0].round().astype(int), 0, w - 1)] > 0)
        P, d, m = P[keep], d[keep], m[keep]; used = np.zeros(len(C), bool); sel = []
        for k in np.argsort(d):                           # each stroke end belongs to one tick: the nearest partner
            a, b = P[k]
            if not used[a] and not used[b]: used[a] = used[b] = True; sel.append(k)
        T = m[sel]; t = C[P[sel, 0]] - C[P[sel, 1]]; t /= np.hypot(*t.T)[:, None]
        ty, tx = np.clip(T[:, 1].round().astype(int), 0, h - 1), np.clip(T[:, 0].round().astype(int), 0, w - 1)
        oi = ori[ty, tx]; tol = np.where(oi >= 0, 14.0, 22.0); oi = np.where(oi >= 0, oi, ori2[ty, tx]); u = np.c_[np.cos(np.pi * oi / 24), np.sin(np.pi * oi / 24)]
        real = (oi >= 0) & (np.abs((t * u).sum(1)) <= 0.7)    # the two stroke ends must lie across the line, not along it
        real &= closed[ty, tx] == 0                           # a row of short strokes inside a block that closes is a lot line with marks on it
        real &= heavy[ty, tx] == 0                            # the corners of a streetcar's heavy dashes stick out of its thin line like ticks
        return T[real], u[real], tol[real]

    def links(T, u, tol, reach):
        """every pair of ticks that could be neighbours on one line: no further apart than `reach`, neither more than its
        tolerance off the line through the other, ink joining them, and not running along a streetcar's heavy dashes"""
        E = []
        if len(T) < 2: return np.zeros((0, 2), int)
        for i, j in cKDTree(T).query_pairs(reach):
            v = T[j] - T[i]; L = np.hypot(*v)
            if L < 25 or abs(v[0] * u[i][1] - v[1] * u[i][0]) > tol[i] or abs(v[0] * u[j][1] - v[1] * u[j][0]) > tol[j]: continue
            q = (T[i][None] + np.linspace(0, 1, 24)[:, None] * v[None]).round().astype(int); qy, qx = np.clip(q[:, 1], 0, h - 1), np.clip(q[:, 0], 0, w - 1)
            if near[qy, qx].mean() >= 0.8 and heavy[qy, qx].mean() < 0.3: E.append((i, j))
        return np.array(E, int).reshape(-1, 2)

    def rows(T, u, E, need, even):
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
        return E[np.bincount(lab, minlength=nc)[lab[E[:, 0]]] >= need]

    Tc, uc, tolc = ticks(*RAIL['clear']); Ec = rows(Tc, uc, links(Tc, uc, tolc, 120), RAIL['row'], 0); info['clear'] = len(Tc)
    Tf, uf, tolf = ticks(*RAIL['faint']); Lf = links(Tf, uf, tolf, 175); info['faint'] = len(Tf)
    Ef = rows(Tf, uf, Lf[np.hypot(*(Tf[Lf[:, 0]] - Tf[Lf[:, 1]]).T) <= 120] if len(Lf) else Lf, RAIL['faint_row'], RAIL['even'])
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
    for T, E in ((Tc, Ec), (Tf, np.vstack([Ef, grown]) if len(Ef) or len(grown) else Ef)):
        if not len(E): continue
        E = np.unique(np.sort(E, axis=1), axis=0); deg = np.bincount(E.ravel(), minlength=len(T)); info['chained'] += int((deg > 0).sum())
        info['E'] = info['E'] + [(a + len(info['T']), b + len(info['T'])) for a, b in E]; info['T'] = np.vstack([info['T'], T])
        for i, j in E: cv2.line(M, tuple(T[i].round().astype(int).tolist()), tuple(T[j].round().astype(int).tolist()), 1, 15)
        for i in np.nonzero(deg == 1)[0]:                 # carry the track 35 px past the last tick of a row
            j = E[(E == i).any(1)][0]; j = j[0] if j[1] == i else j[1]; e = T[i] - T[j]; e /= np.hypot(*e)
            cv2.line(M, tuple(T[i].round().astype(int).tolist()), tuple((T[i] + 35 * e).round().astype(int).tolist()), 1, 15)
    info['grown'] = int(len(grown))
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
    SM = json.load(open(f'streetmap/22-{N}.json', encoding='utf8')); off = np.array([x0, y0])
    truth = np.zeros((h, w), np.uint8); closed = np.zeros((h, w), np.uint8)
    for l in SM['lines']: cv2.line(truth, tuple(np.round(np.array(l['a']) - off).astype(int).tolist()), tuple(np.round(np.array(l['b']) - off).astype(int).tolist()), 1, 13)
    for bl in SM['blocks']: cv2.fillPoly(closed, [np.round(np.array(bl['ring']) - off).astype(np.int32)], 1)
    old = cv2.resize(cv2.imread(f'unet_data/{N}_label.png', 0), (W, H), interpolation=cv2.INTER_NEAREST)[y0:y1, x0:x1]
    ground = np.where(closed == 1, 1, np.where(old == 0, 0, np.where(old == 1, 1, 2))).astype(np.uint8)   # 0 street, 1 block, 2 not known
    out = np.zeros((h, w), np.uint8)
    rr, RAILINFO = railroad(ink, closed); out[rr] = 4; ink0 = ink; ink = ink & ~rr     # the tracks come out first, so they no longer tie the pipe lines together

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
        k[(k == 5) & (g != 0)] = 8                                       # a heavy bar off the street is a figure 1 of a block number
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
        bar = (tk >= 9) & (tk <= 24) & (lg >= 40) & (lg <= 220) & (lg / tk >= 3) & (g == 0); bar[0] = False
        let = ~bar & (np.maximum(st[:, 2], st[:, 3]) <= 200) & (np.maximum(st[:, 2], st[:, 3]) >= 25) & (A >= 150); let[0] = False
        for sel, kind in ((bar, 5), (let, 8)):
            m = (cv2.dilate(sel[lb].astype(np.uint8), E(7)) > 0) & rest; out[m] = kind; rest &= ~m
    out[rest & (ground == 0)] = 6; out[rest & (ground == 1)] = 2; out[rest & (ground == 2)] = 9
    cnt = {NAMES[k]: int((out == k).sum()) for k in NAMES}; ink = ink0; tot = int(ink.sum())
    print(f'plate {N} window {x0},{y0}-{x1},{y1}: ink {tot} px, {100 * tot / max(1, paper.sum()):.1f}% of the paper | {time.time() - t0:.0f} s')
    for k in NAMES: print(f'  {k} {NAMES[k]:17s} {cnt[NAMES[k]]:9d} px  {100 * cnt[NAMES[k]] / max(1, tot):5.1f}%')
    print('  railroad: clear ticks', RAILINFO['clear'], 'faint ticks', RAILINFO['faint'], 'ticks in rows', RAILINFO['chained'], 'links added by carrying rows on', RAILINFO.get('grown'), '| ground of the ink: street', int((ink & (ground == 0)).sum()), 'block', int((ink & (ground == 1)).sum()), 'not known', int((ink & (ground == 2)).sum()))
    if '--pic' in sys.argv:
        c = (im * 0.35 + 255 * 0.65).astype(np.uint8)
        for k in NAMES: c[out == k] = COL[k]
        if '--ticks' in sys.argv:   # debug: stroke ends (black dots), ticks (blue rings), ticks in a row (red rings), links (black)
            for i, j in RAILINFO.get('E', []): cv2.line(c, tuple(RAILINFO['T'][i].round().astype(int).tolist()), tuple(RAILINFO['T'][j].round().astype(int).tolist()), (0, 0, 0), 1)
            for i, p in enumerate(RAILINFO.get('T', [])): cv2.circle(c, tuple(p.round().astype(int).tolist()), 9, (0, 0, 255), 1)
        cv2.imwrite(sys.argv[sys.argv.index('--pic') + 1], c, [cv2.IMWRITE_JPEG_QUALITY, 92])
    if not win:
        cv2.imwrite(f'unet_data/{N}_bins.png', out)
        json.dump(dict(plate=N, size=[W, H], note='rule-based first guess, not ground truth', made=int(time.time()), ink_px=tot, bins={str(k): dict(name=NAMES[k], px=cnt[NAMES[k]], rgb=list(COL[k][::-1])) for k in NAMES}), open(f'unet_data/{N}_bins.json', 'w', encoding='utf8', newline='\n'), indent=1)

if __name__ == '__main__':
    main()
