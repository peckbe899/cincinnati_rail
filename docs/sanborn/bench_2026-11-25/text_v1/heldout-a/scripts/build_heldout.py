"""Build a HELD-OUT text truth crop (H1, H2 on plate 90) from its hand annotation, and its check tiles.
python -B build_heldout.py H1 [H2 ...] [--check]
Reads heldout-a/annot/H#.txt and heldout-a/crops.json; writes H#_mask.png and H#_words.json to text_v1/heldout/
(and a second copy to heldout-a/out/); check tiles to heldout-a/work/.

Made from the scan alone: ink (Lab L < 140 on the paper mask), straight-run peeling and connected components written
here, and word boxes typed by eye. No finder, words, shapes or bin 8 output is read.

Annotation lines (annot/H#.txt, full-plate px, read by eye from the 1.5x reading tiles and 3x zooms):
  x1 y1 x2 y2 h | reading | kind [| flags]
      a word: its centre line from the middle of the first glyph's leading edge to the middle of the last glyph's
      trailing edge, in reading order (angle 0 reads left to right, 90 downwards, -90 upwards), h the glyph height.
  PATH x1 y1 x2 y2 ... xn yn h | reading | kind [| flags]
      a curved word: its centre line as a polyline; each segment is boxed and snapped on its own, the word is their union.
  flags: partial (cut by the crop edge), unsure, run, curved, nosnap, g:NAME (spaced letters of one name);
         peel:NN (build only, not written out) peels straight runs of NN px or more for this word instead of
         max(41, 1.5 h): for a figure drawn over a small building outline whose sides are shorter than 41 px
  EXCL x0 y0 x1 y1 [note]    ink in this box is not text (a stub, a hook, a dash under a word)
  FORCE x0 y0 x1 y1 [note]   ink in this box is text
  CARE x0 y0 x1 y1 [note]    ink in this box is don't care (3)
  CARELINE x1 y1 x2 y2 w [note]  text ink in this strip becomes don't care (a dashed line through glyphs)
  EXCLLINE x1 y1 x2 y2 w [note]  ink in this strip is not text (a dash or stub a word box takes in, clear of the glyphs)
  # comment
Kinds as in the earlier truth: street house lotdim lot block owner bldg story pipe sewer rail adj ditto other.

Rules (the same as the earlier truth T1-T7, so the scores compare):
  - straight runs of at least max(41, 1.5 h) px (any of 72 directions, after a 3x3 closing) are line ink;
  - snap: the typed box is grown by 0.15 h + 4 px along and 0.15 h + 3 px across; the pieces of ink-less-lines (lines
    grown 2 px) lying at least 70% inside it give the tight box, no side trimmed by more than 0.25 h along or 0.2 h across;
  - text = ink in the snapped box (grown 1.5 px) that is not on, or within 2 px of, a straight run reaching more than
    4 px out of the box; line ink within 2 px of that text inside the box is don't care (3): shared glyph-line ink.
Mask: 0 paper, 1 ink not text, 2 text ink, 3 don't care.
Check tiles (work/H#_check_RC.jpg, 1.5x): text red, don't care yellow, other ink grey, text pieces that run on well
outside their word box orange (to look at), word boxes magenta with the annotation line number."""
import sys, os, json, math
import numpy as np, cv2

HERE = os.path.dirname(os.path.abspath(__file__)); HO = os.path.dirname(HERE)          # text_v1/heldout-a (work)
OUT = os.path.join(os.path.dirname(HO), 'heldout')                                         # text_v1/heldout (the crops)
COPY = os.path.join(HO, 'out')                                                             # second copy
ROOT = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn'
CROPS = json.load(open(os.path.join(HO, 'crops.json')))
WORK = os.path.join(HO, 'work'); os.makedirs(WORK, exist_ok=True)
INK_L = 140; PAD = 120
KINDS = {'street', 'house', 'lotdim', 'lot', 'block', 'owner', 'bldg', 'story', 'pipe', 'sewer', 'rail', 'adj', 'ditto', 'other'}
_cache = {}


def plate(p):
    if p not in _cache:
        im = cv2.imread(f'{ROOT}/cufp/22-{p}.jpg'); H, W = im.shape[:2]
        al = np.load(f'{ROOT}/cufp/{p}/png_alpha_s4.npy')
        _cache[p] = (im, cv2.resize(al, (W, H), interpolation=cv2.INTER_NEAREST) > 0)
    return _cache[p]


def window(p, x0, y0, x1, y1):
    im, pap = plate(p); H, W = im.shape[:2]
    x0, y0, x1, y1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
    c = im[y0:y1, x0:x1]; L = cv2.cvtColor(c, cv2.COLOR_BGR2LAB)[..., 0]
    return c, (L < INK_L) & pap[y0:y1, x0:x1], (x0, y0, x1, y1)


def straight_runs(ink, length, nang=72):
    """ink on a straight 1 px run of at least `length` px in any of nang directions (opening with a line kernel),
    after a 3x3 closing that bridges the scan's pinholes; cut back to ink"""
    u = cv2.morphologyEx(ink.astype(np.uint8), cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
    out = np.zeros_like(u); c = length // 2
    for i in range(nang):
        a = math.pi * i / nang; k = np.zeros((length, length), np.uint8)
        d = np.array([math.cos(a), math.sin(a)]) * c
        cv2.line(k, tuple(np.round(c - d).astype(int).tolist()), tuple(np.round(c + d).astype(int).tolist()), 1, 1)
        out |= cv2.morphologyEx(u, cv2.MORPH_OPEN, k)
    return (out > 0) & ink


def in_rect(X, Y, cx, cy, L, h, ang):
    a = math.radians(ang); dx, dy = X - cx, Y - cy
    al = dx * math.cos(a) + dy * math.sin(a); ac = -dx * math.sin(a) + dy * math.cos(a)
    return (np.abs(al) <= L / 2) & (np.abs(ac) <= h / 2), al, ac


def rpoly(cx, cy, L, h, ang):
    a = math.radians(ang); u = np.array([math.cos(a), math.sin(a)]); v = np.array([-math.sin(a), math.cos(a)])
    c = np.array([cx, cy])
    return np.array([c - u * L / 2 - v * h / 2, c + u * L / 2 - v * h / 2, c + u * L / 2 + v * h / 2, c - u * L / 2 + v * h / 2])


def parse(cid):
    words, boxes = [], []
    for k, raw in enumerate(open(os.path.join(HO, 'annot', f'{cid}.txt'), encoding='utf8')):
        s = raw.strip()
        if not s or s.startswith('#'): continue
        f = s.split()
        if f[0] in ('EXCL', 'FORCE', 'CARE'):
            boxes.append(dict(op=f[0], box=[int(v) for v in f[1:5]], note=' '.join(f[5:]), line=k + 1)); continue
        if f[0] in ('CARELINE', 'EXCLLINE'):
            boxes.append(dict(op=f[0], seg=[int(v) for v in f[1:5]], width=int(f[5]), note=' '.join(f[6:]), line=k + 1)); continue
        parts = [q.strip() for q in s.split('|')]
        g = parts[0].split(); path = g[0] == 'PATH'
        v = [float(t) for t in (g[1:] if path else g)]
        if path:
            if len(v) < 5 or len(v) % 2 == 0: raise SystemExit(f'{cid} line {k + 1}: PATH needs x y pairs and h: {s}')
            pts = np.array(v[:-1]).reshape(-1, 2); h = v[-1]
        else:
            if len(v) != 5: raise SystemExit(f'{cid} line {k + 1}: need x1 y1 x2 y2 h: {s}')
            pts = np.array(v[:4]).reshape(2, 2); h = v[4]
        kind = parts[2]
        if kind not in KINDS: raise SystemExit(f'{cid} line {k + 1}: unknown kind {kind}')
        flags = parts[3].split() if len(parts) > 3 else []
        peel = [int(f_[5:]) for f_ in flags if f_.startswith('peel:')]
        flags = [f_ for f_ in flags if not f_.startswith('peel:')]
        if path and 'curved' not in flags: flags.append('curved')
        words.append(dict(pts=pts, h=h, reading=parts[1], kind=kind, flags=flags, line=k + 1, path=path, peel=peel[0] if peel else None))
    return words, boxes


def seg_text(ink, X, Y, x1, y1, x2, y2, h, wx0, wy0, nosnap, notes, tag, peel=None):
    """one straight box: snap it, then its text and shared ink (window-sized bool arrays restricted to a sub-box)"""
    hh, ww = ink.shape
    ang = math.degrees(math.atan2(y2 - y1, x2 - x1)); L = math.hypot(x2 - x1, y2 - y1)
    cx, cy = (x1 + x2) / 2 - wx0, (y1 + y2) / 2 - wy0
    Ll = (int(peel) if peel else int(max(41, round(1.5 * h)))) | 1
    R = int(L / 2 + h + max(Ll, 41) + 10)
    bx0, by0, bx1, by1 = max(0, int(cx - R)), max(0, int(cy - R)), min(ww, int(cx + R)), min(hh, int(cy + R))
    sub = ink[by0:by1, bx0:bx1]; ln = straight_runs(sub, Ll)
    Xs, Ys = X[by0:by1, bx0:bx1], Y[by0:by1, bx0:bx1]
    snapped = False
    if not nosnap:
        ma, mc = 0.15 * h + 4, 0.15 * h + 3
        cand = sub & ~(cv2.dilate(ln.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0)
        n, lb, _, _ = cv2.connectedComponentsWithStats(cand.astype(np.uint8), connectivity=8)
        inw, al, ac = in_rect(Xs, Ys, cx, cy, L + 2 * ma, h + 2 * mc, ang)
        tot = np.bincount(lb.ravel(), minlength=n); ins = np.bincount(lb.ravel(), inw.ravel(), minlength=n)
        ok = (ins >= 0.7 * tot) & (tot >= 3); ok[0] = False
        sel = ok[lb] & inw
        if sel.sum() >= 8:
            a1, c1 = al[sel], ac[sel]
            lo, hi, clo, chi = a1.min(), a1.max(), c1.min(), c1.max()
            sa, sc = 0.25 * h, 0.2 * h
            lo, hi = min(lo, -L / 2 + sa), max(hi, L / 2 - sa); clo, chi = min(clo, -h / 2 + sc), max(chi, h / 2 - sc)
            a = math.radians(ang); u = np.array([math.cos(a), math.sin(a)]); v = np.array([-math.sin(a), math.cos(a)])
            ctr = np.array([cx, cy]) + u * (lo + hi) / 2 + v * (clo + chi) / 2
            cx, cy = ctr; L = hi - lo + 2; h = chi - clo + 2; snapped = True
        else:
            notes.append(f'{tag}: nothing to snap to')
    inw = in_rect(Xs, Ys, cx, cy, L + 3, h + 3, ang)[0]
    n, lb, _, _ = cv2.connectedComponentsWithStats(ln.astype(np.uint8), connectivity=8)
    outside = np.bincount(lb.ravel(), (~in_rect(Xs, Ys, cx, cy, L + 8, h + 8, ang)[0]).ravel(), minlength=n) > 0; outside[0] = False
    lpx = (cv2.dilate(outside[lb].astype(np.uint8), np.ones((5, 5), np.uint8)) > 0) & sub
    t = sub & inw & ~lpx
    ov = lpx & inw & (cv2.dilate(t.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0)
    tl = bool((cv2.dilate(t.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0)[lpx].any())
    return dict(sl=(slice(by0, by1), slice(bx0, bx1)), t=t, ov=ov, cx=cx + wx0, cy=cy + wy0, L=L, h=h, ang=ang,
                snapped=snapped, touches=tl, box=inw)


def build(cid, check=False):
    c = CROPS[cid]; p = c['plate']; X0, Y0, X1, Y1 = c['win']
    img, ink, (wx0, wy0, wx1, wy1) = window(p, X0 - PAD, Y0 - PAD, X1 + PAD, Y1 + PAD)
    hh, ww = ink.shape
    Y, X = np.mgrid[0:hh, 0:ww].astype(np.float32)
    words, boxes = parse(cid)
    text = np.zeros_like(ink); care = np.zeros_like(ink); wbox = np.zeros(ink.shape, np.int32); notes = []
    out = []
    for i, w in enumerate(words):
        pts = w['pts']; segs = []
        for j in range(len(pts) - 1):
            (x1, y1), (x2, y2) = pts[j], pts[j + 1]
            segs.append(seg_text(ink, X, Y, x1, y1, x2, y2, w['h'], wx0, wy0, 'nosnap' in w['flags'] or w['path'], notes,
                                 f"{cid} line {w['line']} {w['reading']!r}", w.get('peel')))
        tpx = 0; allpts = []
        wt = np.zeros_like(ink)
        for s in segs:
            text[s['sl']] |= s['t']; care[s['sl']] |= s['ov']; wt[s['sl']] |= s['t']
            wbox[s['sl']][s['box']] = w['line']
            allpts.append(rpoly(s['cx'], s['cy'], s['L'], s['h'], s['ang']))
        allpts = np.concatenate(allpts)
        if w['path']:
            # the box of a curved word: the rectangle along its chord that holds every segment box
            (x1, y1), (x2, y2) = pts[0], pts[-1]; ang = math.degrees(math.atan2(y2 - y1, x2 - x1)); a = math.radians(ang)
            u = np.array([math.cos(a), math.sin(a)]); v = np.array([-math.sin(a), math.cos(a)])
            pa, pc = allpts @ u, allpts @ v
            ctr = u * (pa.min() + pa.max()) / 2 + v * (pc.min() + pc.max()) / 2
            L, h = pa.max() - pa.min(), pc.max() - pc.min()
            poly = rpoly(ctr[0], ctr[1], L, h, ang); hgt = w['h']
            path = [[round(float(a_), 1), round(float(b_), 1)] for a_, b_ in pts]
        else:
            s = segs[0]; ang, L, h, poly, hgt, path = s['ang'], s['L'], s['h'], allpts, s['h'], None
        d = dict(id=f'{cid}-{i + 1:03d}', reading=w['reading'], kind=w['kind'], flags=w['flags'], angle=round(ang, 1),
                 height=round(float(hgt), 1), length=round(float(L), 1), poly=np.round(poly, 1).tolist(),
                 aabb=[int(math.floor(poly[:, 0].min())), int(math.floor(poly[:, 1].min())), int(math.ceil(poly[:, 0].max())), int(math.ceil(poly[:, 1].max()))],
                 snapped=all(s['snapped'] for s in segs), touches_line=any(s['touches'] for s in segs),
                 text_px=int(wt.sum()), annot_line=w['line'])
        if path: d['path'] = path
        out.append(d)
    for b in boxes:
        if b['op'] in ('CARELINE', 'EXCLLINE'):
            st = np.zeros(ink.shape, np.uint8); a_ = np.array(b['seg'], float) - [wx0, wy0, wx0, wy0]
            cv2.line(st, (int(round(a_[0])), int(round(a_[1]))), (int(round(a_[2])), int(round(a_[3]))), 1, b['width'])
            st = st > 0
            if b['op'] == 'CARELINE': care |= text & st
            else: care &= ~st
            text &= ~st; continue
        x0_, y0_, x1_, y1_ = b['box']
        s = (slice(max(0, y0_ - wy0), max(0, y1_ - wy0)), slice(max(0, x0_ - wx0), max(0, x1_ - wx0)))
        if b['op'] == 'EXCL': text[s] = False; care[s] = False
        elif b['op'] == 'FORCE': text[s] |= ink[s]; care[s] &= ~ink[s]
        elif b['op'] == 'CARE': care[s] |= ink[s]; text[s] &= ~ink[s]
    text &= ~care
    oy, ox = Y0 - wy0, X0 - wx0
    sl = (slice(oy, oy + (Y1 - Y0)), slice(ox, ox + (X1 - X0)))
    M = np.zeros((Y1 - Y0, X1 - X0), np.uint8); I = ink[sl]
    M[I] = 1; M[I & text[sl]] = 2; M[I & care[sl]] = 3
    # each word's text px inside the window only
    for d_ in (OUT, COPY):
        os.makedirs(d_, exist_ok=True); cv2.imwrite(os.path.join(d_, f'{cid}_mask.png'), M)
    rec = dict(crop=cid, plate=p, win=c['win'], why=c.get('why', ''), held_out=True, n_words=len(out), mask=f'{cid}_mask.png',
               mask_values={'0': 'paper', '1': 'ink, not text', '2': 'text ink', '3': "don't care (glyph and line share ink; CARE boxes)"},
               counts={k: int((M == v).sum()) for k, v in (('paper', 0), ('ink_not_text', 1), ('text', 2), ('dont_care', 3))},
               boxes=boxes, words=out)
    for d_ in (OUT, COPY):
        with open(os.path.join(d_, f'{cid}_words.json'), 'w', encoding='utf8') as fh:
            json.dump(rec, fh, indent=1, ensure_ascii=False)
    print(cid, len(out), 'words', rec['counts'], f"text share of ink {rec['counts']['text'] / max(1, int(I.sum())):.3f}")
    for s_ in notes: print('  ', s_)
    if check:
        # text pieces that run on well outside every word box: look at them
        tc = text & ~care
        rest = ink & ~straight_runs(ink, 41)
        n, lb, _, _ = cv2.connectedComponentsWithStats(rest.astype(np.uint8), connectivity=8)
        inb = cv2.dilate((wbox > 0).astype(np.uint8), np.ones((13, 13), np.uint8)) > 0
        tot = np.bincount(lb.ravel(), minlength=n); outb = np.bincount(lb.ravel(), (~inb).ravel(), minlength=n)
        hastext = np.bincount(lb.ravel(), tc.ravel(), minlength=n) > 0
        bad = hastext & (outb >= 12) & (outb >= 0.25 * tot); bad[0] = False
        spill = bad[lb] & tc
        render(cid, img[sl[0], sl[1]], M, spill[sl], out)


def render(cid, im, M, spill, words, tw=500, th=500, sc=1.5, P=25):
    X0, Y0, X1, Y1 = CROPS[cid]['win']
    c = (im * 0.3 + 255 * 0.7).astype(np.uint8)
    c[M == 1] = (120, 120, 120); c[M == 2] = (0, 0, 230); c[M == 3] = (0, 210, 255); c[spill] = (0, 140, 255)
    big = cv2.copyMakeBorder(c, P, P, P, P, cv2.BORDER_CONSTANT, value=(255, 255, 255))
    for r, ty in enumerate(range(0, Y1 - Y0, th)):
        for q, tx in enumerate(range(0, X1 - X0, tw)):
            ox, oy = tx - P, ty - P
            t = big[ty:ty + th + 2 * P, tx:tx + tw + 2 * P].copy()
            t = cv2.resize(t, None, fx=sc, fy=sc, interpolation=cv2.INTER_NEAREST)
            for w in words:
                qq = (np.array(w['poly']) - [X0 + ox, Y0 + oy]) * sc
                if qq[:, 0].max() < 0 or qq[:, 1].max() < 0 or qq[:, 0].min() > t.shape[1] or qq[:, 1].min() > t.shape[0]: continue
                cv2.polylines(t, [np.round(qq).astype(np.int32)], True, (255, 0, 170), 1)
                k = qq[np.argmin(qq[:, 1])]
                cv2.putText(t, str(w['annot_line']), (int(k[0]) + 2, int(k[1]) - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.33, (160, 0, 120), 1)
            for gx in range(((X0 + ox) // 100 + 1) * 100, X0 + ox + int(t.shape[1] / sc) - 1, 100):
                Xp = int((gx - X0 - ox) * sc); cv2.putText(t, str(gx), (Xp + 2, 11), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (200, 0, 0), 1); t[:8, Xp] = (200, 0, 0)
            for gy in range(((Y0 + oy) // 100 + 1) * 100, Y0 + oy + int(t.shape[0] / sc) - 1, 100):
                Yp = int((gy - Y0 - oy) * sc); cv2.putText(t, str(gy), (2, Yp - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (200, 0, 0), 1); t[Yp, :8] = (200, 0, 0)
            cv2.imwrite(os.path.join(WORK, f'{cid}_check_{r}{q}.jpg'), t, [cv2.IMWRITE_JPEG_QUALITY, 92])


if __name__ == '__main__':
    chk = '--check' in sys.argv
    for a in [a for a in sys.argv[1:] if not a.startswith('--')]: build(a, chk)
