"""TARGETED TRUTH builder for ditto marks (dev_ditto, 26 Nov 2026). An adapted copy of text_v1/truth-fix/scripts/
build_truth_v2.py (truth v2's builder): the same word snap, line rule, hand ops and shared-ink rule, plus box words and
the targeted scope.

    cd data/sanborn
    python -B bench_2026-11-26/text_fix/dev_ditto/scripts/build_dd.py TRUTHDIR [ID ...] [--check] [--sheet]

TRUTHDIR is dev_ditto/truth or dev_ditto/negatives. It holds crops.json and annot/<ID>.txt; the builder writes
<ID>_mask.png and <ID>_words.json there, and check pictures to TRUTHDIR/check/. No ID: every crop in crops.json.

Annotation lines (full-plate px):
  B x0 y0 x1 y1 | reading | kind [| flags]       (new) a word given by its axis box (inclusive pixel corners). The ink in
      the box grown by 1 px is the word's ink, less line ink that reaches outside the box (as for v2 words). Used for
      ditto marks (tight boxes read off the piece boxes of scripts/cand.py) and for short neighbouring words.
  x1 y1 x2 y2 h | reading | kind [| flags]      a word by its centre line and height, snapped (v2, unchanged).
  EXCL / FORCE / CARE / CAREDIR / CARELINE / NOTTEXT / FORCELINE / EXCLCIRC: the v2 hand ops, unchanged, in file order.
  # comment
Flags: target (the word is a target; kind ditto is a target unless flagged nontarget), style:pair / style:quote /
  style:other (the ditto's look, by eye), unsure, partial, nosnap, curved, and for negatives neg:TYPE on the marks.
Kinds: v2's (street house lotdim lot block owner bldg story pipe sewer rail adj ditto other) and, for the negative set,
  negative (a non-text look-alike mark: its ink is labelled 1, it is listed in words.json but has no text).

Mask (<ID>_mask.png, the size of the crop window): 0 paper, 1 ink that is not text, 2 text ink, 3 don't care.
  Text, line and shared-ink rules as truth v2 (shared ink within 2 px of a text-line contact is 3). Then the SCOPE:
  crops.json 'scope_pad' (25): the union of every target word's axis box grown by scope_pad px is scored; all ink
  outside it is 3. 'scope': 'window' (negatives) scores the whole window.
Words (<ID>_words.json): {'words': [...]} as v2 (id, reading, kind, flags, poly, aabb, text_px ...) plus, for targets,
  target=True, ink_px (all ink in the box), pieces (8-connected pieces of its text ink), style, and a 'scope' list."""
import sys, os, json, math
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common import window, line_mask, rrect_poly, jdump

PAD = 120
KINDS = {'street', 'house', 'lotdim', 'lot', 'block', 'owner', 'bldg', 'story', 'pipe', 'sewer', 'rail', 'adj', 'ditto', 'other', 'negative'}
SHARE_PX = 2


def parse(path):
    words, boxes = [], []
    for k, raw in enumerate(open(path, encoding='utf8')):
        s = raw.strip()
        if not s or s.startswith('#'): continue
        f = s.split()
        if f[0] in ('EXCL', 'FORCE', 'CARE'):
            boxes.append(dict(op=f[0], box=[int(v) for v in f[1:5]], note=' '.join(f[5:]), line=k + 1)); continue
        if f[0] == 'CAREDIR':
            boxes.append(dict(op=f[0], box=[int(v) for v in f[1:5]], angle=float(f[5]), length=int(f[6]), note=' '.join(f[7:]), line=k + 1)); continue
        if f[0] == 'EXCLCIRC':
            boxes.append(dict(op=f[0], circ=[float(v) for v in f[1:4]], note=' '.join(f[4:]), line=k + 1)); continue
        if f[0] in ('CARELINE', 'NOTTEXT', 'FORCELINE'):
            boxes.append(dict(op=f[0], seg=[int(v) for v in f[1:5]], width=int(f[5]), note=' '.join(f[6:]), line=k + 1)); continue
        parts = [q.strip() for q in s.split('|')]
        g = parts[0].split(); isbox = g[0] == 'B'
        if isbox: g = g[1:]
        g = [float(v) for v in g]
        if len(g) != (4 if isbox else 5): raise SystemExit(f'{path} line {k + 1}: bad geometry: {s}')
        kind = parts[2]
        if kind not in KINDS: raise SystemExit(f'{path} line {k + 1}: unknown kind {kind}')
        flags = parts[3].split() if len(parts) > 3 else []
        words.append(dict(geo=g, box=isbox, reading=parts[1], kind=kind, flags=flags, line=k + 1))
    return words, boxes


def in_rect(xs, ys, cx, cy, L, h, ang):
    a = math.radians(ang); u = (math.cos(a), math.sin(a)); v = (-math.sin(a), math.cos(a))
    dx, dy = xs - cx, ys - cy; al = dx * u[0] + dy * u[1]; ac = dx * v[0] + dy * v[1]
    return (np.abs(al) <= L / 2) & (np.abs(ac) <= h / 2), al, ac


def share_rule(ink, text, care):
    """v2: in every 8-connected ink piece that holds text and non-text ink, the ink of either within SHARE_PX px of the
    other becomes don't care"""
    from scipy.ndimage import find_objects
    nt = ink & ~text & ~care
    n, lb = cv2.connectedComponents(ink.astype(np.uint8), connectivity=8)
    both = np.intersect1d(np.unique(lb[text]), np.unique(lb[nt])); both = both[both > 0]
    if not len(both): return 0
    k = np.ones((2 * SHARE_PX + 1, 2 * SHARE_PX + 1), np.uint8); moved = 0; sl = find_objects(lb)
    for i in both:
        ys, xs = sl[i - 1]; y0, y1 = max(0, ys.start - SHARE_PX), min(ink.shape[0], ys.stop + SHARE_PX); x0, x1 = max(0, xs.start - SHARE_PX), min(ink.shape[1], xs.stop + SHARE_PX)
        m = lb[y0:y1, x0:x1] == i; t = text[y0:y1, x0:x1] & m; o = nt[y0:y1, x0:x1] & m
        band = ((cv2.dilate(t.astype(np.uint8), k) > 0) & o) | ((cv2.dilate(o.astype(np.uint8), k) > 0) & t)
        care[y0:y1, x0:x1] |= band; text[y0:y1, x0:x1] &= ~band; moved += int(band.sum())
    return moved


def is_target(w):
    if 'nontarget' in w['flags']: return False
    return 'target' in w['flags'] or w['kind'] == 'ditto'


def build(TD, tid, crops, check=False):
    c = crops[tid]; p = c['plate']; X0, Y0, X1, Y1 = c['win']
    img, lab, ink, (wx0, wy0, wx1, wy1) = window(p, X0 - PAD, Y0 - PAD, X1 + PAD, Y1 + PAD)
    hh, ww = ink.shape
    words, boxes = parse(os.path.join(TD, 'annot', f'{tid}.txt'))
    text = np.zeros_like(ink); care = np.zeros_like(ink); notes = []
    yy, xx = np.mgrid[0:hh, 0:ww]
    out_words = []; boxmasks = []
    for i, w in enumerate(words):
        if w['box']:
            bx0_, by0_, bx1_, by1_ = w['geo']; L = bx1_ - bx0_ + 1; h = by1_ - by0_ + 1; ang = 0.0
            cx, cy = (bx0_ + bx1_ + 1) / 2 - wx0, (by0_ + by1_ + 1) / 2 - wy0
            Lline = 41
        else:
            x1, y1, x2, y2, h = w['geo']; ang = math.degrees(math.atan2(y2 - y1, x2 - x1)); L = math.hypot(x2 - x1, y2 - y1)
            cx, cy = (x1 + x2) / 2 - wx0, (y1 + y2) / 2 - wy0
            Lline = int(max(41, round(1.5 * h))) | 1
        R = int(max(L, h) / 2 + h + Lline + 10)
        bx0, by0, bx1, by1 = max(0, int(cx - R)), max(0, int(cy - R)), min(ww, int(cx + R)), min(hh, int(cy + R))
        sub_ink = ink[by0:by1, bx0:bx1]
        sub_ln = line_mask(sub_ink, Lline, nang=72)
        X = xx[by0:by1, bx0:bx1].astype(float) + 0.5; Y = yy[by0:by1, bx0:bx1].astype(float) + 0.5
        snapped = False
        if not w['box'] and 'nosnap' not in w['flags']:   # v2 snap, unchanged
            mg_a, mg_c = 0.15 * h + 4, 0.15 * h + 3
            cand = sub_ink & ~(cv2.dilate(sub_ln.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0)
            n, lb, st, _ = cv2.connectedComponentsWithStats(cand.astype(np.uint8), connectivity=8)
            inw, al, ac = in_rect(X, Y, cx, cy, L + 2 * mg_a, h + 2 * mg_c, ang)
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
            else:
                notes.append(f'{tid} line {w["line"]} {w["reading"]!r}: nothing to snap to')
        grow = 2 if w['box'] else 3     # box words: the box grown by 1 px each side; v2 words: 1.5 px
        inw, al, ac = in_rect(X, Y, cx, cy, L + grow, h + grow, ang)
        n, lb, st, _ = cv2.connectedComponentsWithStats(sub_ln.astype(np.uint8), connectivity=8)
        outside = np.bincount(lb.ravel(), (~in_rect(X, Y, cx, cy, L + 8, h + 8, ang)[0]).ravel(), minlength=n) > 0; outside[0] = False
        lpx = (cv2.dilate(outside[lb].astype(np.uint8), np.ones((5, 5), np.uint8)) > 0) & sub_ink
        if w['kind'] == 'negative': t = np.zeros_like(sub_ink)       # a look-alike mark: listed, never text
        else: t = sub_ink & inw & ~lpx
        ov = lpx & inw & (cv2.dilate(t.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0)
        text[by0:by1, bx0:bx1] |= t; care[by0:by1, bx0:bx1] |= ov
        poly = rrect_poly(cx + wx0, cy + wy0, L, h, ang)
        tl = bool((cv2.dilate(t.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0)[lpx].any())
        bm = np.zeros_like(ink); bm[by0:by1, bx0:bx1] = inw & sub_ink; boxmasks.append(bm)
        out_words.append(dict(id=f'{tid}-{i + 1:03d}', reading=w['reading'], kind=w['kind'], flags=w['flags'], angle=round(ang, 1),
                              height=round(float(h), 1), length=round(float(L), 1), poly=np.round(poly, 1).tolist(),
                              aabb=[int(math.floor(poly[:, 0].min())), int(math.floor(poly[:, 1].min())), int(math.ceil(poly[:, 0].max())), int(math.ceil(poly[:, 1].max()))],
                              snapped=snapped, touches_line=tl, annot_line=w['line'], target=is_target(w), box_word=w['box']))
    for b in boxes:   # v2 ops, unchanged
        if b['op'] == 'EXCLCIRC':
            cx_, cy_, r_ = b['circ']; st_ = (xx - (cx_ - wx0)) ** 2 + (yy - (cy_ - wy0)) ** 2 <= r_ * r_
            text &= ~st_; care &= ~st_; continue
        if b['op'] in ('CARELINE', 'NOTTEXT', 'FORCELINE'):
            st_ = np.zeros_like(ink, np.uint8); a_ = np.array(b['seg'], float) - [wx0, wy0, wx0, wy0]
            cv2.line(st_, (int(round(a_[0])), int(round(a_[1]))), (int(round(a_[2])), int(round(a_[3]))), 1, b['width'])
            st_ = st_ > 0
            if b['op'] == 'CARELINE': care |= text & st_; text &= ~st_
            elif b['op'] == 'NOTTEXT': text &= ~st_; care &= ~st_
            else: text |= ink & st_; care &= ~st_
            continue
        x0_, y0_, x1_, y1_ = b['box']; s = (slice(max(0, y0_ - wy0), max(0, y1_ - wy0)), slice(max(0, x0_ - wx0), max(0, x1_ - wx0)))
        if b['op'] == 'CAREDIR':
            sub = ink[max(0, y0_ - wy0 - 60):y1_ - wy0 + 60, max(0, x0_ - wx0 - 60):x1_ - wx0 + 60]
            u = cv2.morphologyEx(sub.astype(np.uint8), cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))); o = np.zeros_like(u)
            Lk = b['length'] | 1; c_ = Lk // 2
            for da in np.arange(-10, 10.1, 2.5):
                a = math.radians(b['angle'] + da); k_ = np.zeros((Lk, Lk), np.uint8); d_ = np.array([math.cos(a), math.sin(a)]) * c_
                cv2.line(k_, tuple(np.round(c_ - d_).astype(int).tolist()), tuple(np.round(c_ + d_).astype(int).tolist()), 1, 1)
                o |= cv2.morphologyEx(u, cv2.MORPH_OPEN, k_)
            o = cv2.dilate(o, np.ones((5, 5), np.uint8)) > 0
            oy_, ox_ = (y0_ - wy0) - max(0, y0_ - wy0 - 60), (x0_ - wx0) - max(0, x0_ - wx0 - 60)
            m = np.zeros_like(ink); m[s] = o[oy_:oy_ + (s[0].stop - s[0].start), ox_:ox_ + (s[1].stop - s[1].start)]
            care |= text & m; text &= ~m; continue
        if b['op'] == 'EXCL': text[s] = False; care[s] = False
        elif b['op'] == 'FORCE': text[s] |= ink[s]; care[s] &= ~ink[s]
        elif b['op'] == 'CARE': care[s] |= ink[s]; text[s] &= ~ink[s]
    text &= ~care
    share_rule(ink, text, care)
    # scope
    oy, ox = Y0 - wy0, X0 - wx0
    sl = (slice(oy, oy + (Y1 - Y0)), slice(ox, ox + (X1 - X0)))
    scope = np.zeros((Y1 - Y0, X1 - X0), bool); scopes = []
    if c.get('scope') == 'window': scope[:] = True; scopes.append([X0, Y0, X1, Y1])
    else:
        pad = int(c.get('scope_pad', 25))
        for w in out_words:
            if not w['target']: continue
            a0, b0, a1, b1 = w['aabb']; s0 = [a0 - pad, b0 - pad, a1 + pad, b1 + pad]; scopes.append(s0)
            scope[max(0, s0[1] - Y0):max(0, s0[3] - Y0), max(0, s0[0] - X0):max(0, s0[2] - X0)] = True
    M = np.zeros((Y1 - Y0, X1 - X0), np.uint8); I = ink[sl]
    M[I] = 1; M[I & text[sl]] = 2; M[I & care[sl]] = 3
    M[I & ~scope] = 3
    os.makedirs(TD, exist_ok=True); cv2.imwrite(os.path.join(TD, f'{tid}_mask.png'), M)
    # per-word numbers (text px inside the poly, as score_text.py counts them; for targets ink and pieces too)
    for w, bm in zip(out_words, boxmasks):
        pm = np.zeros((Y1 - Y0, X1 - X0), np.uint8)
        cv2.fillPoly(pm, [np.round(np.array(w['poly'], float) - [X0, Y0]).astype(np.int32)], 1); pm = pm > 0
        w['text_px'] = int(((M == 2) & pm).sum())
        w['in_scope'] = bool((pm & scope).any())
        if w['target'] or w['kind'] == 'negative':
            w['ink_px'] = int((I & pm).sum()); w['care_px'] = int(((M == 3) & pm & scope).sum())
            tm = ((M == 2) & pm).astype(np.uint8) if w['kind'] != 'negative' else (I & pm).astype(np.uint8)
            n_, _, st_, _ = cv2.connectedComponentsWithStats(tm, connectivity=8)
            w['pieces'] = int(n_ - 1); w['piece_px'] = sorted([int(v) for v in st_[1:, 4]], reverse=True)
            w['style'] = next((f.split(':', 1)[1] for f in w['flags'] if f.startswith('style:')), '')
            w['neg_type'] = next((f.split(':', 1)[1] for f in w['flags'] if f.startswith('neg:')), '')
    rec = dict(crop=tid, plate=p, win=c['win'], kind=c.get('kind'), target=c.get('target'), scope_pad=c.get('scope_pad'), scope=scopes,
               n_words=len(out_words), n_targets=sum(w['target'] for w in out_words), mask=f'{tid}_mask.png',
               mask_values={'0': 'paper', '1': 'ink, not text', '2': 'text ink', '3': "don't care (shared ink, CARE boxes, and all ink outside the scope)"},
               counts={k: int((M == v).sum()) for k, v in (('paper', 0), ('ink_not_text', 1), ('text', 2), ('dont_care', 3))},
               counts_in_scope={k: int(((M == v) & scope).sum()) for k, v in (('ink_not_text', 1), ('text', 2), ('dont_care', 3))},
               boxes=boxes, words=out_words)
    jdump(rec, os.path.join(TD, f'{tid}_words.json'))
    tg = [w for w in out_words if w['target']]
    print(tid, p, len(out_words), 'words,', len(tg), 'targets', rec['counts_in_scope'],
          ' target text px', [w['text_px'] for w in tg] if c.get('target') != 'negative' else [w.get('ink_px') for w in out_words if w['kind'] == 'negative'])
    for s in notes: print('  ', s)
    for w in tg:
        if w['kind'] != 'negative' and w['text_px'] == 0: print('   !! target with no text px:', w['id'], w['aabb'])
    if check: render(TD, tid, c, img[sl[0], sl[1]], M, scope, out_words)
    return rec


def colour(im, M, scope):
    o = (im.astype(np.float32) * 0.35 + 255 * 0.65).astype(np.uint8)
    o[~scope] = (o[~scope] * 0.75 + np.array([60, 60, 60]) * 0.25).astype(np.uint8)
    o[M == 1] = (200, 120, 40)      # not text: blue
    o[M == 2] = (0, 0, 230)          # text: red
    o[(M == 3) & scope] = (0, 170, 255)   # don't care in scope: orange
    o[(M == 3) & ~scope] = (170, 170, 170)  # outside scope: grey
    return o


def render(TD, tid, c, im, M, scope, words, sc=2.5):
    """check pictures in TD/check/: <ID>_overview.png (whole window, scan above, truth below, x2.5) and <ID>_zoom.png
    (every target's scope, scan left and truth right, x6)"""
    X0, Y0, X1, Y1 = c['win']; CD = os.path.join(TD, 'check'); os.makedirs(CD, exist_ok=True)
    T = colour(im, M, scope)
    def big(a, k): return cv2.resize(a, None, fx=k, fy=k, interpolation=cv2.INTER_NEAREST)
    def deco(a, k, ox, oy):
        for w in words:
            q = (np.array(w['poly']) - [ox, oy]) * k
            cv2.polylines(a, [np.round(q).astype(np.int32)], True, (0, 150, 0) if w['target'] else (200, 0, 160), 1)
            t0 = q[np.argmin(q[:, 1])]; cv2.putText(a, str(w['annot_line']), (int(t0[0]) + 2, int(t0[1]) - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.32, (120, 0, 100), 1)
        return a
    A = big(im, sc); B = deco(big(T, sc), sc, X0, Y0)
    for gx in range((X0 // 50 + 1) * 50, X1, 50):
        X = int((gx - X0) * sc); B[:6, X] = (0, 0, 0); cv2.putText(B, str(gx), (X + 2, 10), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 0, 0), 1)
    for gy in range((Y0 // 50 + 1) * 50, Y1, 50):
        Y = int((gy - Y0) * sc); B[Y, :6] = (0, 0, 0); cv2.putText(B, str(gy), (2, Y - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 0, 0), 1)
    cv2.imwrite(os.path.join(CD, f'{tid}_overview.png'), np.vstack([A, np.full((4, A.shape[1], 3), 255, np.uint8), B]))
    cells = []
    for w in [w for w in words if w['target']]:
        a0, b0, a1, b1 = w['aabb']; pad = 22
        x0, y0, x1, y1 = max(X0, a0 - pad), max(Y0, b0 - pad), min(X1, a1 + pad), min(Y1, b1 + pad)
        k = 6
        S = big(im[y0 - Y0:y1 - Y0, x0 - X0:x1 - X0], k); R = deco(big(T[y0 - Y0:y1 - Y0, x0 - X0:x1 - X0], k), k, x0, y0)
        C = np.hstack([S, np.full((S.shape[0], 3, 3), 255, np.uint8), R])
        C = cv2.copyMakeBorder(C, 14, 2, 2, 2, cv2.BORDER_CONSTANT, value=(255, 255, 255))
        cv2.putText(C, f"{w['id']} l{w['annot_line']} {w['kind']} {' '.join(w['flags'])} txt{w['text_px']}/ink{w.get('ink_px')}", (2, 11), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (0, 0, 0), 1)
        cells.append(C)
    if cells:
        CW = max(x.shape[1] for x in cells); CH = max(x.shape[0] for x in cells); cols = max(1, 1400 // (CW + 4)); rows = (len(cells) + cols - 1) // cols
        G = np.full((rows * (CH + 4), cols * (CW + 4), 3), 190, np.uint8)
        for i, x in enumerate(cells):
            r, cc = divmod(i, cols); G[r * (CH + 4):r * (CH + 4) + x.shape[0], cc * (CW + 4):cc * (CW + 4) + x.shape[1]] = x
        cv2.imwrite(os.path.join(CD, f'{tid}_zoom.png'), G)


if __name__ == '__main__':
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    TD = os.path.abspath(a[0]); crops = json.load(open(os.path.join(TD, 'crops.json')))
    ids = a[1:] or sorted(k for k in crops if os.path.exists(os.path.join(TD, 'annot', f'{k}.txt')))
    for t in ids: build(TD, t, crops, '--check' in sys.argv)
