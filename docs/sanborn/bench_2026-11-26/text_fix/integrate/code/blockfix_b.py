"""blockfix (fix_block_b, 26 Nov 2026): find and READ the big block numbers on a Sanborn 1922 plate by recognising their
figures, then give each recognised figure's ink to text in finder3's hand-off codes. A post-step after finder3.

    cd data/sanborn
    python -B bench_2026-11-26/text_fix/fix_block_b/code/blockfix.py N --in MASK_DIR --out OUT_DIR [--model M.npz]
           [--tmpl T.npz] [--opt k=v,k=v] [--pic] [--debug]
    from python: new_codes = blockfix.apply(N, codes, gray=None, scale_ft=None, **opts)

Reads MASK_DIR/N_text.png (finder3's codes: 0 paper, 1 line ink, 2 text sure, 3 text by context, 4 shared ink, 5 other
ink; the scan's ink on its paper mask is codes > 0, finder2's own ink rule, so the scan itself is only read for --pic)
and scale_table.json (recorded only). Reads no truth. Writes OUT_DIR/N_text.png (codes 0-5), OUT_DIR/N_text.json
(counts, timings, every change listed by number: reading, box, px made text, px made shared, from which codes, the line
cores kept) and OUT_DIR/N_blocks.json (the readings). Refuses the sealed plates. Runs on the system python (numpy, cv2;
finder2.heavy_bars is imported read-only from text_v1/code). About 10-65 s a plate.

How (sizes in full-size scan px, about 300 dpi; block numbers are upright, 44-75 px tall, strokes 6-9 px):
  1. THICK INK K = the ink opened with a 5 px disk: block-number strokes stay; thin lines, ticks, thin dashes and small
     text go. A thin line crossing a figure costs the figure nothing in K (occlusion allowed).
  2. PROPOSE with digit models: one 0-1 map per figure 0-9, the mean of 360 real block-number figures (of 401 cut) from the 12
     dev plates with dev_block's survey lists, never inside a dev truth window or H1-H4 (models/tmpl_real_all.npz;
     scripts/extract_digits.py, build_templates.py). Each map is matched to K by normalised correlation over the
     figure's box grown by mx, my (thick ink missing from the strokes and thick ink in the counters or round the figure
     both cost), at half size for 7 heights; peaks of det or more are refined at full size (3 heights, +-4 px) and
     thinned out (nms1). Every figure-sized piece of K is a proposal too (blob_h), for shapes the mean maps fit badly.
  3. RECOGNISE: a small net (numpy MLP 940 -> 128 -> 11, models/cls_all.npz; scripts/train_cls.py) reads a window
     1.3 h x 1.0 h round each proposal (thick ink 26 x 22 and ink 13 x 11) and a 3 h context (thick ink 15 x 15,
     averaged with its mirror image, so it sees letters in a row but not on which side a neighbour figure stands) at 3
     sizes, and gives P(0) .. P(9) and P(none). Fitted on the real figures (and 164 more placed by fitting the known
     reading where figures are crossed or joined: scripts/fit_digits.py), shifted, scaled and crossed by drawn thin
     lines; on 52,000 proposals far from every surveyed block number (letters, walls, symbols, sheet numbers); and on
     windows half off a real figure. A proposal is kept when P(none) <= none; the models of its best and runner-up
     reading are placed on the ink, the window is read again where each sits, and the surer one is kept (nms2).
  4. NUMBERS: figures side by side (height +-20%, same row, gap -0.1 to 0.5 h) chain into a number. A NUMBER MODEL
     (logistic, models/num_all.npz; scripts/train_num.py) gives P(block number) from 18 numbers that describe the chain
     (figure scores, size and fill, thick ink round it, letter-sized neighbours, finder3's codes under it). Kept when
     P >= pnum (0.6) and: 1-3 figures; every figure's model score s >= acc; no figure on a streetcar dash
     (finder2.heavy_bars); strokes not heavier than sw_max (wall-corner symbols, sheet numbers); a lone 1 passes the
     lone-1 tests (P(1) >= p1, s >= acc1, nothing thick round it, finder3 did not call it line ink, no line ink touching
     it, no bar like it on its axis); a number of 1s only is not beside a thick glyph (an H), not called line ink by
     finder3 (a double line, bars_line) and not carried on by line ink above and below (bar_run).
     Chains with pnum_list <= P < pnum are LISTED as unsure readings; their ink is not changed.
  5. INK OF A FIGURE: the thick ink under the model's strokes, grown through ink that stays inside the model's outline
     (map >= fat_thr, + 1 px), at most grow px. LINE CORES: line pieces found by a Hough transform in the ink round the
     figure (outside it) that run into it (within reach_one px, or line_reach px when the line has pieces on both sides
     of the figure); pieces on one line are joined, the line is fitted to all its outside ink, its width and centre are
     measured from the ink across it, and it is carried through the figure's box at that width + core_pad.
  6. CODES: figure ink that finder3 called 1, 4 or 5 becomes 2 (text sure). Within shared_r px of a line core, other
     ink (5) becomes 4 (shared) and line ink (1) stays 1; on a line core every pixel keeps finder3's code: line ink
     through or along a figure stays line ink. Text already found (2, 3) is never changed. Nothing outside a kept
     figure's outline is changed. No truth, no rail or line file is read, so rail ticks and dashes are protected only by
     the rules above (thin ink is not in K; streetcar dashes refused; a figure's ink stays inside its model's outline).
  7. READINGS (N_blocks.json, per number): reading (figures left to right; a fraction such as 1/2 is not read), box,
     score (mean P(figure)), pnum, unsure, each figure's P and runner-up, the chain's numbers (feat), and FLAGS from
     checks by code: more than 3 figures; a reading seen twice or more on the plate (block numbers are mostly unique);
     far from its 5 nearest neighbours' numbers (blocks are numbered in runs: none within 10); a figure whose runner-up
     reading is close; unsure. Also the chains refused, with why_not.
Settings (P below): pnum by sweeps on one dev fold scored on the other (scripts/sweep.py; both folds chose 0.6); core_pad
2 (the folds chose 1 and 0 by F1; 2 was taken for less line ink called text on Ben's plate 5); pnum_list 0.45 for a
cleaner list; the rest set while looking at dev crops of both folds. Numbers: fix_block_b/scores/summary.json.
"""
import json, os, sys, time
sys.dont_write_bytecode = True
import numpy as np, cv2

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
MOD = os.path.normpath(os.path.join(HERE, '..', 'models'))
DEF_TMPL = os.path.join(MOD, 'tmpl_real_all.npz')
DEF_MODEL = os.path.join(MOD, 'cls_all.npz')
F2 = os.path.normpath(os.path.join(HERE, '..', '..', '..', '..', 'bench_2026-11-25', 'text_v1', 'code'))
SEALED = {'6', '9', '52', '56', '58', '63', '35', '38', '41', '66', '71', '76', '84', '88', '46', '92'}
P = dict(heights=(44, 48, 52, 57, 62, 68, 74), k_open=5, fg_thr=0.5, bg_thr=0.15, mx=0.08, my=0.10,
         det=0.45, peak=5, refine_dh=(0.93, 1.0, 1.075), refine_xy=4, nms1=0.5,
         none=0.5, acc=0.45, p1=0.9, acc1=0.6, ring1=0.35, nms2=0.3,
         chain_dh=0.20, chain_gap=(-0.10, 0.50), chain_ov=0.70, num_model=os.path.join(MOD, 'num_all.npz'), pnum=0.6, pnum_list=0.45, iso_r=1.0, iso_size=(0.4, 1.4), iso_max=99, nb=False, nb_zone=0.9, nb_h=(0.45, 1.4), nb_w=1.3, max_figs=3, bar_run=0.6, bars_line=0.9, sw_max=13.0,
         blob_h=(34, 85), cls_scales=(0.9, 1.0, 1.1), grow=6, fat_thr=0.15, core_thr=0.40, hough=(25, 30, 3), reach_one=8, line_reach=25, core_pad=2.0, line_w=(2, 7), shared_r=2, heavy=True)
CAN, H0 = 72, 52
WIN = (1.3, 1.0)            # classifier window: height, width as shares of the figure height (a neighbour figure
                            # barely shows, so the reading cannot lean on where a figure stands in its number)
FK, FI = (26, 22), (13, 11)  # classifier input sizes (h, w) for thick ink and ink
CTX, FC = 3.0, (15, 15)      # context window (3 h square) of thick ink, shrunk to 15 x 15 and averaged with its mirror
                             # image (left = right): letters in a row round it, but not which side a neighbour stands


def load_templates(path):
    z = np.load(path); return {d: (z[f't{d}'].astype(np.float32), float(z[f'a{d}'])) for d in '0123456789' if f't{d}' in z}


class Kern:
    """normalised-correlation kernels per (digit, height, resolution), cached"""
    def __init__(self, T, p): self.T, self.p, self.c = T, p, {}

    def get(self, d, h, f=1.0):
        key = (d, int(h), f)
        if key in self.c: return self.c[key]
        M0, a = self.T[d]; s = h / H0 * f; n = max(8, int(round(CAN * s)))
        M = cv2.resize(M0, (n, n), interpolation=cv2.INTER_AREA)
        hh = h * f; ww = a * h * f; cy = cx = n / 2.0
        mx, my = self.p['mx'] * hh, self.p['my'] * hh
        x0, x1 = int(np.floor(cx - ww / 2 - mx)), int(np.ceil(cx + ww / 2 + mx)); y0, y1 = int(np.floor(cy - hh / 2 - my)), int(np.ceil(cy + hh / 2 + my))
        x0, y0 = max(0, x0), max(0, y0); x1, y1 = min(n, x1), min(n, y1)
        m = M[y0:y1, x0:x1]
        r = dict(w=m.astype(np.float32), F=m >= self.p['fg_thr'], B=m <= self.p['bg_thr'], M=m, kh=m.shape[0], kw=m.shape[1], ox=cx - x0, oy=cy - y0, hh=hh, ww=ww)
        self.c[key] = r; return r


def thick(ink, k):
    return cv2.morphologyEx(ink, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))


def detect(K, KN, p):
    """half-size search, every figure at every height; peaks (cx, cy, digit, h, score) in full-size px"""
    Kh = cv2.resize(K.astype(np.float32), None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)
    Hh, Wh = Kh.shape; best = np.full((Hh, Wh), -1.0, np.float32); arg = np.zeros((Hh, Wh), np.int16)
    combos = [(d, h) for d in sorted(KN.T) for h in p['heights']]
    for ci, (d, h) in enumerate(combos):
        k = KN.get(d, h, 0.5)
        if k['kh'] >= Hh or k['kw'] >= Wh: continue
        R = cv2.matchTemplate(Kh, k['w'], cv2.TM_CCOEFF_NORMED)
        oy, ox = int(round(k['oy'])), int(round(k['ox']))
        sub = best[oy:oy + R.shape[0], ox:ox + R.shape[1]]; a = arg[oy:oy + R.shape[0], ox:ox + R.shape[1]]
        m = R > sub; sub[m] = R[m]; a[m] = ci
    mxf = cv2.dilate(best, np.ones((p['peak'], p['peak']), np.uint8))
    ys, xs = np.nonzero((best >= p['det']) & (best >= mxf))
    return [(2 * x + 1, 2 * y + 1, combos[arg[y, x]][0], combos[arg[y, x]][1], float(best[y, x])) for y, x in zip(ys, xs)]


def score_at(K, KN, d, h, cx, cy, r):
    """best full-size placement of figure d, height h, centre near (cx, cy) within +-r px: (score, kx, ky)"""
    k = KN.get(d, h); H, W = K.shape
    x0 = int(round(cx - k['ox'])) - r; y0 = int(round(cy - k['oy'])) - r
    if x0 < 0 or y0 < 0 or x0 + k['kw'] + 2 * r > W or y0 + k['kh'] + 2 * r > H: return None
    win = K[y0:y0 + k['kh'] + 2 * r, x0:x0 + k['kw'] + 2 * r].astype(np.float32)
    R = cv2.matchTemplate(win, k['w'], cv2.TM_CCOEFF_NORMED); _, s, _, (bx, by) = cv2.minMaxLoc(R)
    return float(s), x0 + bx, y0 + by


def place(K, KN, d, h0, cx, cy, p, dh=None):
    """best placement of figure d over heights h0*dh and +-refine_xy px: dict with s, h, kx, ky, cx, cy, box"""
    best = None
    for f in (dh or p['refine_dh']):
        h = int(round(h0 * f)); r = score_at(K, KN, d, h, cx, cy, p['refine_xy'])
        if r and (best is None or r[0] > best[0]): best = r + (h,)
    if best is None: return None
    s, X, Y, h = best; k = KN.get(d, h); c = (X + k['ox'], Y + k['oy'])
    return dict(d=d, s=s, h=h, kx=int(X), ky=int(Y), cx=float(c[0]), cy=float(c[1]),
                box=[float(c[0] - k['ww'] / 2), float(c[1] - k['hh'] / 2), float(c[0] + k['ww'] / 2), float(c[1] + k['hh'] / 2)])


def nms(items, key, frac):
    items = sorted(items, key=lambda q: -q[key]); keep = []
    for q in items:
        b = q['box']; A = (b[2] - b[0]) * (b[3] - b[1]); ok = True
        for k in keep:
            c = k['box']; iw = min(b[2], c[2]) - max(b[0], c[0]); ih = min(b[3], c[3]) - max(b[1], c[1])
            if iw > 0 and ih > 0 and iw * ih >= frac * min(A, (c[2] - c[0]) * (c[3] - c[1])): ok = False; break
        if ok: keep.append(q)
    return keep


def propose(K, KN, p):
    peaks = detect(K, KN, p); props = []
    for cx, cy, d, h, s0 in peaks:
        q = place(K, KN, d, h, cx, cy, p)
        if q: q['s0'] = s0; props.append(q)
    return nms(props, 's', p['nms1']) + blobs(K, p), len(peaks)


def blobs(K, p):
    """figure-sized pieces of thick ink as proposals too (any figure shape, e.g. an open 4 the models fit badly)"""
    n, lb, st, cen = cv2.connectedComponentsWithStats(K, connectivity=8); out = []
    for i in range(1, n):
        x, y, w, h, a = st[i]
        if p['blob_h'][0] <= h <= p['blob_h'][1] and 6 <= w <= 0.95 * h and a >= 0.08 * h * h:
            out.append(dict(d='blob', s=0.0, h=int(h), cx=float(x + w / 2), cy=float(y + h / 2), box=[float(x), float(y), float(x + w), float(y + h)]))
    return out


def bar_height(K, cx, cy, h):
    """a figure 1's own height: the run of thick ink down its axis through its centre (None if unclear)"""
    H, W = K.shape; x0, x1 = int(round(cx)) - 3, int(round(cx)) + 4; y0, y1 = max(0, int(cy - 0.9 * h)), min(H, int(cy + 0.9 * h))
    if x0 < 0 or x1 > W: return None
    col = K[y0:y1, x0:x1].mean(1) >= 0.5; c = int(round(cy)) - y0
    if c < 0 or c >= len(col) or not col[c]: return None
    a = c
    while a > 0 and (col[a - 1] or (a > 2 and col[a - 3:a - 1].any())): a -= 1
    b = c
    while b < len(col) - 1 and (col[b + 1] or (b < len(col) - 3 and col[b + 2:b + 4].any())): b += 1
    hh = b - a + 1
    if hh < 36 or not (0.6 * h <= hh <= 1.6 * h): return None
    return y0 + (a + b) / 2.0, hh


def features(K, I, cxs, cys, hs):
    """classifier input for windows centred at (cx, cy), figure height h: thick ink 26 x 22 and ink 13 x 11, 0-1"""
    Kf = K if K.dtype == np.float32 else K.astype(np.float32); If = I if I.dtype == np.float32 else I.astype(np.float32); n1, n2 = FK[0] * FK[1], FI[0] * FI[1]
    X = np.zeros((len(cxs), n1 + n2 + FC[0] * FC[1]), np.float32)
    for i, (cx, cy, h) in enumerate(zip(cxs, cys, hs)):
        wh, ww = int(round(WIN[0] * h)), int(round(WIN[1] * h)); c = (float(cx), float(cy))
        a = cv2.getRectSubPix(Kf, (ww, wh), c); b = cv2.getRectSubPix(If, (ww, wh), c); cs = int(round(CTX * h))
        X[i, :n1] = cv2.resize(a, (FK[1], FK[0]), interpolation=cv2.INTER_AREA).ravel()
        X[i, n1:n1 + n2] = cv2.resize(b, (FI[1], FI[0]), interpolation=cv2.INTER_AREA).ravel()
        g = cv2.resize(cv2.getRectSubPix(Kf, (cs, cs), c), (FC[1], FC[0]), interpolation=cv2.INTER_AREA); X[i, n1 + n2:] = ((g + g[:, ::-1]) / 2).ravel()
    return X


def mlp_predict(M, X):
    Z = (X - M['mu']) / M['sd']; H = np.maximum(0, Z @ M['W1'] + M['b1'])
    O = H @ M['W2'] + M['b2']; O -= O.max(1, keepdims=True); E = np.exp(O); return E / E.sum(1, keepdims=True)


def load_model(path):
    z = dict(np.load(path, allow_pickle=True)); z['classes'] = [str(c) for c in z['classes']]; return z


def chains(figs, p):
    """join figures side by side into numbers (left to right)"""
    figs = sorted(figs, key=lambda q: q['box'][0]); n = len(figs); nxt = [-1] * n; prv = [-1] * n
    for i, a in enumerate(figs):
        best = None
        for j in range(i + 1, n):
            b = figs[j]; h = max(a['h'], b['h'])
            if b['box'][0] - a['box'][2] > p['chain_gap'][1] * h: break
            if abs(a['h'] - b['h']) > p['chain_dh'] * h: continue
            ov = min(a['box'][3], b['box'][3]) - max(a['box'][1], b['box'][1])
            if ov < p['chain_ov'] * min(a['h'], b['h']): continue
            g = b['box'][0] - a['box'][2]
            if g < p['chain_gap'][0] * h or prv[j] >= 0: continue
            if best is None or g < best[0]: best = (g, j)
        if best: nxt[i] = best[1]; prv[best[1]] = i
    out = []
    for i in range(n):
        if prv[i] >= 0: continue
        c = [i]
        while nxt[c[-1]] >= 0: c.append(nxt[c[-1]])
        out.append([figs[j] for j in c])
    return out


def nb_glyphs(chain, st, p):
    """thick glyph-like pieces (not the chain's own) in the row just left and right of a chain: a word in big lettering"""
    x0 = min(q['box'][0] for q in chain); x1 = max(q['box'][2] for q in chain)
    y0 = min(q['box'][1] for q in chain); y1 = max(q['box'][3] for q in chain); h = y1 - y0; hits = []
    sel = (st[:, 0] + st[:, 2] >= x0 - p['nb_zone'] * h) & (st[:, 0] <= x1 + p['nb_zone'] * h) & (st[:, 1] + st[:, 3] >= y0) & (st[:, 1] <= y1)
    for i in np.nonzero(sel)[0]:
        if i == 0: continue
        bx, by, bw, bh, a = st[i]
        if x0 - 2 <= bx + bw / 2 <= x1 + 2: continue
        if not (p['nb_h'][0] * h <= bh <= p['nb_h'][1] * h) or bw > p['nb_w'] * h: continue
        if by < y0 - 0.3 * h or by + bh > y1 + 0.3 * h or a < 0.08 * h * h: continue
        hits.append([int(bx), int(by), int(bw), int(bh)])
    return hits


def neighbours(chain, st, p):
    """letter-sized pieces of thick ink round a number, in any direction (not its own figures): a block number stands
    alone in its block; letters of a street or owner name, upright or slanted, stand in a row"""
    x0 = min(q['box'][0] for q in chain); x1 = max(q['box'][2] for q in chain)
    y0 = min(q['box'][1] for q in chain); y1 = max(q['box'][3] for q in chain); h = max(q['h'] for q in chain); r = p['iso_r'] * h
    bx, by, bw, bh, a = st[:, 0], st[:, 1], st[:, 2], st[:, 3], st[:, 4]
    cx, cy = bx + bw / 2, by + bh / 2; big = np.maximum(bw, bh); small = np.minimum(bw, bh)
    sel = (bx + bw >= x0 - r) & (bx <= x1 + r) & (by + bh >= y0 - r) & (by <= y1 + r)
    sel &= ~((cx >= x0 - 3) & (cx <= x1 + 3) & (cy >= y0 - 3) & (cy <= y1 + 3))
    sel &= (big >= p['iso_size'][0] * h) & (big <= p['iso_size'][1] * h) & (small >= 0.12 * h) & (a >= 0.05 * h * h)
    sel[0] = False
    return int(sel.sum())


def text_neighbours(chain, tst, p):
    """letter-sized pieces of finder3's text (codes 2, 3) round a number, any direction, not its own figures"""
    x0 = min(q['box'][0] for q in chain); x1 = max(q['box'][2] for q in chain)
    y0 = min(q['box'][1] for q in chain); y1 = max(q['box'][3] for q in chain); h = max(q['h'] for q in chain); r = p['iso_r'] * h
    bx, by, bw, bh, a = tst[:, 0], tst[:, 1], tst[:, 2], tst[:, 3], tst[:, 4]
    cx, cy = bx + bw / 2, by + bh / 2; big = np.maximum(bw, bh)
    sel = (cx >= x0 - r) & (cx <= x1 + r) & (cy >= y0 - r) & (cy <= y1 + r)
    sel &= ~((bx < x1) & (bx + bw > x0) & (by < y1) & (by + bh > y0))
    sel &= (big >= 0.45 * h) & (big <= 1.5 * h) & (a >= 0.04 * h * h)
    sel[0] = False
    return int(sel.sum())


NUM_FEATS = ('nf', 'pmin', 'pnone', 'smin', 'smean', 'h', 'iso', 'iso_t', 'nb', 'ring', 'vext', 'hext', 'fill', 'comp', 'f3text', 'f3line', 'f3other', 'bgK')


def chain_feats(ch, K, codes, lb, st, tst, KN, p):
    """numbers that describe a chain of figures, for the number model (no truth)"""
    H, W = K.shape; f = dict(nf=len(ch), pmin=min(q['p'] for q in ch), pnone=max(q['pnone'] for q in ch), smin=min(q['s'] for q in ch),
                             smean=float(np.mean([q['s'] for q in ch])), h=float(np.mean([q['h'] for q in ch])),
                             iso=neighbours(ch, st, p), iso_t=text_neighbours(ch, tst, p), nb=len(nb_glyphs(ch, st, p)))
    x0 = min(q['box'][0] for q in ch); x1 = max(q['box'][2] for q in ch); y0 = min(q['box'][1] for q in ch); y1 = max(q['box'][3] for q in ch); h = f['h']
    r = 0.6 * h; X0, Y0, X1, Y1 = int(max(0, x0 - r)), int(max(0, y0 - r)), int(min(W, x1 + r)), int(min(H, y1 + r))
    tot = K[Y0:Y1, X0:X1].sum(); inn = K[int(max(0, y0)):int(y1), int(max(0, x0)):int(x1)].sum()
    f['ring'] = float((tot - inn) / max(1, (X1 - X0) * (Y1 - Y0) - (x1 - x0) * (y1 - y0)))
    ve, he, fi, co, ft, fl, fo, bk = [], [], [], [], [], [], [], []
    for q in ch:
        k = KN.get(q['d'], q['h']); X, Y = q['kx'], q['ky']; win = K[Y:Y + k['kh'], X:X + k['kw']] > 0; c = codes[Y:Y + k['kh'], X:X + k['kw']]
        bx0, bx1 = int(max(0, q['box'][0])), int(min(W, q['box'][2]))
        rows = np.nonzero(K[int(max(0, q['box'][1] - 0.3 * q['h'])):int(min(H, q['box'][3] + 0.3 * q['h'])), bx0:bx1].any(1))[0]
        ve.append((rows.max() - rows.min() + 1) / q['h'] if len(rows) else 0.0)
        cols = np.nonzero(win.any(0))[0]; he.append((cols.max() - cols.min() + 1) / max(1.0, k['ww']) if len(cols) else 0.0)
        bm = np.zeros(win.shape, bool); oy, ox = int(k['oy'] - k['hh'] / 2), int(k['ox'] - k['ww'] / 2)
        bm[max(0, oy):oy + int(k['hh']), max(0, ox):ox + int(k['ww'])] = True; fi.append(float(win[bm].mean()) if bm.any() else 0.0)
        lw = lb[Y:Y + k['kh'], X:X + k['kw']]; ids = np.unique(lw[win & k['F']]); ids = ids[ids > 0]
        co.append(float(np.isin(lw, ids).sum() / max(1, st[ids, 4].sum())) if len(ids) else 0.0)   # share of its thick pieces inside it
        ink = c > 0; F = k['F'] & ink; n_ = max(1, F.sum())
        ft.append(float(np.isin(c[F], (2, 3)).sum() / n_)); fl.append(float((c[F] == 1).sum() / n_)); fo.append(float((c[F] == 5).sum() / n_))
        bk.append(float(win[k['B']].mean()) if k['B'].any() else 0.0)
    f.update(vext=float(min(ve)), hext=float(min(he)), fill=float(max(fi)), comp=float(min(co)), f3text=float(np.mean(ft)), f3line=float(np.mean(fl)), f3other=float(np.mean(fo)), bgK=float(max(bk)))
    return f


def num_predict(Mn, f):
    x = np.array([f[k] for k in Mn['feats']], np.float32); z = (x - Mn['mu']) / Mn['sd']
    if 'W1' in Mn: hdn = np.maximum(0, z @ Mn['W1'] + Mn['b1']); o = float(hdn @ Mn['w'] + Mn['b'])
    else: o = float(z @ Mn['w'] + Mn['b'])
    return 1.0 / (1.0 + np.exp(-o))


def bar_on_line(q, codes, p):
    """a figure 1 that is a piece of a longer line: finder3's line ink (1) carries on along its axis both above and below
    it (on more than bar_run of the rows within half its height of either end). Asked only of numbers made of 1s alone"""
    H, W = codes.shape; h = q['h']; cx = int(round(q['cx'])); y0, y1 = int(q['box'][1]), int(q['box'][3]); r = int(0.5 * h)
    if cx - 2 < 0 or cx + 3 > W: return False
    col = (codes[:, cx - 2:cx + 3] == 1).any(1)
    up = col[max(0, y0 - r):max(0, y0 - 2)]; dn = col[min(H, y1 + 2):min(H, y1 + r)]
    return bool(len(up) and up.mean() > p['bar_run'] and len(dn) and dn.mean() > p['bar_run'])


def stroke_width(q, K, KN):
    """how heavy the thick ink under the figure is: 2 x the 95th percentile of the distance to paper (measured on the
    thick ink round it, not cut to the model) where the model has strokes. Block-number strokes give 6-12 px; the
    thick L of a wall-corner symbol or a sheet number more"""
    k = KN.get(q['d'], q['h']); H, W = K.shape; g = 20
    X0, Y0, X1, Y1 = max(0, q['kx'] - g), max(0, q['ky'] - g), min(W, q['kx'] + k['kw'] + g), min(H, q['ky'] + k['kh'] + g)
    kk = (K[Y0:Y1, X0:X1] > 0).astype(np.uint8)
    dt = cv2.distanceTransform(np.pad(kk, 1), cv2.DIST_L2, 5)[1:-1, 1:-1]
    F = np.zeros(kk.shape, bool); F[q['ky'] - Y0:q['ky'] - Y0 + k['kh'], q['kx'] - X0:q['kx'] - X0 + k['kw']] = k['F']
    m = F & (kk > 0)
    return float(2 * np.percentile(dt[m], 95)) if m.any() else 0.0


def lone_one(q, K, codes, KN, p, st):
    """extra tests for a number that is a single figure 1 (None = passes, else why not)"""
    k = KN.get(q['d'], q['h']); X, Y = q['kx'], q['ky']; H, W = K.shape; h = q['h']
    if q['p'] < p['p1'] or q['s'] < p['acc1']: return 'lone 1: score'
    r = int(0.5 * h); x0, y0, x1, y1 = max(0, X - r), max(0, Y - r), min(W, X + k['kw'] + r), min(H, Y + k['kh'] + r)
    ring = K[y0:y1, x0:x1].copy(); ring[Y - y0:Y - y0 + k['kh'], X - x0:X - x0 + k['kw']] = 0
    if ring.sum() > p['ring1'] * k['F'].sum(): return 'lone 1: thick ink round it'
    g = codes[Y:Y + k['kh'], X:X + k['kw']]
    if (g[k['F']] == 1).mean() > 0.2: return 'lone 1: finder3 line ink'
    sub = codes[max(0, Y - 3):Y + k['kh'] + 3, max(0, X - 3):X + k['kw'] + 3]
    if (sub == 1).sum() > 4: return 'lone 1: line ink touches it'
    dy = np.abs(st[:, 1] + st[:, 3] / 2 - q['cy'])
    sel = (np.abs(st[:, 0] + st[:, 2] / 2 - q['cx']) < 0.3 * h) & (np.abs(st[:, 3] - h) < 0.3 * h) & (dy > 0.8 * h) & (dy < 3 * h)
    if sel[1:].any(): return 'lone 1: bar row'
    return None


def figure_ink(q, K, I, KN, p):
    """the figure's ink (bool, kernel window) and the window's corner"""
    k = KN.get(q['d'], q['h']); X, Y = q['kx'], q['ky']; M = k['M']
    kk = K[Y:Y + k['kh'], X:X + k['kw']] > 0; ii = I[Y:Y + k['kh'], X:X + k['kw']] > 0
    fat = cv2.dilate((M >= p['fat_thr']).astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
    g = kk & (M >= p['core_thr']); lim = ii & fat
    for _ in range(p['grow']):
        g2 = (cv2.dilate(g.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0) & lim
        if (g2 == g).all(): break
        g = g2
    return g, X, Y


def line_core(G, gx, gy, I, p, pad=60):
    """straight lines in the ink round a figure (outside it) that run into it, carried through it at their own width.
    Line pieces are found with a Hough transform on the ink outside the figure; pieces on one line (same direction
    +-3 deg, offset +-3 px) are joined, the line is fitted by least squares to all the outside ink along them (both sides
    of the figure when it crosses), and drawn across the figure's box at its measured width (2 x the 90th percentile of
    the ink's distance from the fitted line, + 1 px)"""
    H, W = I.shape; h, w = G.shape
    X0, Y0, X1, Y1 = max(0, gx - pad), max(0, gy - pad), min(W, gx + w + pad), min(H, gy + h + pad)
    win = I[Y0:Y1, X0:X1]; Gw = np.zeros(win.shape, np.uint8); Gw[gy - Y0:gy - Y0 + h, gx - X0:gx - X0 + w] = G
    out = (win > 0) & ~(cv2.dilate(Gw, np.ones((3, 3), np.uint8)) > 0)
    th, ml, gap = p['hough']; used = []; Lc = np.zeros(win.shape, np.uint8)
    segs = cv2.HoughLinesP(out.astype(np.uint8) * 255, 1, np.pi / 360, th, minLineLength=ml, maxLineGap=gap)
    gys, gxs = np.nonzero(Gw)
    if segs is None or not len(gxs): return np.zeros(win.shape, bool), (X0, Y0), used
    gpts = np.c_[gxs, gys].astype(np.float32); oy, ox = np.nonzero(out); ops = np.c_[ox, oy].astype(np.float32)
    lines = []; gc = gpts.mean(0)
    for x1, y1, x2, y2 in segs[:, 0]:
        a = np.array([x1, y1], np.float32); b = np.array([x2, y2], np.float32); L = float(np.linalg.norm(b - a))
        if L < 1: continue
        u = (b - a) / L; nrm = np.array([-u[1], u[0]], np.float32); dg = np.abs((gpts - a) @ nrm)
        if (dg <= 2.0).sum() < 3: continue                                  # its line does not pass through the figure
        de = float(min(np.min(np.hypot(*(gpts - a).T)), np.min(np.hypot(*(gpts - b).T))))
        t = (gpts - a) @ u; onl = dg <= 2.0
        if ((t[onl] >= -2) & (t[onl] <= L + 2)).any(): de = 0.0             # it runs over the figure itself
        ang = np.arctan2(u[1], u[0]) % np.pi; c = float(a @ nrm)
        side = float(np.sign(((a + b) / 2 - gc) @ np.array([np.cos(ang), np.sin(ang)])))   # which side of the figure
        for ln in lines:                                                    # same line as one found before?
            da = abs(((ang - ln['ang']) + np.pi / 2) % np.pi - np.pi / 2)
            if da <= np.radians(3) and abs(float(a @ ln['nrm']) - ln['c']) <= 3 and abs(float(b @ ln['nrm']) - ln['c']) <= 3:
                ln['segs'].append((a, b)); ln['de'] = min(ln['de'], de); ln['sides'].add(side); break
        else: lines.append(dict(ang=ang, nrm=nrm, c=c, u=u, segs=[(a, b)], de=de, sides={side}))
    # a line counts when it reaches the figure (reach_one px), or, when it has pieces on both sides of the figure (it
    # crosses it), when it comes within line_reach px of it (lettering or a joined figure may hide the last bit)
    lines = [ln for ln in lines if ln['de'] <= p['reach_one'] or (len(ln['sides']) > 1 and ln['de'] <= p['line_reach'])]
    for ln in lines:
        # least-squares fit to the outside ink within 2.5 px of any of its pieces, within the pieces' span
        sel = np.zeros(len(ops), bool)
        for a, b in ln['segs']:
            L = float(np.linalg.norm(b - a)); u = (b - a) / L; nrm = np.array([-u[1], u[0]], np.float32)
            t = (ops - a) @ u; d = np.abs((ops - a) @ nrm); sel |= (t >= -2) & (t <= L + 2) & (d <= 2.5)
        Q = ops[sel]
        if len(Q) < 10: continue
        m = Q.mean(0); _, _, vt = np.linalg.svd(Q - m, full_matrices=False); u = vt[0]; nrm = np.array([-u[1], u[0]])
        # its width and centre from the ink across it: offsets -7..7 px from the fitted axis that hold ink along at least
        # 40% of the pieces' length (ticks and lettering touching it are too short to count), the run round the fullest
        t_all = (ops - m) @ u; d_all = (ops - m) @ nrm
        tq = (Q - m) @ u; ta, tb = tq.min(), tq.max(); sel2 = (t_all >= ta) & (t_all <= tb) & (np.abs(d_all) <= 7.5)
        occ = np.bincount(np.round(d_all[sel2]).astype(int) + 7, minlength=15)[:15] / max(1.0, tb - ta)
        c0 = int(np.argmax(occ)); lo = hi = c0
        while lo > 0 and occ[lo - 1] >= 0.4: lo -= 1
        while hi < 14 and occ[hi + 1] >= 0.4: hi += 1
        wd = float(np.clip(hi - lo + 1, p['line_w'][0], p['line_w'][1])); m = m + nrm * ((lo + hi) / 2.0 - 7)
        e0 = m - u * 400; e1 = m + u * 400
        cv2.line(Lc, tuple(np.round(e0).astype(int).tolist()), tuple(np.round(e1).astype(int).tolist()), 1, max(1, int(round(wd + p['core_pad']))))
        used.append(dict(segs=[[int(a[0] + X0), int(a[1] + Y0), int(b[0] + X0), int(b[1] + Y0)] for a, b in ln['segs']], width=round(wd, 2),
                         angle=round(float(np.degrees(np.arctan2(u[1], u[0]) % np.pi)), 1), px=int(len(Q))))
    near = np.zeros(win.shape, bool); near[max(0, gy - Y0 - 3):gy - Y0 + h + 3, max(0, gx - X0 - 3):gx - X0 + w + 3] = True
    return (Lc > 0) & (win > 0) & near, (X0, Y0), used


def plausibility(nums):
    """checks by code on the readings"""
    from collections import Counter
    vals = []
    for n in nums:
        try: vals.append(int(n['reading']))
        except ValueError: vals.append(None)
    C = np.array([[(n['box'][0] + n['box'][2]) / 2, (n['box'][1] + n['box'][3]) / 2] for n in nums]) if nums else np.zeros((0, 2))
    cnt = Counter(n['reading'] for n in nums)
    for i, n in enumerate(nums):
        f = []
        if len(n['reading']) > 3: f.append('more than 3 figures')
        if cnt[n['reading']] > 1: f.append(f"reading seen {cnt[n['reading']]} times on the plate")
        if vals[i] is not None and len(nums) >= 4:
            d = np.hypot(*(C - C[i]).T); o = [j for j in np.argsort(d)[1:6] if vals[j] is not None]
            if o:
                n['neighbours'] = [nums[j]['reading'] for j in o]
                if np.min(np.abs(np.array([vals[j] for j in o]) - vals[i])) > 10: f.append("far from its neighbours' numbers")
        if min(q['p'] - q['p2'] for q in n['figs']) < 0.3: f.append('a figure close to another reading')
        if n.get('unsure'): f.append(f"unsure: number model {n.get('pnum')} (listed, ink not changed)")
        n['flags'] = f
    return nums


def recognise(codes, p, KN, M, props=None, Mn=None):
    """the figures and numbers on a plate (no code change): returns K, I, numbers, rejected, proposals, figures, counts,
    timings. props: proposals made before (tuning only; else made here)"""
    T = {}; t0 = time.time()
    I = (codes > 0).astype(np.uint8); K = thick(I, p['k_open'])
    if props is None: props, npk = propose(K, KN, p)
    else: npk = -1
    T['propose'] = time.time() - t0
    if props:
        cl = M['classes']; inone = cl.index('none'); dig = [i for i, c in enumerate(cl) if c != 'none']; best = None
        Kf0, If0 = K.astype(np.float32), I.astype(np.float32)
        for f in p['cls_scales']:      # read each proposal at 3 sizes; keep the size where it looks most like a figure
            X = features(Kf0, If0, [q['cx'] for q in props], [q['cy'] for q in props], [q['h'] * f for q in props])
            pr = mlp_predict(M, X)
            if best is None: best = pr.copy(); bf = np.full(len(props), f)
            else: m = pr[:, inone] < best[:, inone]; best[m] = pr[m]; bf[m] = f
        for q, r, f in zip(props, best, bf):
            o = sorted(dig, key=lambda i: -r[i]); q['pnone'] = float(r[inone]); q['cls'] = cl[o[0]]; q['p'] = float(r[o[0]]); q['p2'] = float(r[o[1]]); q['cls2'] = cl[o[1]]; q['hf'] = float(f)
    T['classify'] = time.time() - t0
    figs = []; Kf = K.astype(np.float32); If = I.astype(np.float32)
    for q in props:
        if q['pnone'] > p['none']: continue
        # place the model of the best and the runner-up reading on the ink, read the window again where each sits, and keep
        # the reading that is surest there (a window half off a figure reads as another figure: the right half of 8 as 3)
        best = None
        for c in (q['cls'], q['cls2']):
            h, cy = q['h'] * q.get('hf', 1.0), q['cy']
            if c == '1':
                bh = bar_height(K, q['cx'], q['cy'], h)
                if bh: cy, h = bh
            r = place(K, KN, c, h, q['cx'], cy, p)
            if r is None: continue
            pr = mlp_predict(M, features(Kf, If, [r['cx']] * len(p['cls_scales']), [r['cy']] * len(p['cls_scales']), [r['h'] * f for f in p['cls_scales']]))
            j = int(np.argmin(pr[:, inone])); pv = pr[j]; o = sorted(dig, key=lambda i: -pv[i])
            if cl[o[0]] != c: continue
            r.update(p=float(pv[o[0]]), p2=float(pv[o[1]]), cls2=cl[o[1]], pnone=float(pv[inone]), p0=q['p'])
            if best is None or r['p'] > best['p']: best = r
        if best is not None and best['pnone'] <= p['none']: figs.append(best)
    figs = nms(figs, 'p', p['nms2'])
    n, lb, st, cen = cv2.connectedComponentsWithStats(K, connectivity=8)
    _, _, tst, _ = cv2.connectedComponentsWithStats(np.isin(codes, (2, 3)).astype(np.uint8), connectivity=8)
    heavy = None
    if p['heavy']:
        if F2 not in sys.path: sys.path.insert(0, F2)
        import finder2
        heavy = finder2.heavy_bars(I) > 0
    T['figures'] = time.time() - t0
    nums, rej = [], []
    for ch in chains(figs, p):
        why = None
        if len(ch) > p['max_figs']: why = f'{len(ch)} figures'
        if not why and min(q['s'] for q in ch) < p['acc']: why = 'a figure scores under acc'
        fe = chain_feats(ch, K, codes, lb, st, tst, KN, p); iso, isot = fe['iso'], fe['iso_t']
        pn = num_predict(Mn, fe) if Mn is not None else None
        unsure = False
        if not why and pn is not None and pn < p['pnum']:
            if pn >= p['pnum_list']: unsure = True                 # listed as an unsure reading; its ink is not changed
            else: why = f'number model {pn:.2f}'
        if not why and iso > p['iso_max']: why = f'{iso} letter-sized thick pieces round it (a word)'
        if not why and p['nb'] and fe['nb']: why = f"beside {fe['nb']} thick glyphs (a word)"
        if not why and heavy is not None:
            for q in ch:
                k = KN.get(q['d'], q['h']); sub = heavy[q['ky']:q['ky'] + k['kh'], q['kx']:q['kx'] + k['kw']]
                if (sub & k['F']).sum() > 0.2 * k['F'].sum(): why = 'streetcar dash'; break
        if not why and len(ch) == 1 and ch[0]['d'] == '1': why = lone_one(ch[0], K, codes, KN, p, st)
        if not why and len(ch) > 1 and all(q['d'] == '1' for q in ch) and fe['nb']: why = 'bars beside a thick glyph (an H or a word)'
        if not why and all(q['d'] == '1' for q in ch) and any(bar_on_line(q, codes, p) for q in ch): why = 'a figure 1 that carries on as a line'
        if not why and all(q['d'] == '1' for q in ch) and fe['f3line'] > p['bars_line']: why = 'bars that finder3 calls line ink (a double line)'
        if not why and max(stroke_width(q, K, KN) for q in ch) > p['sw_max']: why = 'strokes too heavy (sheet number or title lettering)'
        box = [min(q['box'][0] for q in ch), min(q['box'][1] for q in ch), max(q['box'][2] for q in ch), max(q['box'][3] for q in ch)]
        rec = dict(reading=''.join(q['d'] for q in ch), box=[round(v, 1) for v in box], score=round(float(np.mean([q['p'] for q in ch])), 3), pnum=None if pn is None else round(pn, 3),
                   feat={k: round(float(v), 4) for k, v in fe.items()},
                   figs=[dict(d=q['d'], p=round(q['p'], 3), p2=round(q['p2'], 3), runner_up=q['cls2'], pnone=round(q['pnone'], 3), s=round(q['s'], 3), h=q['h'],
                              box=[round(v, 1) for v in q['box']], kx=q['kx'], ky=q['ky']) for q in ch])
        if why: rec['why_not'] = why; rej.append(rec)
        else: rec['unsure'] = unsure; nums.append(rec)
    T['numbers'] = time.time() - t0
    return K, I, nums, rej, props, figs, dict(peaks=npk, proposals=len(props), figures=len(figs)), T


def apply(N, codes, gray=None, scale_ft=None, tmpl=DEF_TMPL, model=DEF_MODEL, return_info=False, props=None, **opts):
    """codes: finder3's hand-off codes (uint8, whole plate). gray: not used (the ink is codes > 0, finder2's ink rule).
    Returns the new codes (uint8, codes 0-5); with return_info also (info, numbers, rejected)."""
    if str(N) in SEALED: raise SystemExit(f'plate {N} is sealed')
    p = dict(P, **opts); t0 = time.time()
    KN = Kern(load_templates(tmpl), p); M = load_model(model)
    Mn = None
    if p.get('num_model'):
        Mn = dict(np.load(p['num_model'], allow_pickle=True)); Mn['feats'] = [str(x) for x in Mn['feats']]
    K, I, nums, rej, props, figs, cnt, T = recognise(codes, p, KN, M, props, Mn)
    out = codes.copy(); changes = []
    for nrec in nums:
        if nrec.get('unsure'): continue                            # unsure readings are listed only
        cs = dict(reading=nrec['reading'], box=nrec['box'], to_text=0, to_shared=0, from_codes={'1': 0, '4': 0, '5': 0}, lines=[])
        for f in nrec['figs']:
            G, gx, gy = figure_ink(f, K, I, KN, p)
            Lc, (X0, Y0), used = line_core(G, gx, gy, I, p)
            h, w = G.shape; Lf = Lc[gy - Y0:gy - Y0 + h, gx - X0:gx - X0 + w]
            band = cv2.dilate(Lf.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * p['shared_r'] + 1,) * 2)) > 0
            sub = out[gy:gy + h, gx:gx + w]; src = codes[gy:gy + h, gx:gx + w]
            m_txt = G & ~Lf & ~band & np.isin(src, (1, 4, 5)) & np.isin(sub, (1, 4, 5))
            m_sh = G & ~Lf & band & (src == 5) & (sub == 5)        # line ink (1) is never changed, not even to shared
            for v in (1, 4, 5): cs['from_codes'][str(v)] += int((m_txt & (src == v)).sum())
            sub[m_txt] = 2; sub[m_sh] = 4
            cs['to_text'] += int(m_txt.sum()); cs['to_shared'] += int(m_sh.sum()); cs['lines'] += used
        changes.append(cs)
    T['assign'] = time.time() - t0
    nums = plausibility(nums)
    info = dict(plate=str(N), scale_ft=scale_ft, tmpl=os.path.basename(tmpl), model=os.path.basename(model), params=dict(p), **cnt,
                numbers=len(nums), rejected=len(rej), px_to_text=int(sum(c['to_text'] for c in changes)), px_to_shared=int(sum(c['to_shared'] for c in changes)),
                codes_before={str(v): int((codes == v).sum()) for v in range(6)}, codes_after={str(v): int((out == v).sum()) for v in range(6)},
                seconds={k: round(v, 1) for k, v in T.items()}, changes=changes)
    if p.get('debug'):
        info['proposals_all'] = [{k: (round(v, 4) if isinstance(v, float) else v) for k, v in q.items()} for q in props]
    if return_info: return out, info, nums, rej
    return out


def main():
    a = sys.argv; N = a[1]
    if N in SEALED: raise SystemExit(f'plate {N} is sealed')
    ind = a[a.index('--in') + 1]; od = a[a.index('--out') + 1]
    tmpl = a[a.index('--tmpl') + 1] if '--tmpl' in a else DEF_TMPL
    model = a[a.index('--model') + 1] if '--model' in a else DEF_MODEL
    opts = {}
    if '--debug' in a: opts['debug'] = True
    if '--opt' in a:
        for kv in a[a.index('--opt') + 1].split(','):
            k, v = kv.split('='); opts[k] = (v in ('1', 'True', 'true')) if isinstance(P[k], bool) else type(P[k])(v)
    codes = cv2.imread(os.path.join(ind, f'{N}_text.png'), 0)
    try: ft = int(json.load(open('scale_table.json'))[N]['ft_per_inch'])
    except Exception: ft = None
    out, info, nums, rej = apply(N, codes, None, ft, tmpl=tmpl, model=model, return_info=True, **opts)
    os.makedirs(od, exist_ok=True)
    cv2.imwrite(os.path.join(od, f'{N}_text.png'), out)
    info['in'] = os.path.join(ind, f'{N}_text.png'); info['made'] = time.strftime('%Y-%m-%d %H:%M')
    json.dump(info, open(os.path.join(od, f'{N}_text.json'), 'w', encoding='utf8', newline='\n'), indent=1, default=str)
    json.dump(dict(plate=N, scale_ft=ft, model=info['model'], numbers=nums, rejected=rej), open(os.path.join(od, f'{N}_blocks.json'), 'w', encoding='utf8', newline='\n'), indent=1, default=str)
    print(f"blockfix {N}: {len(nums)} numbers ({len(rej)} rejected), {info['px_to_text']} px to text, {info['px_to_shared']} to shared, {info['seconds']}", flush=True)
    if '--pic' in a:
        im = cv2.imread(f'cufp/22-{N}.jpg'); o = im.copy(); d = (out != codes)
        o[d & (out == 2)] = (0, 0, 255); o[d & (out == 4)] = (0, 200, 230)
        for nm in nums:
            b = [int(v) for v in nm['box']]; cv2.rectangle(o, (b[0] - 4, b[1] - 4), (b[2] + 4, b[3] + 4), (0, 160, 0), 2)
            cv2.putText(o, nm['reading'], (b[0], b[1] - 8), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 120, 0), 2)
        cv2.imwrite(os.path.join(od, f'{N}_blockfix.jpg'), cv2.resize(o, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 85])


if __name__ == '__main__':
    main()
