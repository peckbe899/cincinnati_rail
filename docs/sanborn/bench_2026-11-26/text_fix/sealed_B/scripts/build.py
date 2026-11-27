"""SEALED-B truth builder (26 Nov 2026): a copy of text_v1/truth-fix/scripts/build_truth_v2.py (kept unchanged beside
it as build_truth_v2_orig.py), adapted for the targeted sealed set. Reads sealed_B/truth/crops.json and
sealed_B/truth/annot/<id>.txt, writes sealed_B/truth/<id>_mask.png and <id>_words.json, and with --check the check
pictures in sealed_B/work/.
    cd data/sanborn
    python -B bench_2026-11-26/text_fix/sealed_B/scripts/build.py SB-B01 [SB-D01 ...|all] [--check]

Changed against build_truth_v2.py (everything else, the annotation syntax, the snap, the line peel, the hand ops and
the shared-ink rule, is the same code):
  - paths: crops.json, annot/, the outputs and work/ are in sealed_B; plates are only builder B's sealed plates;
  - bin 8 is never read (the v2 check tiles showed bin 8 in green; here there is no method output at all);
  - a word line may carry the flag `target` (taken out of flags, stored as "target": true);
  - TARGETED crops (crops.json "kind": "targeted"): the scored SCOPE is the union of the target words' axis boxes
    (of the snapped rotated box) grown by scope_pad (25) px each side; outside the scope every pixel is 3 (don't care),
    paper too. The scope boxes are written into the words file ("scope") and into crops.json ("scope");
  - every word gets ink_px (ink inside its box) besides text_px (its text ink before the shared-ink rule) and
    text_px_final (its truth-2 pixels in the final mask, the pixels score_text.py counts);
  - crops.json "line_bridge": B (used on the full crop SB-F1 only): besides the v2 straight-run test, ink on a straight
    run of 121 px or more once gaps of up to 2B px along the run are bridged (common.line_mask_bridged) is line ink too,
    so long thin printed lines broken by the ink threshold are still peeled (a v2-length bridged test took text);
  - check pictures: per target word, the scan beside the truth at 6-8x (work/<id>_zoom.png); for a FULL crop, 1.5x tiles
    of scan beside truth (work/<id>_check_RC.jpg).
Mask values: 0 paper, 1 ink that is not text, 2 text ink, 3 don't care. Ink: Lab L < 140 on the paper mask."""
import sys, os, json, math
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import numpy as np, cv2
from common import INV, window, line_mask, line_mask_bridged, rrect_poly, jdump

TR = os.path.join(INV, 'truth'); WORK = os.path.join(INV, 'work'); os.makedirs(WORK, exist_ok=True)
CROPS_PATH = os.path.join(TR, 'crops.json')
PAD = 120
KINDS = {'street', 'house', 'lotdim', 'lot', 'block', 'owner', 'bldg', 'story', 'pipe', 'sewer', 'rail', 'adj', 'ditto', 'other'}


def parse(tid):
    words, boxes = [], []
    for k, raw in enumerate(open(os.path.join(TR, 'annot', f'{tid}.txt'), encoding='utf8')):
        s = raw.strip()
        if not s or s.startswith('#'): continue
        if s.split()[0] in ('EXCL', 'FORCE', 'CARE'):
            f = s.split(); boxes.append(dict(op=f[0], box=[int(v) for v in f[1:5]], note=' '.join(f[5:]), line=k + 1)); continue
        if s.split()[0] == 'CAREDIR':
            f = s.split(); boxes.append(dict(op=f[0], box=[int(v) for v in f[1:5]], angle=float(f[5]), length=int(f[6]), note=' '.join(f[7:]), line=k + 1)); continue
        if s.split()[0] == 'EXCLCIRC':
            f = s.split(); boxes.append(dict(op=f[0], circ=[float(v) for v in f[1:4]], note=' '.join(f[4:]), line=k + 1)); continue
        if s.split()[0] in ('CARELINE', 'NOTTEXT', 'FORCELINE'):
            f = s.split(); boxes.append(dict(op=f[0], seg=[int(v) for v in f[1:5]], width=int(f[5]), note=' '.join(f[6:]), line=k + 1)); continue
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


SHARE = '--noshare' not in sys.argv
SHARE_PX = 2


def share_rule(ink, text, care):
    """v2 convention: in every 8-connected ink piece that holds both text and non-text ink, the non-text ink within
    SHARE_PX px of text ink and the text ink within SHARE_PX px of non-text ink become don't care (3)."""
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


def build(tid, crops, check=False):
    c = crops[tid]; p = c['plate']; X0, Y0, X1, Y1 = c['win']
    img, lab, ink, (wx0, wy0, wx1, wy1) = window(p, X0 - PAD, Y0 - PAD, X1 + PAD, Y1 + PAD)
    hh, ww = ink.shape
    words, boxes = parse(tid)
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
        if c.get('line_bridge'): sub_ln |= line_mask_bridged(sub_ink, 121, int(c['line_bridge']))   # sealed-B: long thin lines broken by the threshold
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
    for b in boxes:
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
    if SHARE: share_rule(ink, text, care)
    oy, ox = Y0 - wy0, X0 - wx0
    sl = (slice(oy, oy + (Y1 - Y0)), slice(ox, ox + (X1 - X0)))
    M = np.zeros((Y1 - Y0, X1 - X0), np.uint8); I = ink[sl]
    M[I] = 1; M[I & text[sl]] = 2; M[I & care[sl]] = 3
    scope = None
    if c.get('kind') == 'targeted':
        pad = int(c.get('scope_pad', 25)); scope = []; S = np.zeros_like(M, bool)
        for w in out_words:
            if not w['target']: continue
            a = w['aabb']; r = [a[0] - pad, a[1] - pad, a[2] + pad, a[3] + pad]; scope.append(r)
            S[max(0, r[1] - Y0):max(0, r[3] - Y0), max(0, r[0] - X0):max(0, r[2] - X0)] = True
        if not scope: raise SystemExit(f'{tid}: targeted crop without a target word')
        for r in scope:
            if r[0] < X0 or r[1] < Y0 or r[2] > X1 or r[3] > Y1: notes.append(f'{tid}: scope {r} reaches outside the window {c["win"]}')
        M[~S] = 3
    # per-word pixel counts in the final mask
    for w in out_words:
        pm = np.zeros(M.shape, np.uint8); cv2.fillPoly(pm, [np.round(np.array(w['poly']) - [X0, Y0]).astype(np.int32)], 1); pm = pm > 0
        w['ink_px'] = int((pm & I).sum()); w['text_px_final'] = int((pm & (M == 2)).sum())
    os.makedirs(TR, exist_ok=True); cv2.imwrite(os.path.join(TR, f'{tid}_mask.png'), M)
    rec = dict(crop=tid, plate=p, win=c['win'], kind=c.get('kind', 'full'), target=c.get('target'), scope_pad=c.get('scope_pad'), scope=scope,
               why=c.get('why', ''), n_words=len(out_words), mask=f'{tid}_mask.png',
               mask_values={'0': 'paper', '1': 'ink, not text', '2': 'text ink', '3': "don't care (shared ink, CARE boxes, outside the scope)"},
               counts={k: int((M == v).sum()) for k, v in (('paper', 0), ('ink_not_text', 1), ('text', 2), ('dont_care', 3))},
               boxes=boxes, words=out_words)
    jdump(rec, os.path.join(TR, f'{tid}_words.json'))
    tg = [w for w in out_words if w['target']]
    print(tid, p, len(out_words), 'words', len(tg), 'targets', rec['counts'], ' targets:', ' '.join(f"{w['reading']}({w['ink_px']}/{w['text_px_final']})" for w in tg))
    for s in notes: print('  ', s)
    if check: render(tid, c, img[sl[0], sl[1]], M, out_words, scope)
    return rec


def colour(im, M):
    c = (im * 0.35 + 255 * 0.65).astype(np.uint8)
    c[M == 1] = (110, 110, 110); c[M == 2] = (0, 0, 230); c[M == 3] = (0, 200, 255)
    return c


def render(tid, crop, im, M, words, scope):
    X0, Y0, X1, Y1 = crop['win']
    col = colour(im, M)
    if scope is not None:   # outside the scope: blue tint over the colours
        S = np.zeros(M.shape, bool)
        for r in scope: S[max(0, r[1] - Y0):max(0, r[3] - Y0), max(0, r[0] - X0):max(0, r[2] - X0)] = True
        col[~S] = (col[~S] * 0.5 + np.array([255, 200, 160]) * 0.5).astype(np.uint8)
        panels = []
        for w in words:
            if not w['target']: continue
            a = w['aabb']; m = 32
            x0, y0, x1, y1 = max(X0, a[0] - m), max(Y0, a[1] - m), min(X1, a[2] + m), min(Y1, a[3] + m)
            z = int(max(4, min(8, 560 / max(x1 - x0, y1 - y0))))
            A = cv2.resize(im[y0 - Y0:y1 - Y0, x0 - X0:x1 - X0], None, fx=z, fy=z, interpolation=cv2.INTER_NEAREST)
            B = cv2.resize(col[y0 - Y0:y1 - Y0, x0 - X0:x1 - X0], None, fx=z, fy=z, interpolation=cv2.INTER_NEAREST)
            for q in words:
                P = (np.array(q['poly']) - [x0, y0]) * z
                cv2.polylines(B, [np.round(P).astype(np.int32)], True, (255, 0, 170) if q['target'] else (160, 0, 160), 1)
            for gx in range((x0 // 10 + 1) * 10, x1, 10):
                X = (gx - x0) * z; A[:4 if gx % 50 else 10, X] = (200, 0, 0)
            for gy in range((y0 // 10 + 1) * 10, y1, 10):
                Y = (gy - y0) * z; A[Y, :4 if gy % 50 else 10] = (200, 0, 0)
            t = np.full((A.shape[0] + 20, 2 * A.shape[1] + 8, 3), 255, np.uint8); t[20:, :A.shape[1]] = A; t[20:, A.shape[1] + 8:] = B
            cv2.putText(t, f"{tid} {w['reading']} [{x0},{y0}] x{z} ink {w['ink_px']} text {w['text_px_final']}", (2, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 160), 1)
            panels.append(t)
        H = sum(p.shape[0] + 6 for p in panels); Wd = max(p.shape[1] for p in panels)
        out = np.full((H, Wd, 3), 255, np.uint8); y = 0
        for p in panels: out[y:y + p.shape[0], :p.shape[1]] = p; y += p.shape[0] + 6
        cv2.imwrite(os.path.join(WORK, f'{tid}_zoom.png'), out)
        # the whole window, scan beside truth, 2x
        z = 2 if max(X1 - X0, Y1 - Y0) <= 520 else 1
        A = cv2.resize(im, None, fx=z, fy=z, interpolation=cv2.INTER_NEAREST); B = cv2.resize(col, None, fx=z, fy=z, interpolation=cv2.INTER_NEAREST)
        for q in words:
            P = (np.array(q['poly']) - [X0, Y0]) * z
            cv2.polylines(B, [np.round(P).astype(np.int32)], True, (255, 0, 170) if q['target'] else (160, 0, 160), 1)
            k = P[np.argmin(P[:, 1])]; cv2.putText(B, str(q['annot_line']), (int(k[0]) + 2, int(k[1]) - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.33, (160, 0, 120), 1)
        cv2.imwrite(os.path.join(WORK, f'{tid}_win.jpg'), np.hstack([A, np.full((A.shape[0], 8, 3), 255, np.uint8), B]), [cv2.IMWRITE_JPEG_QUALITY, 92])
        return
    # full crop: 1.5x tiles 500 x 340, scan above truth
    tw, th, sc = 500, 340, 1.5
    for r, ty in enumerate(range(0, Y1 - Y0, th)):
        for cc, tx in enumerate(range(0, X1 - X0, tw)):
            a = im[ty:ty + th, tx:tx + tw]; b = col[ty:ty + th, tx:tx + tw].copy()
            A = cv2.resize(a, None, fx=sc, fy=sc, interpolation=cv2.INTER_CUBIC); B = cv2.resize(b, None, fx=sc, fy=sc, interpolation=cv2.INTER_NEAREST)
            for q in words:
                P = (np.array(q['poly']) - [X0 + tx, Y0 + ty]) * sc
                if P[:, 0].max() < 0 or P[:, 1].max() < 0 or P[:, 0].min() > B.shape[1] or P[:, 1].min() > B.shape[0]: continue
                cv2.polylines(B, [np.round(P).astype(np.int32)], True, (255, 0, 170), 1)
                k = P[np.argmin(P[:, 1])]; cv2.putText(B, str(q['annot_line']), (int(k[0]) + 2, int(k[1]) - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.33, (160, 0, 120), 1)
            for g in range(((X0 + tx) // 50 + 1) * 50, X0 + tx + a.shape[1], 50):
                X = int((g - X0 - tx) * sc); A[:6, X] = (200, 0, 0); B[:6, X] = (200, 0, 0)
                if g % 100 == 0: cv2.putText(A, str(g), (X + 2, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (200, 0, 0), 1)
            for g in range(((Y0 + ty) // 50 + 1) * 50, Y0 + ty + a.shape[0], 50):
                Y = int((g - Y0 - ty) * sc); A[Y, :6] = (200, 0, 0); B[Y, :6] = (200, 0, 0)
                if g % 100 == 0: cv2.putText(A, str(g), (2, Y - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (200, 0, 0), 1)
            cv2.imwrite(os.path.join(WORK, f'{tid}_check_{r}{cc}.jpg'), np.hstack([A, np.full((A.shape[0], 6, 3), 255, np.uint8), B]), [cv2.IMWRITE_JPEG_QUALITY, 92])


if __name__ == '__main__':
    crops = json.load(open(CROPS_PATH, encoding='utf8'))
    ids = [a for a in sys.argv[1:] if not a.startswith('--')]
    if ids == ['all']: ids = sorted(k for k in crops if os.path.exists(os.path.join(TR, 'annot', f'{k}.txt')))
    chk = '--check' in sys.argv; changed = False
    for t in ids:
        rec = build(t, crops, chk)
        if rec['scope'] is not None and crops[t].get('scope') != rec['scope']: crops[t]['scope'] = rec['scope']; changed = True
    if changed: jdump(crops, CROPS_PATH)
