"""SEALED FINAL builder (sealed cross-check, 26 Nov 2026): one builder for both halves of the sealed truth.
A merge of sealed_A/scripts/build_truth_sa.py and sealed_B/scripts/build.py, which are both copies of
text_v1/truth-fix/scripts/build_truth_v2.py. The snap, the line peel, the hand ops and the shared-ink rule are the v2 code,
unchanged. Reads sealed_final/crops.json and sealed_final/annot/<annot or id>.txt; writes <id>_mask.png and <id>_words.json.

    cd data/sanborn
    python -B bench_2026-11-26/text_fix/sealed_check/scripts/build_final.py all|SA-B01 ... [--out=DIR] [--scope=half]

Kept from the half builders:
  - TARGETED crops (crops.json "kind": "targeted"): the scope is the union of each target word's axis box (aabb of its
    snapped box) grown by scope_pad (25) px. Inside it all ink is labelled (2 text, 1 not text, 3 don't care); outside
    it the mask is 3, paper too. The scope box [x0, y0, x1, y1] = [a0-25, a1-25, a2+25, a3+25] includes both ends.
    (--scope=half reproduces the halves exactly: half A included both ends, half B left out the last row and column.)
  - targets: a word line flagged `target`; or, for a crop that reads a shared annotation file ("annot"), the lines in
    "target_lines" (half A's ditto windows; words and ops more than 60 px from the window are left out, as in half A).
  - ops: v2's EXCL FORCE CARE CAREDIR CARELINE NOTTEXT FORCELINE EXCLCIRC, plus half A's CARESTRIP (all ink in the strip
    is don't care) and the cross-check's EXCLPIECE x0 y0 x1 y1 (every 8-connected piece of text lying wholly inside the
    box is not text: a dash of a dashed line or a wall stub inside a word box).
  - "line_bridge": B (SB-F1 only): half B's extra line peel (straight runs of 121 px once gaps up to 2B px are bridged).
  - words.json: target words and every word whose box meets the scope; the rest are listed in dropped_outside_scope.
    Each word has target (bool), ink_px (ink inside its box) and text_px_final (its text pixels in the final mask: what
    score_text.py counts for it).
No bin and no method output is read."""
import sys, os, json, math
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import numpy as np, cv2
from common import FINAL, window, line_mask, line_mask_bridged, rrect_poly, jdump

TR = FINAL
OUT = next((a.split('=', 1)[1] for a in sys.argv if a.startswith('--out=')), TR)
SCOPE_HALF = '--scope=half' in sys.argv
PAD = 120
KINDS = {'street', 'house', 'lotdim', 'lot', 'block', 'owner', 'bldg', 'story', 'pipe', 'sewer', 'rail', 'adj', 'ditto', 'other'}


def parse(tid, c):
    words, boxes = [], []
    af = c.get('annot', tid)
    for k, raw in enumerate(open(os.path.join(TR, 'annot', f'{af}.txt'), encoding='utf8')):
        s = raw.strip()
        if not s or s.startswith('#'): continue
        op = s.split()[0]
        if op in ('EXCL', 'FORCE', 'CARE', 'EXCLPIECE'):
            f = s.split(); boxes.append(dict(op=op, box=[int(v) for v in f[1:5]], note=' '.join(f[5:]), line=k + 1)); continue
        if op == 'CAREDIR':
            f = s.split(); boxes.append(dict(op=op, box=[int(v) for v in f[1:5]], angle=float(f[5]), length=int(f[6]), note=' '.join(f[7:]), line=k + 1)); continue
        if op == 'EXCLCIRC':
            f = s.split(); boxes.append(dict(op=op, circ=[float(v) for v in f[1:4]], note=' '.join(f[4:]), line=k + 1)); continue
        if op in ('CARELINE', 'NOTTEXT', 'FORCELINE', 'CARESTRIP'):
            f = s.split(); boxes.append(dict(op=op, seg=[int(v) for v in f[1:5]], width=int(f[5]), note=' '.join(f[6:]), line=k + 1)); continue
        parts = [q.strip() for q in s.split('|')]
        g = [float(v) for v in parts[0].split()]
        if len(g) != 5: raise SystemExit(f'{tid} line {k + 1}: need x1 y1 x2 y2 h: {s}')
        kind = parts[2]
        if kind not in KINDS: raise SystemExit(f'{tid} line {k + 1}: unknown kind {kind}')
        flags = parts[3].split() if len(parts) > 3 else []
        tgt = 'target' in flags; flags = [f for f in flags if f != 'target']
        words.append(dict(geo=g, reading=parts[1], kind=kind, flags=flags, target=tgt, line=k + 1))
    return words, boxes


def in_rect(xs, ys, cx, cy, L, h, ang):
    a = math.radians(ang); u = (math.cos(a), math.sin(a)); v = (-math.sin(a), math.cos(a))
    dx, dy = xs - cx, ys - cy; al = dx * u[0] + dy * u[1]; ac = dx * v[0] + dy * v[1]
    return (np.abs(al) <= L / 2) & (np.abs(ac) <= h / 2), al, ac


SHARE_PX = 2
# (A rule that peeled shorter straight runs (21 px) leaving the word box was tried on 26 Nov and rejected: on the
#  before/after pictures it took italic glyph strokes as often as building walls. Walls are fixed by hand ops instead.)


def share_rule(ink, text, care):
    """v2 shared-ink rule, unchanged"""
    nt = ink & ~text & ~care
    n, lb = cv2.connectedComponents(ink.astype(np.uint8), connectivity=8)
    both = np.intersect1d(np.unique(lb[text]), np.unique(lb[nt])); both = both[both > 0]
    if not len(both): return 0
    k = np.ones((2 * SHARE_PX + 1, 2 * SHARE_PX + 1), np.uint8); moved = 0
    sl = __import__('scipy.ndimage', fromlist=['find_objects']).find_objects(lb)
    for i in both:
        ys, xs = sl[i - 1]; y0, y1 = max(0, ys.start - SHARE_PX), min(ink.shape[0], ys.stop + SHARE_PX); x0, x1 = max(0, xs.start - SHARE_PX), min(ink.shape[1], xs.stop + SHARE_PX)
        m = lb[y0:y1, x0:x1] == i; t = text[y0:y1, x0:x1] & m; o = nt[y0:y1, x0:x1] & m
        band = ((cv2.dilate(t.astype(np.uint8), k) > 0) & o) | ((cv2.dilate(o.astype(np.uint8), k) > 0) & t)
        care[y0:y1, x0:x1] |= band; text[y0:y1, x0:x1] &= ~band; moved += int(band.sum())
    return moved


def build(tid, crops, quiet=False):
    c = crops[tid]; p = c['plate']; X0, Y0, X1, Y1 = c['win']
    img, lab, ink, (wx0, wy0, wx1, wy1) = window(p, X0 - PAD, Y0 - PAD, X1 + PAD, Y1 + PAD)
    hh, ww = ink.shape
    words, boxes = parse(tid, c)
    if 'annot' in c:   # half A: a shared annotation file per ditto window
        tl_ = set(c.get('target_lines', []))
        def near(x0_, y0_, x1_, y1_, m=60): return not (x1_ < X0 - m or x0_ > X1 + m or y1_ < Y0 - m or y0_ > Y1 + m)
        words = [w for w in words if near(min(w['geo'][0], w['geo'][2]), min(w['geo'][1], w['geo'][3]), max(w['geo'][0], w['geo'][2]), max(w['geo'][1], w['geo'][3]))]
        for w in words: w['target'] = w['line'] in tl_
        if not any(w['target'] for w in words): raise SystemExit(f'{tid}: none of target_lines {sorted(tl_)} is a word near the window')
        def bnear(b):
            if 'circ' in b: cx_, cy_, r_ = b['circ']; return near(cx_ - r_, cy_ - r_, cx_ + r_, cy_ + r_)
            q = b.get('box') or b.get('seg'); return near(min(q[0], q[2]), min(q[1], q[3]), max(q[0], q[2]), max(q[1], q[3]))
        boxes = [b for b in boxes if bnear(b)]
    text = np.zeros_like(ink); care = np.zeros_like(ink); notes = []
    yy, xx = np.mgrid[0:hh, 0:ww]
    out_words = []
    for i, w in enumerate(words):
        x1, y1, x2, y2, h = w['geo']; ang = math.degrees(math.atan2(y2 - y1, x2 - x1)); L = math.hypot(x2 - x1, y2 - y1)
        cx, cy = (x1 + x2) / 2 - wx0, (y1 + y2) / 2 - wy0
        Lline = int(max(41, round(1.5 * h))) | 1
        R = int(L / 2 + h + Lline + 10)
        bx0, by0, bx1, by1 = max(0, int(cx - R)), max(0, int(cy - R)), min(ww, int(cx + R)), min(hh, int(cy + R))
        sub_ink = ink[by0:by1, bx0:bx1]
        sub_ln = line_mask(sub_ink, Lline, nang=72)
        if c.get('line_bridge'): sub_ln |= line_mask_bridged(sub_ink, 121, int(c['line_bridge']))
        X = xx[by0:by1, bx0:bx1].astype(float); Y = yy[by0:by1, bx0:bx1].astype(float)
        mg_a, mg_c = 0.15 * h + 4, 0.15 * h + 3
        snapped = False
        if 'nosnap' not in w['flags']:
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
        inw, al, ac = in_rect(X, Y, cx, cy, L + 3, h + 3, ang)
        n, lb, st, _ = cv2.connectedComponentsWithStats(sub_ln.astype(np.uint8), connectivity=8)
        outside = np.bincount(lb.ravel(), (~in_rect(X, Y, cx, cy, L + 8, h + 8, ang)[0]).ravel(), minlength=n) > 0; outside[0] = False
        lpx = (cv2.dilate(outside[lb].astype(np.uint8), np.ones((5, 5), np.uint8)) > 0) & sub_ink
        t = sub_ink & inw & ~lpx
        ov = lpx & inw & (cv2.dilate(t.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0)
        text[by0:by1, bx0:bx1] |= t; care[by0:by1, bx0:bx1] |= ov
        poly = rrect_poly(cx + wx0, cy + wy0, L, h, ang)
        tl = bool((cv2.dilate(t.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0)[lpx].any())
        out_words.append(dict(id=f'{tid}-{i + 1:03d}', reading=w['reading'], kind=w['kind'], flags=w['flags'], target=w['target'], angle=round(ang, 1),
                              height=round(float(h), 1), length=round(float(L), 1), poly=np.round(poly, 1).tolist(),
                              aabb=[int(math.floor(poly[:, 0].min())), int(math.floor(poly[:, 1].min())), int(math.ceil(poly[:, 0].max())), int(math.ceil(poly[:, 1].max()))],
                              snapped=snapped, touches_line=tl, text_px=int(t.sum()), annot_line=w['line']))
    sl0 = (slice(Y0 - wy0, Y0 - wy0 + (Y1 - Y0)), slice(X0 - wx0, X0 - wx0 + (X1 - X0)))
    def _state(): return text[sl0].astype(np.uint8) * 2 + care[sl0].astype(np.uint8)
    prev = _state(); last_b = None   # each op's own effect: pixels of the crop window whose class it changed (before the shared-ink rule)
    for b in boxes:
        if last_b is not None: cur = _state(); last_b['effect_px'] = int((cur != prev).sum()); prev = cur
        last_b = b
        if b['op'] == 'EXCLCIRC':
            cx_, cy_, r_ = b['circ']; st_ = (xx - (cx_ - wx0)) ** 2 + (yy - (cy_ - wy0)) ** 2 <= r_ * r_
            text &= ~st_; care &= ~st_; continue
        if b['op'] in ('CARELINE', 'NOTTEXT', 'FORCELINE', 'CARESTRIP'):
            st_ = np.zeros_like(ink, np.uint8); a_ = np.array(b['seg'], float) - [wx0, wy0, wx0, wy0]
            cv2.line(st_, (int(round(a_[0])), int(round(a_[1]))), (int(round(a_[2])), int(round(a_[3]))), 1, b['width'])
            st_ = st_ > 0
            if b['op'] == 'CARELINE': care |= text & st_; text &= ~st_
            elif b['op'] == 'NOTTEXT': text &= ~st_; care &= ~st_
            elif b['op'] == 'CARESTRIP': care |= ink & st_; text &= ~st_
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
        if b['op'] == 'EXCLPIECE':   # sealed-check: each 8-connected piece of text lying wholly inside the box is not text (a dash, a wall stub)
            n_, lb_ = cv2.connectedComponents(text.astype(np.uint8), connectivity=8)
            inside = np.zeros(n_, bool); inside[np.unique(lb_[s])] = True
            m_ = np.ones(lb_.shape, bool); m_[s] = False; inside[np.unique(lb_[m_ & (lb_ > 0)])] = False; inside[0] = False
            kill = inside[lb_]; text &= ~kill; care &= ~kill; continue
        if b['op'] == 'EXCL': text[s] = False; care[s] = False
        elif b['op'] == 'FORCE': text[s] |= ink[s]; care[s] &= ~ink[s]
        elif b['op'] == 'CARE': care[s] |= ink[s]; text[s] &= ~ink[s]
    if last_b is not None: last_b['effect_px'] = int((_state() != prev).sum())
    text &= ~care
    share_rule(ink, text, care)
    oy, ox = Y0 - wy0, X0 - wx0
    sl = (slice(oy, oy + (Y1 - Y0)), slice(ox, ox + (X1 - X0)))
    M = np.zeros((Y1 - Y0, X1 - X0), np.uint8); I = ink[sl]
    M[I] = 1; M[I & text[sl]] = 2; M[I & care[sl]] = 3
    scope = None; dropped = []; scope_px = None
    if c.get('kind') == 'targeted':
        pad = int(c.get('scope_pad', 25)); S = np.zeros(M.shape, bool); scope = []
        tg = [w for w in out_words if w['target']]
        if not tg: raise SystemExit(f'{tid}: targeted crop without a target word')
        incl = 0 if (SCOPE_HALF and c.get('half') == 'B') else 1
        for w in tg:
            a = w['aabb']; r = [a[0] - pad, a[1] - pad, a[2] + pad, a[3] + pad]; scope.append(r)
            S[max(0, r[1] - Y0):max(0, r[3] - Y0 + incl), max(0, r[0] - X0):max(0, r[2] - X0 + incl)] = True
            if r[0] < X0 or r[1] < Y0 or r[2] >= X1 or r[3] >= Y1: notes.append(f'{tid}: scope {r} reaches outside the window {c["win"]}')
        M[~S] = 3; scope_px = int(S.sum())
        keep = []
        for w in out_words:
            pm = np.zeros(M.shape, np.uint8); cv2.fillPoly(pm, [np.round(np.array(w['poly']) - [X0, Y0]).astype(np.int32)], 1)
            if w['target'] or (pm.astype(bool) & S).any(): keep.append(w)
            else: dropped.append(dict(id=w['id'], reading=w['reading'], kind=w['kind'], annot_line=w['annot_line']))
        out_words = keep
    for w in out_words:
        pm = np.zeros(M.shape, np.uint8); cv2.fillPoly(pm, [np.round(np.array(w['poly']) - [X0, Y0]).astype(np.int32)], 1); pm = pm > 0
        w['ink_px'] = int((pm & I).sum()); w['text_px_final'] = int((pm & (M == 2)).sum())
    os.makedirs(OUT, exist_ok=True); cv2.imwrite(os.path.join(OUT, f'{tid}_mask.png'), M)
    rec = dict(crop=tid, plate=p, win=c['win'], scale_ft_per_inch=c.get('scale_ft_per_inch'), half=c.get('half'), kind=c.get('kind', 'full'),
               target=c.get('target'), scope_pad=c.get('scope_pad'), scope=scope, scope_px=scope_px, why=c.get('why', ''),
               n_words=len(out_words), mask=f'{tid}_mask.png',
               mask_values={'0': 'paper', '1': 'ink, not text', '2': 'text ink', '3': "don't care (shared ink, CARE boxes, outside the scope of a targeted crop)"},
               counts={k: int((M == v).sum()) for k, v in (('paper', 0), ('ink_not_text', 1), ('text', 2), ('dont_care', 3))},
               boxes=boxes, words=out_words, dropped_outside_scope=dropped)
    jdump(rec, os.path.join(OUT, f'{tid}_words.json'))
    if not quiet:
        tg = [w for w in out_words if w['target']]
        print(tid, p, len(out_words), 'words', rec['counts'], ' targets:', ' '.join(f"{w['reading']}({w['ink_px']}/{w['text_px_final']})" for w in tg))
        for s in notes: print('  ', s)
    return rec


if __name__ == '__main__':
    crops = json.load(open(os.path.join(TR, 'crops.json'), encoding='utf8'))
    ids = [a for a in sys.argv[1:] if not a.startswith('--')]
    if ids == ['all']: ids = list(crops)
    for t in ids: build(t, crops, quiet='--quiet' in sys.argv)
