"""TARGETED TRUTH builder (dev_block, 26 Nov 2026): a copy of text_v1/truth-fix/scripts/build_truth_v2.py (truth v2) that
reads dev_block/truth/annot/DB##.txt and writes dev_block/truth/DB##_mask.png, DB##_words.json and the crop's entry in
dev_block/truth/crops.json. The v2 rules (word boxes, snap, line rule, hand ops, shared-ink rule) are unchanged; the
targeted-crop additions are marked "dev".
    cd data/sanborn
    python -B bench_2026-11-26/text_fix/dev_block/scripts/build_dev.py DB01 [DB02 ...] [--check] [--all]

dev additions:
  - a word line with the flag `target` is a target word (here a block number). The crop WINDOW is not typed: it is the
    snapped target box(es) (axis box) grown by WIN_PAD = 60 px, written to crops.json with kind 'targeted', target
    'block', scope_pad 25, the plate's scale and the draw record (candidates/draw.json).
  - SCOPE: each target word's snapped box (its rotated rectangle) grown by SCOPE_PAD = 25 px (a 51 x 51 square). Only the
    scope is scored: outside it the mask is 3 (don't care), paper included.
  - words.json keeps the targets and every word whose box reaches into the scope (flag 'cut_by_scope' when part of it
    lies outside), and records per word its text px, don't-care px and all ink px inside the scope.
  - check pictures: pics/check/DB##_check.png, the scan and the truth side by side at 4x (or less for a big window), the
    scope outlined. They use the scan and the truth only (no bin 8, no finder).
  - the `#plate N` line at the top of an annotation file gives the plate.
The v2 builder's own description follows.

TRUTH V2 builder: a copy of text/inventory/scripts/build_truth.py (25 Nov 2026) that reads text_v1/truth/annot/T#.txt
and writes text_v1/truth/T#_mask.png and T#_words.json (or --out=DIR). Unchanged rules; v2 additions are marked "v2".

Build the hand-checked TEXT TRUTH of a crop from its annotation file (truth/annot/T#.txt), and the check pictures.

Annotation lines (written by eye from 1:1 and 2:1 views of the plate, full-plate pixel coordinates):
  x1 y1 x2 y2 h | reading | kind [| flags]
      a word or number: its centre line from the middle of the first glyph's leading edge to the middle of the last
      glyph's trailing edge, in reading order (so the angle is the reading direction: 0 left to right, 90 reading
      downwards, -90 reading upwards), h the glyph height. Rough to about 10 px; it is snapped (below).
      flags: nosnap (keep the box as typed), partial (cut by the crop edge or partly unreadable), curved
  EXCL x0 y0 x1 y1 [note]   ink in this box is NOT text, whatever the words say (a dash, a hook mark under a word)
  FORCE x0 y0 x1 y1 [note]  ink in this box IS text (a glyph the word box misses)
  CARE x0 y0 x1 y1 [note]   ink in this box is "don't care" (3)
  CAREDIR x0 y0 x1 y1 angle len [note]  inside the box, text ink on a straight run of len px or more within 10 degrees
      of angle (rail, street and dashed lines through a big glyph) becomes don't care
  CARELINE x1 y1 x2 y2 w [note]  a dashed line crossing glyphs: the text ink within this strip (w px wide) becomes don't care
  v2 additions:
  NOTTEXT x1 y1 x2 y2 w [note]   all ink in this strip is not text (a lot line through a word box)
  FORCELINE x1 y1 x2 y2 w [note] all ink in this strip is text (a stroke the line rule took)
  EXCLCIRC cx cy r [note]         all ink in this circle is not text (hydrant dots, manhole and valve marks)
  The ops act in the order they are written, after all the words. Then (v2) the shared-ink rule: in each ink piece that
  holds text and non-text ink, the ink of either within 2 px of the other becomes don't care (share_rule; --noshare off).
  # comment
Kinds: street (street, avenue, alley, place names), house (house numbers), lotdim (lot dimensions, bearings, areas),
  lot (auditor's and actual lot numbers), block (block numbers), owner (owner, estate and subdivision names, firms),
  bldg (building names and notes), story (story heights and building letters inside buildings), pipe (water pipe
  labels), sewer (sewer labels), rail (railroad names), adj (adjoining sheet numbers), ditto (ditto marks), other.

Snap: the typed box is widened by 0.15 h + 3 px across and 0.15 h + 4 px along; the text candidate ink (ink less
straight runs of max(41, 1.5 h) px or more, found in the word's neighbourhood) whose pieces lie at least 70% inside the
widened box gives the tight box along the typed angle, but no side is trimmed by more than 0.25 h along or 0.2 h across
(a glyph joined to a short line is not a candidate and must not be cut off). So a snap trims the typed box a little or
grows it a little.

Mask (truth/T#_mask.png, size of the crop window): 0 paper, 1 ink that is not text, 2 text ink, 3 don't care: ink
where a glyph and a line share pixels (line ink within 2 px of glyph ink, inside the word box) and CARE boxes.
Text ink = ink inside a snapped word box (grown by 1.5 px each side) that is not on, or within 2 px of, a straight run
(as above) reaching more than 4 px outside the box. Short non-text marks inside a box (an outline stub, a dash) are removed by EXCL boxes
found on the check pictures.
Words (truth/T#_words.json): every word with its reading, kind, rotated box (4 corners), axis box, angle, height."""
import sys, os, json, math, re
import numpy as np, cv2
sys.dont_write_bytecode = True
from common import INV, window, line_mask, rrect_poly, jdump, plate_img

TR = os.path.join(INV, 'truth'); WORK = os.path.join(INV, 'pics', 'check'); os.makedirs(WORK, exist_ok=True)
OUT = next((a.split('=', 1)[1] for a in sys.argv if a.startswith('--out=')), TR)   # v2: where the mask and words go
PAD = 120
WIN_PAD, SCOPE_PAD = 60, 25   # dev: crop window = target box + 60 px; scored scope = target box + 25 px
SCALES = {k: v['ft_per_inch'] for k, v in json.load(open(os.path.join(INV, '..', '..', '..', 'scale_table.json'))).items()}
DRAW = json.load(open(os.path.join(INV, 'candidates', 'draw.json'), encoding='utf8'))
KINDS = {'street', 'house', 'lotdim', 'lot', 'block', 'owner', 'bldg', 'story', 'pipe', 'sewer', 'rail', 'adj', 'ditto', 'other'}


PLATE = {}


def parse(tid):
    words, boxes = [], []
    for k, raw in enumerate(open(os.path.join(TR, 'annot', f'{tid}.txt'), encoding='utf8')):
        s = raw.strip()
        if s.startswith('#plate'): PLATE[tid] = s.split()[1]; continue   # dev
        if not s or s.startswith('#'): continue
        if s.split()[0] in ('EXCL', 'FORCE', 'CARE'):
            f = s.split(); boxes.append(dict(op=f[0], box=[int(v) for v in f[1:5]], note=' '.join(f[5:]), line=k + 1)); continue
        if s.split()[0] == 'CAREDIR':
            f = s.split(); boxes.append(dict(op=f[0], box=[int(v) for v in f[1:5]], angle=float(f[5]), length=int(f[6]), note=' '.join(f[7:]), line=k + 1)); continue
        if s.split()[0] == 'EXCLCIRC':   # v2: a round symbol (hydrant, manhole): ink in the circle is not text
            f = s.split(); boxes.append(dict(op=f[0], circ=[float(v) for v in f[1:4]], note=' '.join(f[4:]), line=k + 1)); continue
        if s.split()[0] in ('CARELINE', 'NOTTEXT', 'FORCELINE'):   # v2: NOTTEXT and FORCELINE are strips like CARELINE
            f = s.split(); boxes.append(dict(op=f[0], seg=[int(v) for v in f[1:5]], width=int(f[5]), note=' '.join(f[6:]), line=k + 1)); continue
        parts = [q.strip() for q in s.split('|')]
        g = [float(v) for v in parts[0].split()]
        if len(g) != 5: raise SystemExit(f'{tid} line {k + 1}: need x1 y1 x2 y2 h: {s}')
        kind = parts[2]
        if kind not in KINDS: raise SystemExit(f'{tid} line {k + 1}: unknown kind {kind}')
        flags = parts[3].split() if len(parts) > 3 else []
        words.append(dict(geo=g, reading=parts[1], kind=kind, flags=flags, line=k + 1))
    return words, boxes


def in_rect(xs, ys, cx, cy, L, h, ang):
    a = math.radians(ang); u = (math.cos(a), math.sin(a)); v = (-math.sin(a), math.cos(a))
    dx, dy = xs - cx, ys - cy; al = dx * u[0] + dy * u[1]; ac = dx * v[0] + dy * v[1]
    return (np.abs(al) <= L / 2) & (np.abs(ac) <= h / 2), al, ac


SHARE = '--noshare' not in sys.argv
SHARE_PX = 2


def share_rule(ink, text, care):
    """v2 convention (Ben's default, 25 Nov 2026): where a glyph touches a line or another non-text mark, the ink they
    share is don't care. In every 8-connected ink piece that holds both text and non-text ink, the non-text ink within
    SHARE_PX px of text ink and the text ink within SHARE_PX px of non-text ink become don't care (3). Pieces that do
    not touch are left alone. In place on text and care."""
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


def typed_poly(w):
    x1, y1, x2, y2, h = w['geo']
    return rrect_poly((x1 + x2) / 2, (y1 + y2) / 2, math.hypot(x2 - x1, y2 - y1), h, math.degrees(math.atan2(y2 - y1, x2 - x1)))


def build(tid, check=False):
    words, boxes = parse(tid); p = PLATE[tid]   # dev: the plate comes from the annotation, the window from the targets
    tg = [w for w in words if 'target' in w['flags']]
    if not tg: raise SystemExit(f'{tid}: no target word')
    q = np.vstack([typed_poly(w) for w in tg]); slack = WIN_PAD + 40
    RX0, RY0, RX1, RY1 = int(q[:, 0].min()) - slack, int(q[:, 1].min()) - slack, int(q[:, 0].max()) + slack, int(q[:, 1].max()) + slack
    img, lab, ink, (wx0, wy0, wx1, wy1) = window(p, RX0 - PAD, RY0 - PAD, RX1 + PAD, RY1 + PAD)
    hh, ww = ink.shape
    text = np.zeros_like(ink); care = np.zeros_like(ink); notes = []
    yy, xx = np.mgrid[0:hh, 0:ww]
    out_words = []
    for i, w in enumerate(words):
        x1, y1, x2, y2, h = w['geo']; ang = math.degrees(math.atan2(y2 - y1, x2 - x1)); L = math.hypot(x2 - x1, y2 - y1)
        cx, cy = (x1 + x2) / 2 - wx0, (y1 + y2) / 2 - wy0
        Lline = int(max(41, round(1.5 * h))) | 1     # a straight run half again as long as the glyphs are tall is a line, not a stroke (a figure 1 is not)
        R = int(L / 2 + h + Lline + 10)
        bx0, by0, bx1, by1 = max(0, int(cx - R)), max(0, int(cy - R)), min(ww, int(cx + R)), min(hh, int(cy + R))
        sub_ink = ink[by0:by1, bx0:bx1]
        sub_ln = line_mask(sub_ink, Lline, nang=72)
        X = xx[by0:by1, bx0:bx1].astype(float); Y = yy[by0:by1, bx0:bx1].astype(float)
        mg_a, mg_c = 0.15 * h + 4, 0.15 * h + 3     # the snap may move each side of the typed box this far
        snapped = False
        if 'nosnap' not in w['flags']:
            cand = sub_ink & ~(cv2.dilate(sub_ln.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0)   # the ragged edge of a line too
            n, lb, st, _ = cv2.connectedComponentsWithStats(cand.astype(np.uint8), connectivity=8)
            inw, al, ac = in_rect(X, Y, cx, cy, L + 2 * mg_a, h + 2 * mg_c, ang)
            tot = np.bincount(lb.ravel(), minlength=n); ins = np.bincount(lb.ravel(), inw.ravel(), minlength=n)
            ok = (ins >= 0.7 * tot) & (tot >= 3); ok[0] = False
            sel = ok[lb] & inw
            if sel.sum() >= 8:
                a1, c1 = al[sel], ac[sel]
                lo, hi, clo, chi = a1.min(), a1.max(), c1.min(), c1.max()
                # never trim more than 0.25 h off a typed side: a glyph joined to a line (left out above) keeps its place
                s_a, s_c = 0.25 * h, 0.2 * h
                lo, hi = min(lo, -L / 2 + s_a), max(hi, L / 2 - s_a); clo, chi = min(clo, -h / 2 + s_c), max(chi, h / 2 - s_c)
                a = math.radians(ang); u = np.array([math.cos(a), math.sin(a)]); v = np.array([-math.sin(a), math.cos(a)])
                ctr = np.array([cx, cy]) + u * (lo + hi) / 2 + v * (clo + chi) / 2
                cx, cy = ctr; L = hi - lo + 2; h = chi - clo + 2; snapped = True
            else:
                notes.append(f'{tid} line {w["line"]} {w["reading"]!r}: nothing to snap to')
        inw, al, ac = in_rect(X, Y, cx, cy, L + 3, h + 3, ang)
        # line ink in the box that reaches outside it: not text
        n, lb, st, _ = cv2.connectedComponentsWithStats(sub_ln.astype(np.uint8), connectivity=8)
        outside = np.bincount(lb.ravel(), (~in_rect(X, Y, cx, cy, L + 8, h + 8, ang)[0]).ravel(), minlength=n) > 0; outside[0] = False
        lpx = (cv2.dilate(outside[lb].astype(np.uint8), np.ones((5, 5), np.uint8)) > 0) & sub_ink   # with the line's ragged edge (2 px)
        t = sub_ink & inw & ~lpx
        ov = lpx & inw & (cv2.dilate(t.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0)
        text[by0:by1, bx0:bx1] |= t; care[by0:by1, bx0:bx1] |= ov
        poly = rrect_poly(cx + wx0, cy + wy0, L, h, ang)
        # touching: the glyph ink is joined (8-connected, through ink) to line ink that reaches outside the box
        tl = bool((cv2.dilate(t.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0)[lpx].any())
        out_words.append(dict(id=f'{tid}-{i + 1:03d}', reading=w['reading'], kind=w['kind'], flags=w['flags'], angle=round(ang, 1),
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
            if b['op'] == 'CARELINE': care |= text & st_; text &= ~st_      # a dashed line through glyphs: what the words called text along it becomes don't care
            elif b['op'] == 'NOTTEXT': text &= ~st_; care &= ~st_          # v2: all ink in the strip is not text (a lot line through a word box)
            else: text |= ink & st_; care &= ~st_                          # v2 FORCELINE: all ink in the strip is text (a stroke along a line)
            continue
        x0_, y0_, x1_, y1_ = b['box']; s = (slice(max(0, y0_ - wy0), max(0, y1_ - wy0)), slice(max(0, x0_ - wx0), max(0, x1_ - wx0)))
        if b['op'] == 'CAREDIR':   # straight runs at about this angle (rail and street lines, dashes) through a big glyph
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
    if SHARE: share_rule(ink, text, care)   # v2 convention: shared ink where text touches other ink is don't care
    # dev: the window is the snapped target boxes grown by WIN_PAD, clipped to the plate
    H_, W_ = plate_img(p).shape[:2]
    tq = np.vstack([np.array(w['poly']) for w in out_words if 'target' in w['flags']])
    X0, Y0 = max(0, int(math.floor(tq[:, 0].min())) - WIN_PAD), max(0, int(math.floor(tq[:, 1].min())) - WIN_PAD)
    X1, Y1 = min(W_, int(math.ceil(tq[:, 0].max())) + WIN_PAD), min(H_, int(math.ceil(tq[:, 1].max())) + WIN_PAD)
    assert X0 >= wx0 and Y0 >= wy0 and X1 <= wx1 and Y1 <= wy1, (tid, (X0, Y0, X1, Y1), (wx0, wy0, wx1, wy1))
    oy, ox = Y0 - wy0, X0 - wx0
    sl = (slice(oy, oy + (Y1 - Y0)), slice(ox, ox + (X1 - X0)))
    M = np.zeros((Y1 - Y0, X1 - X0), np.uint8); I = ink[sl]
    M[I] = 1; M[I & text[sl]] = 2; M[I & care[sl]] = 3
    # dev: the scope (target boxes grown by SCOPE_PAD); outside it everything is don't care
    scope = np.zeros(M.shape, np.uint8)
    for w in out_words:
        if 'target' in w['flags']: cv2.fillPoly(scope, [np.round(np.array(w['poly']) - [X0, Y0]).astype(np.int32)], 1)
    scope = cv2.dilate(scope, np.ones((2 * SCOPE_PAD + 1, 2 * SCOPE_PAD + 1), np.uint8)) > 0
    M[~scope] = 3
    os.makedirs(OUT, exist_ok=True); cv2.imwrite(os.path.join(OUT, f'{tid}_mask.png'), M)
    keep = []
    for w in out_words:
        pm = np.zeros(M.shape, np.uint8); cv2.fillPoly(pm, [np.round(np.array(w['poly']) - [X0, Y0]).astype(np.int32)], 1); pm = pm > 0
        if not (pm & scope).any(): continue
        if (pm & ~scope).any() and 'target' not in w['flags']: w['flags'] = w['flags'] + ['cut_by_scope']
        w['in_scope'] = dict(text_px=int((pm & (M == 2)).sum()), dont_care_px=int((pm & scope & (M == 3)).sum()), ink_px=int((pm & scope & I).sum()))
        if 'target' in w['flags']: w['target'] = True; w['ink_size_px'] = w['in_scope']['text_px'] + w['in_scope']['dont_care_px']
        keep.append(w)
    sc = SCALES.get(p)
    draw = next((dict(plate=N, seed=v['seed'], order_pos=v['order'].index(k['i']), candidate=k) for N, v in DRAW['plates'].items() for k in v['picks'] if k.get('id') == tid), None)
    crop = dict(plate=p, win=[X0, Y0, X1, Y1], scale_ft_per_inch=sc, kind='targeted', target='block', scope_pad=SCOPE_PAD, win_pad=WIN_PAD,
                targets=[w['id'] for w in keep if w.get('target')], readings=[w['reading'] for w in keep if w.get('target')],
                why=f"block number {', '.join(w['reading'] for w in keep if w.get('target'))} on plate {p} ({sc} ft), drawn at random (candidates/draw.json)", draw=draw)
    rec = dict(crop=tid, plate=p, win=[X0, Y0, X1, Y1], why=crop['why'], n_words=len(keep), mask=f'{tid}_mask.png',
               mask_values={'0': 'paper (in scope)', '1': 'ink, not text (in scope)', '2': 'text ink (in scope)', '3': "don't care (glyph and line share ink; CARE boxes; everything outside the scope)"},
               counts={k: int((M == v).sum()) for k, v in (('paper', 0), ('ink_not_text', 1), ('text', 2), ('dont_care', 3))},
               scope_px=int(scope.sum()), scope_counts={k: int(((M == v) & scope).sum()) for k, v in (('paper', 0), ('ink_not_text', 1), ('text', 2), ('dont_care', 3))},
               boxes=boxes, words=keep)
    jdump(rec, os.path.join(OUT, f'{tid}_words.json'))
    cf = os.path.join(OUT, 'crops.json'); C = json.load(open(cf, encoding='utf8')) if os.path.exists(cf) else {}
    C[tid] = crop; jdump(dict(sorted(C.items())), cf)
    t = [w for w in keep if w.get('target')]
    print(tid, p, sc, 'win', [X0, Y0, X1, Y1], len(keep), 'words', 'scope', rec['scope_counts'], 'targets', [(w['reading'], w['in_scope']) for w in t])
    for s_ in notes: print('  ', s_)
    if check: render(tid, plate_img(p)[Y0:Y1, X0:X1], M, keep, (X0, Y0), scope)


def render(tid, im, M, words, org, scope):
    """dev check picture: the scan (left) and the truth (right: text red, not text blue, don't care orange, paper faded),
    at 4x (less for a big window), a 10 px grid labelled every 50 px, word boxes magenta with their annotation line, the
    scope outlined green; ink outside the scope pale blue. Scan and truth only."""
    X0, Y0 = org; h, w = M.shape; sc = min(4.0, 760 / max(h, w))
    o = (im.astype(np.float32) * 0.35 + 255 * 0.65).astype(np.uint8)
    for v, col in {1: (200, 90, 0), 2: (0, 0, 230), 3: (0, 160, 255)}.items(): o[(M == v) & scope] = col
    o[~scope & (cv2.cvtColor(im, cv2.COLOR_BGR2LAB)[..., 0] < 140)] = (230, 200, 170)
    A = cv2.resize(im, None, fx=sc, fy=sc, interpolation=cv2.INTER_NEAREST); B = cv2.resize(o, None, fx=sc, fy=sc, interpolation=cv2.INTER_NEAREST)
    for P_ in (A, B):
        for gx in range((X0 // 10 + 1) * 10, X0 + w, 10):
            X = int((gx - X0) * sc); P_[:, X] = (P_[:, X].astype(int) * 3 // 4 + np.array([0, 0, 160]) // 4).astype(np.uint8) if gx % 50 else (P_[:, X].astype(int) // 2 + np.array([0, 0, 160]) // 2).astype(np.uint8)
        for gy in range((Y0 // 10 + 1) * 10, Y0 + h, 10):
            Y = int((gy - Y0) * sc); P_[Y, :] = (P_[Y, :].astype(int) * 3 // 4 + np.array([0, 0, 160]) // 4).astype(np.uint8) if gy % 50 else (P_[Y, :].astype(int) // 2 + np.array([0, 0, 160]) // 2).astype(np.uint8)
        for gx in range((X0 // 50 + 1) * 50, X0 + w, 50): cv2.putText(P_, str(gx), (int((gx - X0) * sc) + 2, 11), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (0, 0, 200), 1)
        for gy in range((Y0 // 50 + 1) * 50, Y0 + h, 50): cv2.putText(P_, str(gy), (2, int((gy - Y0) * sc) - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (0, 0, 200), 1)
    cs, _ = cv2.findContours(cv2.resize(scope.astype(np.uint8), None, fx=sc, fy=sc, interpolation=cv2.INTER_NEAREST), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(B, cs, -1, (0, 170, 0), 1)
    for w_ in words:
        q = (np.array(w_['poly']) - [X0, Y0]) * sc
        cv2.polylines(B, [np.round(q).astype(np.int32)], True, (220, 0, 220), 1)
        k = q[np.argmin(q[:, 1])]; cv2.putText(B, str(w_['annot_line']), (int(k[0]) + 2, int(k[1]) - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (150, 0, 150), 1)
    cv2.imwrite(os.path.join(WORK, f'{tid}_check.png'), np.hstack([A, np.full((A.shape[0], 6, 3), 255, np.uint8), B]))


if __name__ == '__main__':
    chk = '--check' in sys.argv
    ids = [a for a in sys.argv[1:] if not a.startswith('--')]
    if '--all' in sys.argv: ids = sorted(f[:-4] for f in os.listdir(os.path.join(TR, 'annot')) if f.endswith('.txt'))
    for t in ids: build(t, chk)
