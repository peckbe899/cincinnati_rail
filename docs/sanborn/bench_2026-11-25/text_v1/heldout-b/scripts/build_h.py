"""Build the held-out text truth H3 / H4 from the hand annotation (annot/Hn.txt) and the ink alone.
python -B build_h.py H4 [--check] [--tiles tw th scale]

Written from scratch for heldout-b. It uses only the scan, the paper mask and the hand annotation. No finder, words,
shapes or other prototype output is read, and no truth of Ben's (street map, rail, lines).

ANNOTATION (full-plate px; typed by eye from the 2-2.5x reading tiles work/Hn_read_RC.jpg)
  x1 y1 x2 y2 h | reading | kind [| flags]
      one word: its centre line from the middle of the first glyph's leading edge to the middle of the last glyph's
      trailing edge, in reading order (so the angle is the reading direction: 0 left to right, 90 reading downwards,
      -90 reading upwards); h the glyph height. Kinds and flags as in text/inventory/truth/README.md.
  flags as in the T truth (partial, unsure, run, curved, nosnap, g:NAME) plus tight: the box is kept as typed and
      grown by only 2 px (a figure inside a small framed building, a glyph in a dense spot).
  NOT x0 y0 x1 y1 [note]    ink in the box is not text (1)
  TEXT x0 y0 x1 y1 [note]   ink in the box is text (2)
  CARE x0 y0 x1 y1 [note]   ink in the box is don't care (3)
  NOTS x1 y1 x2 y2 w [note] ink in the strip (centre line, full width w) is not text (1)
  CARES x1 y1 x2 y2 w [note] text ink in the strip becomes don't care (3): a line crossing glyphs
  TEXTS x1 y1 x2 y2 w [note] ink in the strip is text (2)
  # comment
  The hand fixes are applied after all words, in file order, so a later line wins.

COMPONENT LABELLING (the automatic part)
  Ink = Lab L < 140 on the paper (hcommon.window). 8-connected components of the ink in the window plus PAD px.
  For each word, its box is the typed box grown by 0.15 h + 4 px along and 0.15 h + 3 px across.
  - A component with at least 70% of its pixels in the grown box is a glyph piece: all of it is text.
  - A component with less is ink the word shares with something longer (a block, lot or building line). Inside the
    grown box, its pixels on a straight run of max(31, 1.5 h) px or more (hcommon.straight_runs, found on the whole
    window, so a line keeps its full length) stay line ink; the rest of its in-box pixels are text; and its line
    pixels within 2 px of that text become don't care (3): the shared ink.
  The word box written to Hn_words.json is the tight box of the word's text pixels along the typed angle.

MASK  heldout/Hn_mask.png, the size of the window: 0 paper, 1 non-text ink, 2 text ink, 3 don't care.
WORDS heldout/Hn_words.json, the same fields as text/inventory/truth/T#_words.json.
CHECK work/Hn_check_RC.jpg: text red, don't care yellow, other ink grey, word boxes magenta with their annotation
  line number; small compact pieces of non-text ink (possible missed glyphs) cyan."""
import sys, os, re, math, json
import numpy as np, cv2
from scipy import ndimage as ndi
from hcommon import CROPS, OUT, WORK, ANNOT, PAD, window, straight_runs, rbox, poly_of, jdump

KINDS = {'street', 'house', 'lotdim', 'lot', 'block', 'owner', 'bldg', 'story', 'pipe', 'sewer', 'rail', 'adj',
         'ditto', 'other'}
FLAGS = {'partial', 'unsure', 'run', 'curved', 'nosnap', 'tight'}


def parse(cid):
    words, ops = [], []
    for k, raw in enumerate(open(os.path.join(ANNOT, f'{cid}.txt'), encoding='utf8')):
        s = raw.strip()
        if not s or s.startswith('#'): continue
        f = s.split()
        if f[0] in ('NOT', 'TEXT', 'CARE'):
            ops.append(dict(op=f[0], box=[int(v) for v in f[1:5]], note=' '.join(f[5:]), line=k + 1)); continue
        if f[0] in ('NOTS', 'CARES', 'TEXTS'):
            ops.append(dict(op=f[0], seg=[float(v) for v in f[1:5]], w=float(f[5]), note=' '.join(f[6:]), line=k + 1))
            continue
        parts = [q.strip() for q in s.split('|')]
        g = [float(v) for v in parts[0].split()]
        if len(g) != 5: raise SystemExit(f'{cid} line {k + 1}: need x1 y1 x2 y2 h: {s}')
        kind = parts[2]
        if kind not in KINDS: raise SystemExit(f'{cid} line {k + 1}: unknown kind {kind}')
        flags = parts[3].split() if len(parts) > 3 else []
        for fl in flags:
            if fl not in FLAGS and not fl.startswith('g:'): raise SystemExit(f'{cid} line {k + 1}: unknown flag {fl}')
        words.append(dict(geo=g, reading=parts[1], kind=kind, flags=flags, line=k + 1))
    return words, ops


def strip_mask(shape, ox, oy, seg, w):
    x1, y1, x2, y2 = seg; m = np.zeros(shape, np.uint8)
    cv2.line(m, (int(round(x1 - ox)), int(round(y1 - oy))), (int(round(x2 - ox)), int(round(y2 - oy))), 1,
             max(1, int(round(w))))
    return m > 0


def presnap(c, u, v, L, h, lab, sizes, objs, r21):
    """Correct the typed box from the free glyph pieces near it. A piece counts when it is glyph sized (its box at
    most 2.2 h + 4 px each way) and its centre lies in the typed box grown by 0.2 h + 4 along and 0.25 h + 4 across.
    A speck (under max(8, 0.02 h^2) px) or a thin long piece (its least rectangle at most max(5, 0.2 h) px wide and
    2.5 times as long: a dash, a broken piece of a line, also a lone figure 1) is not used. The box then takes their middle across (and their height, if larger than 0.9 h), and the union of the typed
    length and their extent along. With no free piece the typed box is kept (a word wholly joined to lines)."""
    R = int(L / 2 + h + 12)
    x0, y0 = int(c[0] - R), int(c[1] - R)
    x0, y0 = max(0, x0), max(0, y0); x1, y1 = min(lab.shape[1], int(c[0] + R)), min(lab.shape[0], int(c[1] + R))
    ids = np.unique(lab[y0:y1, x0:x1]); ids = ids[ids > 0]
    lim = 2.2 * h + 4; pts = []
    for k in ids:
        sl = objs[k - 1]
        if sl[0].stop - sl[0].start > lim or sl[1].stop - sl[1].start > lim: continue
        m = lab[sl] == k
        if sizes[k] < max(8, 0.02 * h * h): continue                       # a speck
        ys, xs = np.nonzero(m); xs = xs + sl[1].start; ys = ys + sl[0].start
        (_, _), (rw, rh), _ = cv2.minAreaRect(np.stack([xs, ys], 1).astype(np.float32))
        sh, lo = min(rw, rh) + 1, max(rw, rh) + 1
        if sh <= max(5, 0.2 * h) and lo >= 2.5 * sh: continue                # thin and long: a dash, a line piece, a 1
        mx, my = xs.mean() - c[0], ys.mean() - c[1]
        a, b = mx * u[0] + my * u[1], mx * v[0] + my * v[1]
        if abs(a) <= L / 2 + 0.2 * h + 4 and abs(b) <= h / 2 + 0.25 * h + 4:
            pts.append(np.stack([(xs - c[0]) * u[0] + (ys - c[1]) * u[1], (xs - c[0]) * v[0] + (ys - c[1]) * v[1]], 1))
    if not pts: return c, L, h
    P = np.concatenate(pts)
    ga = 0.3 * h + 6                              # an end may grow by at most this
    a0 = max(min(-L / 2, P[:, 0].min() - 0.5), -L / 2 - ga)
    a1 = min(max(L / 2, P[:, 0].max() + 0.5), L / 2 + ga)
    c0, c1 = np.percentile(P[:, 1], 3) - 0.5, np.percentile(P[:, 1], 97) + 0.5
    sc = float(np.clip(np.median(P[:, 1]), -(0.25 * h + 4), 0.25 * h + 4))   # shift across: the ink's median, bounded
    hn = float(np.clip(c1 - c0 + 1, 0.9 * h, 1.25 * h))
    if P[:, 0].max() - P[:, 0].min() < 0.4 * L:      # too little free ink to place the word across: keep the typed line
        sc, hn = 0.0, h
    cn = c + u * (a0 + a1) / 2 + v * sc
    return cn, a1 - a0, hn


def line_local(ink, c, u, v, L, h, ma, mc, Lrun, nang=48):
    """The line ink a word box shares: around the grown box (plus Lrun px), the pieces of straight runs of Lrun px or
    more (one opening per direction, after a 3x3 closing) that lie partly in the grown box and reach at least 8 px
    out of it, grown by 2 px for their ragged edge; and the bridged runs at least 2 Lrun long and at most 5 px thick
    on average that pass through the
    box and out of it (a broken, dotted line: the opening is made after a further 7 px closing along that
    direction, which bridges the breaks), on their ink and not grown. A straight stroke wholly inside the box (a long diagonal of an
    italic 2 or 7 meeting the next glyph) is not a line. Returns a full-size bool mask, empty away from the box."""
    P = poly_of(c, u, v, L + 2 * ma, h + 2 * mc)
    H, W = ink.shape
    x0, y0 = max(0, int(P[:, 0].min()) - Lrun - 3), max(0, int(P[:, 1].min()) - Lrun - 3)
    x1, y1 = min(W, int(P[:, 0].max()) + Lrun + 4), min(H, int(P[:, 1].max()) + Lrun + 4)
    sub = ink[y0:y1, x0:x1]
    yy, xx = np.mgrid[y0:y1, x0:x1]
    dx, dy = xx - c[0], yy - c[1]
    ib = (np.abs(dx * u[0] + dy * u[1]) <= L / 2 + ma) & (np.abs(dx * v[0] + dy * v[1]) <= h / 2 + mc)
    cl = cv2.morphologyEx(sub.astype(np.uint8), cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
    out = np.zeros(sub.shape, bool); outb = np.zeros(sub.shape, bool); k0 = Lrun // 2
    for i in range(nang):
        a = math.pi * i / nang; k = np.zeros((Lrun, Lrun), np.uint8)
        d = np.array([math.cos(a), math.sin(a)]) * (Lrun - 1) / 2
        cv2.line(k, (int(round(k0 - d[0])), int(round(k0 - d[1]))), (int(round(k0 + d[0])), int(round(k0 + d[1]))), 1, 1)
        k7 = np.zeros((7, 7), np.uint8); d7 = np.array([math.cos(a), math.sin(a)]) * 3
        cv2.line(k7, (int(round(3 - d7[0])), int(round(3 - d7[1]))), (int(round(3 + d7[0])), int(round(3 + d7[1]))), 1, 1)
        cla = cv2.morphologyEx(cl, cv2.MORPH_CLOSE, k7)           # bridge breaks of a faint line along its direction
        Oc = cv2.morphologyEx(cla, cv2.MORPH_OPEN, k) > 0          # the runs, small breaks bridged
        if not (Oc & sub & ib).any(): continue
        O = (cv2.morphologyEx(cl, cv2.MORPH_OPEN, k) > 0) & sub      # the runs without bridging, for (a)
        # (a) pieces of run ink, split where the ink breaks, that lie partly in the box and reach out of it
        n, lb = cv2.connectedComponents(O.astype(np.uint8), connectivity=8)
        nin = np.bincount(lb[O & ib], minlength=n); nout = np.bincount(lb[O & ~ib], minlength=n)
        keep = (nin > 0) & (nout >= 8); keep[0] = False
        out |= keep[lb]
        # (b) a broken line: a bridged run at least 2 Lrun long that passes through the box and out of it. The length
        # test keeps out short runs that the bridging makes through a glyph and a nearby line.
        n2, lb2 = cv2.connectedComponents(Oc.astype(np.uint8), connectivity=8)
        Ob = Oc & sub
        nin2 = np.bincount(lb2[Ob & ib], minlength=n2); nout2 = np.bincount(lb2[Ob & ~ib], minlength=n2)
        cand = np.nonzero((nin2 > 0) & (nout2 >= 8))[0]; cand = cand[cand > 0]
        if len(cand):
            pr = xx * math.cos(a) + yy * math.sin(a)
            ext = np.asarray(ndi.maximum(pr, lb2, cand)) - np.asarray(ndi.minimum(pr, lb2, cand))
            area = np.bincount(lb2.ravel(), minlength=n2)[cand]
            # long, and thin (at most 5 px thick on average): a row of glyphs closed into a band is not a line
            keep2 = np.zeros(n2, bool); keep2[cand[(ext >= 2 * Lrun) & (area <= 5 * (ext + 1))]] = True
            outb |= keep2[lb2] & sub
    R = np.zeros(ink.shape, bool)
    R[y0:y1, x0:x1] = ((cv2.dilate(out.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0) | outb) & sub
    return R


def build(cid):
    cr = CROPS[cid]; p = cr['plate']; X0, Y0, X1, Y1 = cr['win']
    img, ink, (ox, oy, ex, ey) = window(p, X0 - PAD, Y0 - PAD, X1 + PAD, Y1 + PAD)
    hh, ww = ink.shape
    lab, nlab = ndi.label(ink, structure=np.ones((3, 3), int))
    sizes = np.bincount(lab.ravel(), minlength=nlab + 1)
    objs = ndi.find_objects(lab)
    r21 = straight_runs(ink, 21)
    words, ops = parse(cid)
    runs = {}
    yy, xx = np.mgrid[0:hh, 0:ww]
    text = np.zeros(ink.shape, bool); care = np.zeros(ink.shape, bool)
    owner = np.full(ink.shape, -1, np.int32)
    out_words = []
    for i, w in enumerate(words):
        x1, y1, x2, y2, h = w['geo']
        c, u, v, L, h, ang = rbox(x1, y1, x2, y2, h)
        c = c - np.array([ox, oy]); h_typed = h
        if 'nosnap' not in w['flags'] and 'tight' not in w['flags']:
            c, L, h = presnap(c, u, v, L, h, lab, sizes, objs, r21)
        ma, mc = (0.15 * h + 4, 0.15 * h + 3) if 'tight' not in w['flags'] else (2.0, 2.0)
        P = poly_of(c, u, v, L + 2 * ma, h + 2 * mc)
        bx0, by0 = np.floor(P.min(0)).astype(int); bx1, by1 = np.ceil(P.max(0)).astype(int) + 1
        bx0, by0 = max(0, bx0), max(0, by0); bx1, by1 = min(ww, bx1), min(hh, by1)
        sub_x, sub_y = xx[by0:by1, bx0:bx1], yy[by0:by1, bx0:bx1]
        dx, dy = sub_x - c[0], sub_y - c[1]
        al, ac = dx * u[0] + dy * u[1], dx * v[0] + dy * v[1]
        inbox = (np.abs(al) <= L / 2 + ma) & (np.abs(ac) <= h / 2 + mc)
        sl = lab[by0:by1, bx0:bx1]; sink = ink[by0:by1, bx0:bx1]
        ids, cnt = np.unique(sl[inbox & sink], return_counts=True)
        touches = False
        Lrun = int(max(31, round(1.5 * h_typed)))
        Rf = line_local(ink, c, u, v, L, h, ma, mc, Lrun)
        minfrag = max(6, int(0.012 * h * h))
        T = np.zeros(ink.shape, bool); C = np.zeros(ink.shape, bool); S = np.zeros(ink.shape, bool)
        full_ids = []
        for cid_, n_in in zip(ids, cnt):
            if cid_ == 0: continue
            o = objs[cid_ - 1]; m = lab[o] == cid_
            oy_, ox_ = np.mgrid[o[0], o[1]]
            ddx, ddy = ox_ - c[0], oy_ - c[1]
            ib = (np.abs(ddx * u[0] + ddy * u[1]) <= L / 2 + ma) & (np.abs(ddx * v[0] + ddy * v[1]) <= h / 2 + mc)
            if n_in >= 0.7 * sizes[cid_]:
                part = m; full_ids.append(int(cid_))        # a glyph piece: all of it, wherever it reaches
            else:
                part = m & ib                                # shared with something longer: only the part in the box
            Rk = Rf[o] & part
            if not Rk.any():
                t = part
            else:
                # a straight run of Lrun px or more is line ink, never text, even inside a glyph piece; crumbs left
                # along a line (edge noise, joins) are given to the line
                t = part & ~Rk
                crumbs = np.zeros(t.shape, bool)
                tl, tn = ndi.label(t, structure=np.ones((3, 3), int))
                if tn:
                    ts = np.bincount(tl.ravel(), minlength=tn + 1)
                    tin = np.bincount(tl[ib], minlength=tn + 1)
                    far = tin < 0.5 * ts; far[0] = False              # mostly out of the box: the far end of a line
                    small = (ts < minfrag) & ~far; small[0] = False   # crumbs in the box: glyph bit or line edge
                    crumbs = small[tl]
                    t &= ~(small | far)[tl]
                near = cv2.dilate(t.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
                C[o] |= (part & ~t & near) | crumbs
                # touches_line: glyph ink of the word is joined to line ink that runs out of the box
                if Rk.sum() >= 8 and t.sum() >= minfrag and (Rk & near).any(): touches = True
                S[o] |= t
            T[o] |= t
        text |= T; care |= C
        owner[T & (owner < 0)] = i
        wsplit = S
        by0 = bx0 = 0
        sy, sx = np.nonzero(wsplit)
        sy, sx = sy + by0, sx + bx0
        dxs, dys = sx - c[0], sy - c[1]
        ssc = np.abs(dxs * v[0] + dys * v[1]) / (h / 2 + mc) + 0.3 * np.abs(dxs * u[0] + dys * u[1]) / (L / 2 + ma)
        out_words.append(dict(i=i, w=w, c=c, u=u, v=v, L=L, h=h, ang=ang, T=np.flatnonzero(T), touches=touches, full=full_ids,
                              split=(sy, sx, ssc),
                              ma=ma, mc=mc))
    # a glyph piece claimed whole by two words belongs, in the word list, to the one whose box centre it is nearer
    # (in box-size units, distance across + 0.3 x distance along); the mask is not affected
    claims = {}
    for k, ow in enumerate(out_words):
        for cid_ in ow['full']: claims.setdefault(cid_, []).append(k)
    for cid_, ks in claims.items():
        if len(ks) < 2: continue
        ys, xs = np.nonzero(lab[objs[cid_ - 1]] == cid_)
        mx, my = xs.mean() + objs[cid_ - 1][1].start, ys.mean() + objs[cid_ - 1][0].start
        sc = []
        for k in ks:
            ow = out_words[k]; dx, dy = mx - ow['c'][0], my - ow['c'][1]
            a = abs(dx * ow['u'][0] + dy * ow['u'][1]) / (ow['L'] / 2 + ow['ma'])
            b = abs(dx * ow['v'][0] + dy * ow['v'][1]) / (ow['h'] / 2 + ow['mc'])
            sc.append(b + 0.3 * a)                   # across counts most: a glyph at a word's end is normal
        best = ks[int(np.argmin(sc))]
        for k in ks:
            if k != best: out_words[k]['T'] = out_words[k]['T'][lab.flat[out_words[k]['T']] != cid_]
    # a pixel split off a line and claimed by two words goes to the nearer one, the same way
    best = np.full(ink.shape, np.inf, np.float32); bown = np.full(ink.shape, -1, np.int32)
    for k, ow in enumerate(out_words):
        sy, sx, ssc = ow['split']
        better = ssc < best[sy, sx]
        best[sy[better], sx[better]] = ssc[better]; bown[sy[better], sx[better]] = k
    for k, ow in enumerate(out_words):
        sy, sx, ssc = ow['split']
        lose = bown[sy, sx] != k
        if lose.any(): ow['T'] = np.setdiff1d(ow['T'], np.ravel_multi_index((sy[lose], sx[lose]), ink.shape))
    # hand fixes, in file order
    for o in ops:
        if 'box' in o:
            x0, y0, x1, y1 = o['box']; m = np.zeros(ink.shape, bool)
            m[max(0, y0 - oy):max(0, y1 - oy), max(0, x0 - ox):max(0, x1 - ox)] = True
        else:
            m = strip_mask(ink.shape, ox, oy, o['seg'], o['w'])
        m &= ink
        if o['op'] in ('NOT', 'NOTS'): text &= ~m; care &= ~m
        elif o['op'] in ('TEXT', 'TEXTS'): text |= m; care &= ~m
        elif o['op'] == 'CARE': care |= m; text &= ~m
        elif o['op'] == 'CARES': care |= (m & text); text &= ~m
    care &= ~text
    # text pixels that no word lists (made text by a TEXT fix) go, in the word list, to the word whose grown box
    # holds them, the nearest one by the same score
    listed = np.zeros(ink.shape, bool)
    for ow in out_words: listed.flat[ow['T']] = True
    ys, xs = np.nonzero(text & ~listed)
    if len(xs):
        best = np.full(len(xs), np.inf); who = np.full(len(xs), -1)
        for k, ow in enumerate(out_words):
            dx, dy = xs - ow['c'][0], ys - ow['c'][1]
            a = np.abs(dx * ow['u'][0] + dy * ow['u'][1]) / (ow['L'] / 2 + ow['ma'])
            b = np.abs(dx * ow['v'][0] + dy * ow['v'][1]) / (ow['h'] / 2 + ow['mc'])
            sc = b + 0.3 * a; ok = (a <= 1) & (b <= 1) & (sc < best)
            best[ok] = sc[ok]; who[ok] = k
        for k, ow in enumerate(out_words):
            sel = who == k
            if sel.any(): ow['T'] = np.union1d(ow['T'], np.ravel_multi_index((ys[sel], xs[sel]), ink.shape))
    mask = np.zeros(ink.shape, np.uint8); mask[ink] = 1; mask[text] = 2; mask[care & ink] = 3
    wx0, wy0 = X0 - ox, Y0 - oy
    crop_mask = mask[wy0:wy0 + (Y1 - Y0), wx0:wx0 + (X1 - X0)]
    os.makedirs(OUT, exist_ok=True)
    cv2.imwrite(os.path.join(OUT, f'{cid}_mask.png'), crop_mask)
    # words
    res = []
    wown = np.full(ink.shape, -1, np.int16)              # debug: which word each text pixel is listed under
    for ow in out_words:
        wown.flat[ow['T']] = ow['i']
        w = ow['w']; T = np.zeros(ink.shape, bool); T.flat[ow['T']] = True; T &= text   # after the hand fixes
        ys, xs = np.nonzero(T)
        u, v, c = ow['u'], ow['v'], ow['c']
        if len(xs):
            al = (xs - c[0]) * u[0] + (ys - c[1]) * u[1]; ac = (xs - c[0]) * v[0] + (ys - c[1]) * v[1]
            a0, a1, c0, c1 = al.min() - 0.5, al.max() + 0.5, ac.min() - 0.5, ac.max() + 0.5
            cc = c + u * (a0 + a1) / 2 + v * (c0 + c1) / 2; L, h = a1 - a0, c1 - c0; snapped = 'nosnap' not in w['flags']
            if not snapped: cc, L, h = c, ow['L'], ow['h']
        else:
            cc, L, h, snapped = c, ow['L'], ow['h'], False
        P = poly_of(cc, u, v, L, h) + np.array([ox, oy])
        inwin = T[wy0:wy0 + (Y1 - Y0), wx0:wx0 + (X1 - X0)]
        res.append(dict(id=f'{cid}-{ow["i"] + 1:03d}', reading=w['reading'], kind=w['kind'], flags=w['flags'],
                        angle=round(ow['ang'], 1), height=round(float(h), 1), length=round(float(L), 1),
                        poly=[[round(float(a), 1), round(float(b), 1)] for a, b in P],
                        aabb=[int(np.floor(P[:, 0].min())), int(np.floor(P[:, 1].min())), int(np.ceil(P[:, 0].max())),
                              int(np.ceil(P[:, 1].max()))],
                        touches_line=bool(ow['touches']), text_px=int(inwin.sum()), annot_line=w['line'],
                        snapped=bool(snapped)))
    np.save(os.path.join(WORK, f'{cid}_wordowner.npy'), wown[wy0:wy0 + (Y1 - Y0), wx0:wx0 + (X1 - X0)])
    counts = {str(k): int((crop_mask == k).sum()) for k in range(4)}
    doc = dict(crop=cid, plate=p, win=cr['win'], why=cr['why'], scale_ft=cr['scale_ft'], n_words=len(res),
               mask=f'{cid}_mask.png', mask_values={'0': 'paper', '1': 'non-text ink', '2': 'text ink',
                                                    '3': "don't care"},
               counts=counts, boxes=[{k: v for k, v in o.items()} for o in ops], words=res)
    jdump(doc, os.path.join(OUT, f'{cid}_words.json'))
    print(cid, 'words', len(res), 'counts', counts, 'empty words', [r['annot_line'] for r in res if r['text_px'] == 0])
    return img, ink, mask, (ox, oy), res, lab, sizes


def check_tiles(cid, img, ink, mask, org, res, lab, sizes, tw, th, s, ctx=20):
    cr = CROPS[cid]; X0, Y0, X1, Y1 = cr['win']; ox, oy = org
    base = (0.35 * img.astype(np.float32) + 0.65 * 255).astype(np.uint8)
    col = base.copy()
    col[mask == 1] = (110, 110, 110); col[mask == 2] = (0, 0, 230); col[mask == 3] = (0, 210, 255)
    # suspects: compact non-text ink pieces of glyph size
    objs = ndi.find_objects(lab)
    for k, sl in enumerate(objs, 1):
        if sl is None: continue
        hgt, wid = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
        if sizes[k] < 6 or max(hgt, wid) > 60: continue
        m = (lab[sl] == k)
        if (mask[sl][m] == 1).mean() > 0.8:
            sub = col[sl]; sub[m] = (230, 200, 0)
    for r, ty in enumerate(range(Y0, Y1, th)):
        for cc, tx in enumerate(range(X0, X1, tw)):
            ex, ey = min(tx + tw, X1), min(ty + th, Y1)
            a0, b0, a1, b1 = tx - ctx - ox, ty - ctx - oy, ex + ctx - ox, ey + ctx - oy
            t = cv2.resize(col[b0:b1, a0:a1], None, fx=s, fy=s, interpolation=cv2.INTER_NEAREST)
            # window frame
            fx0, fy0 = int((X0 - (tx - ctx)) * s), int((Y0 - (ty - ctx)) * s)
            fx1, fy1 = int((X1 - (tx - ctx)) * s), int((Y1 - (ty - ctx)) * s)
            cv2.rectangle(t, (fx0, fy0), (fx1, fy1), (0, 160, 0), 1)
            for rw in res:
                P = (np.array(rw['poly']) - np.array([tx - ctx, ty - ctx])) * s
                if P[:, 0].max() < 0 or P[:, 1].max() < 0 or P[:, 0].min() > t.shape[1] or P[:, 1].min() > t.shape[0]:
                    continue
                cv2.polylines(t, [np.round(P).astype(np.int32)], True, (200, 0, 200), 1)
                cv2.putText(t, str(rw['annot_line']), (int(P[0, 0]), int(P[0, 1]) - 2), cv2.FONT_HERSHEY_SIMPLEX,
                            0.32, (150, 0, 150), 1)
            for gx in range(((tx - ctx) // 50 + 1) * 50, ex + ctx, 50):
                X = int((gx - (tx - ctx)) * s)
                cv2.putText(t, str(gx), (X + 2, 10), cv2.FONT_HERSHEY_SIMPLEX, 0.33, (200, 0, 0), 1)
                for Y in range(0, 14, 2): t[Y, X] = (200, 0, 0)
            for gy in range(((ty - ctx) // 50 + 1) * 50, ey + ctx, 50):
                Y = int((gy - (ty - ctx)) * s)
                cv2.putText(t, str(gy), (1, Y - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.33, (200, 0, 0), 1)
                for X in range(0, 14, 2): t[Y, X] = (200, 0, 0)
            cv2.imwrite(os.path.join(WORK, f'{cid}_check_{r}{cc}.jpg'), t, [cv2.IMWRITE_JPEG_QUALITY, 92])


def main():
    cid = sys.argv[1]
    out = build(cid)
    if '--check' in sys.argv:
        i = sys.argv.index('--check')
        tw, th, s = (int(sys.argv[i + 1]), int(sys.argv[i + 2]), float(sys.argv[i + 3])) if len(sys.argv) > i + 3 \
            else (375, 250, 2.0)
        check_tiles(cid, *out, tw, th, s)


if __name__ == '__main__':
    main()
