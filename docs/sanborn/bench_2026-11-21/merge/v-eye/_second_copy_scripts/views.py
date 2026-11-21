"""merge/v-eye: overlays of the four outline steps for the eye check (21 Nov 2026). Writes only into merge/v-eye/.

    python -B views.py thumbs [N ...]                    -> thumbs/N.jpg (batch above, merged below, thumbs.py's conventions)
                                                            thumbs/N_4.jpg (2 x 2: batch, A, B, merged)
    python -B views.py crop N X0 Y0 [SIZE] [NAME] [--only merged,B]   -> crops/N_NAME.jpg, full resolution, 2 x 2 (or the variants named)

Variants and what the line editor gets of each (its step 4):
  batch   picks22_guided/22-N/outlines.json (44: outline-nesting/runs_plates/legacy/44), repo step 4: drop short, paper_edge
  A       outline-quality's proposal, run here (runs/A/N), its step 4: drop short, paper_edge, 'not on a line'
  B       outline-nesting's final (outline-nesting/runs_plates/final/N), its step 4: drop short, paper_edge;
          off-map hatched from visual-pdf/maparea_check/N_mask8.png
  merged  the staged merge, run here (runs/merged/N), staged step 4 (drop short, paper_edge, 'not on a line', 'on rail');
          off-map hatched from runs/merged/N/N_mapground.png
Colours (BGR as thumbs.py): green 'on print' (editor green), orange other exported, cyan hole sides, light grey polygon
outline, red outline of a block covering > 30% of the map ground, grey hatching off the map ground. Added here:
magenta (thin) a merged side dropped as 'on rail'; dark red (thin, crops only) a side dropped as 'not on a line';
a black core line in a bridging side (crops only).
"""
import json, os, re, sys
import numpy as np
import cv2
import common as C
D = C.DATA; U = C.U; OUT = C.ME
WPANEL = 1150
MASKS_B = C.BENCH + 'visual-pdf/maparea_check/'


def src(n, v):
    if v == 'batch': return (C.BENCH + 'outline-nesting/runs_plates/legacy/44/outlines.json') if n in C.GUIDED else D + f'picks22_guided/22-{n}/outlines.json'
    if v == 'A': return OUT + f'runs/A/{n}/outlines.json'
    if v == 'B': return C.BENCH + f'outline-nesting/runs_plates/final/{n}/outlines.json'
    if v == 'merged': return OUT + f'runs/merged/{n}/outlines.json'


def keep(v, s):
    st = s['state']
    if st == 'short' or s.get('paper_edge'): return False
    if v in ('A', 'merged') and st == 'not on a line': return False
    if v == 'merged' and st == 'on rail': return False
    return True


def exported(v, polys):
    """(side, is_hole) for what the line editor gets"""
    return [(s, bool(p and p[0].get('hole'))) for p in polys for s in p if keep(v, s)]


def mapmask(n, v, shape):
    f = {'B': MASKS_B + f'{n}_mask8.png', 'merged': OUT + f'runs/merged/{n}/{n}_mapground.png'}.get(v)
    if f and os.path.exists(f): return cv2.resize(cv2.imread(f, 0), (shape[1], shape[0]), interpolation=cv2.INTER_NEAREST) > 127
    return None


def header(im, text, h=30, scale=0.6):
    cv2.rectangle(im, (0, 0), (im.shape[1], h), (255, 255, 255), -1)
    cv2.putText(im, text, (6, int(h * 0.73)), cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 0, 0), 1, cv2.LINE_AA)


def counts(n, v, polys):
    ex = exported(v, polys); blocks = [p for p in polys if p and not p[0].get('hole')]; holes = [p for p in polys if p and p[0].get('hole')]
    g = sum(1 for s, _ in ex if s['state'] == 'on print'); rail = sum(1 for p in polys for s in p if s['state'] == 'on rail' and not s.get('paper_edge'))
    rep = {}
    f = {'merged': OUT + f'runs/merged/{n}/{n}_outlines.json', 'B': C.BENCH + f'outline-nesting/runs_plates/final/{n}/{n}_outlines.json'}.get(v)
    if f and os.path.exists(f): rep = json.load(open(f, encoding='utf8'))
    t = f"{n} {v}: {len(blocks)} blocks, {len(holes)} holes, {len(ex)} exported, green {g / max(1, len(ex)):.2f}"
    if v == 'merged': t += f", on rail dropped {rail}, bridges {sum('bridge' in s for s, _ in ex)}"
    if rep.get('suspect'): t += ' SUSPECT ' + ' '.join(w.split()[0] for w in rep.get('suspect_why', []))
    return t


def panel(base, polys, k, title, v, mm=None):
    im = base.copy(); rng = np.random.default_rng(1)
    if mm is not None:
        off = ~mm; yy, xx = np.indices(off.shape); hatch = (xx + yy) % 8 < 2
        im[off] = (im[off] * 0.6 + 70).astype(np.uint8); im[off & hatch] = (120, 120, 120)
    ov = im.copy(); blocks = [p for p in polys if p and not p[0].get('hole')]; areas = []
    for p in blocks:
        r = (np.array([s['a'] for s in p]) * k).round().astype(np.int32)
        if len(r) >= 3: cv2.fillPoly(ov, [r], tuple(int(c) for c in rng.integers(90, 255, 3))); areas.append((cv2.contourArea(r.astype(np.float32)), r))
    im = cv2.addWeighted(ov, 0.35, im, 0.65, 0)
    for p in blocks:
        r = (np.array([s['a'] for s in p]) * k).round().astype(np.int32)
        if len(r) >= 3: cv2.polylines(im, [r], True, (110, 110, 110), 1, cv2.LINE_AA)
    mapa = float(mm.sum()) if mm is not None else None
    if areas:
        a, r = max(areas, key=lambda t: t[0])
        if a > 0.3 * (mapa or im.shape[0] * im.shape[1] * 0.85): cv2.polylines(im, [r], True, (0, 0, 255), 2, cv2.LINE_AA)
    P = lambda q: tuple((np.array(q) * k).round().astype(int))
    if v == 'merged':
        for p in polys:
            for s in p:
                if s['state'] == 'on rail' and not s.get('paper_edge'): cv2.line(im, P(s['a']), P(s['b']), (255, 0, 255), 1, cv2.LINE_AA)
    for s, hole in exported(v, polys):
        col = (255, 255, 0) if hole else ((0, 170, 0) if s['state'] == 'on print' else (0, 140, 255))
        cv2.line(im, P(s['a']), P(s['b']), col, 2, cv2.LINE_AA)
    header(im, title)
    return im


def thumbs(n):
    full = cv2.imread(D + f'cufp/22-{n}.jpg', cv2.IMREAD_REDUCED_COLOR_8); H8, W8 = full.shape[:2]
    k = WPANEL / (W8 * 8); base = cv2.resize(full, (WPANEL, int(round(H8 * 8 * k))), interpolation=cv2.INTER_AREA); base = (base * 0.6 + 90).astype(np.uint8)
    P = {}
    for v in ('batch', 'A', 'B', 'merged'):
        polys = json.load(open(src(n, v), encoding='utf8'))
        P[v] = panel(base, polys, k, counts(n, v, polys), v, mapmask(n, v, base.shape))
    os.makedirs(OUT + 'thumbs', exist_ok=True)
    sep = np.full((6, WPANEL, 3), 255, np.uint8)
    cv2.imwrite(OUT + f'thumbs/{n}.jpg', np.vstack([P['batch'], sep, P['merged']]), [cv2.IMWRITE_JPEG_QUALITY, 82])
    vs = np.full((P['A'].shape[0], 6, 3), 255, np.uint8)
    cv2.imwrite(OUT + f'thumbs/{n}_4.jpg', np.vstack([np.hstack([P['batch'], vs, P['A']]), np.full((6, 2 * WPANEL + 6, 3), 255, np.uint8), np.hstack([P['B'], vs, P['merged']])]), [cv2.IMWRITE_JPEG_QUALITY, 82])


def crop_panel(img, polys, v, x0, y0, S, mm, title, lw=3):
    im = img.copy()
    if mm is not None:
        off = ~mm; yy, xx = np.indices(off.shape); hatch = (xx + yy) % 16 < 3
        im[off] = (im[off] * 0.7 + 50).astype(np.uint8); im[off & hatch] = (120, 120, 120)
    P = lambda q: (int(round(q[0] - x0)), int(round(q[1] - y0)))
    for p in polys:
        if p and not p[0].get('hole') and len(p) >= 3:
            cv2.polylines(im, [np.array([P(s['a']) for s in p], np.int32)], True, (150, 150, 150), 1, cv2.LINE_AA)
    for p in polys:
        for s in p:
            if s.get('paper_edge') or s['state'] == 'short': continue
            if v == 'merged' and s['state'] == 'on rail': cv2.line(im, P(s['a']), P(s['b']), (255, 0, 255), 2, cv2.LINE_AA)
            elif v in ('A', 'merged') and s['state'] == 'not on a line': cv2.line(im, P(s['a']), P(s['b']), (0, 0, 140), 1, cv2.LINE_AA)
    for s, hole in exported(v, polys):
        col = (255, 255, 0) if hole else ((0, 170, 0) if s['state'] == 'on print' else (0, 140, 255))
        cv2.line(im, P(s['a']), P(s['b']), col, lw, cv2.LINE_AA)
        if 'bridge' in s: cv2.line(im, P(s['a']), P(s['b']), (0, 0, 0), 1, cv2.LINE_AA)
        for q in (s['a'], s['b']): cv2.circle(im, P(q), 3, (40, 40, 40), -1)
    header(im, title, 26, 0.55)
    return im


_full = {}


def scan(n):
    if n not in _full: _full[n] = cv2.imread(D + f'cufp/22-{n}.jpg')
    return _full[n]


def crop(n, x0, y0, S=1000, name=None, only=('batch', 'A', 'B', 'merged'), polys_cache={}):
    full = scan(n); H, W = full.shape[:2]; x0 = int(max(0, min(W - S, x0))); y0 = int(max(0, min(H - S, y0)))
    img = full[y0:y0 + S, x0:x0 + S]; img = (img * 0.75 + 60).astype(np.uint8)
    tiles = []
    for v in only:
        key = (n, v)
        if key not in polys_cache: polys_cache[key] = json.load(open(src(n, v), encoding='utf8'))
        mm = mapmask(n, v, (H, W)); mm = mm[y0:y0 + S, x0:x0 + S] if mm is not None else None
        tiles.append(crop_panel(img, polys_cache[key], v, x0, y0, S, mm, f'{n} {v}  x{x0} y{y0} ({S} px)'))
    if len(tiles) == 4:
        sv = np.full((S, 6, 3), 255, np.uint8); sh = np.full((6, 2 * S + 6, 3), 255, np.uint8)
        out = np.vstack([np.hstack([tiles[0], sv, tiles[1]]), sh, np.hstack([tiles[2], sv, tiles[3]])])
    else:
        out = np.hstack([t if i == 0 else np.hstack([np.full((S, 6, 3), 255, np.uint8), t]) for i, t in enumerate(tiles)])
    os.makedirs(OUT + 'crops', exist_ok=True); f = OUT + f'crops/{n}_{name or f"{x0}_{y0}"}.jpg'
    cv2.imwrite(C.must_be_mine(f), out, [cv2.IMWRITE_JPEG_QUALITY, 88]); return f


if __name__ == '__main__':
    a = sys.argv[1:]
    if a[0] == 'thumbs':
        for n in a[1:] or C.PLATES: thumbs(n); print(n, flush=True)
    elif a[0] == 'crop':
        only = tuple(a[a.index('--only') + 1].split(',')) if '--only' in a else ('batch', 'A', 'B', 'merged')
        if '--only' in a: i = a.index('--only'); del a[i:i + 2]
        n, x0, y0 = a[1], int(a[2]), int(a[3]); S = int(a[4]) if len(a) > 4 else 1000; name = a[5] if len(a) > 5 else None
        print(crop(n, x0, y0, S, name, only))
