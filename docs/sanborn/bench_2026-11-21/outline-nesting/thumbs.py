"""Before/after overlay thumbnails, for checking the outline-nesting change by eye.

    python thumbs.py [VARIANT] [N ...]     (default VARIANT new; plates: every plate with a run)  -> thumbs/N.jpg

Top: the batch (as measure.py takes it). Bottom: runs_plates/VARIANT/N. Each panel is the scan at about 1/9 size, darkened:
  block polygons filled with a light random colour (a merge or a nested block shows as one colour patch),
  exported sides (step 4) green (on print) or orange, hole sides cyan, the largest block's outline red when it covers more
  than 30% of the map ground; bottom panel: off-map ground (map_area.py mask) hatched grey.
"""
import json, os, re, sys
import numpy as np
import cv2
HERE = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/') + '/'
D = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; U = D + 'unet_data/'
GUIDED = {'43', '44', '45', '80', '82A'}; MASKS = D + 'bench_2026-11-21/visual-pdf/maparea_check/'
WPANEL = 1150


def step4(polys): return [(s, bool(p and p[0].get('hole'))) for p in polys for s in p if not (s['state'] == 'short' or s.get('paper_edge'))]


def panel(base, polys, k, title, mapmask=None):
    im = base.copy(); ov = im.copy(); rng = np.random.default_rng(1)
    if mapmask is not None:
        off = ~mapmask; hatch = np.zeros(off.shape, bool); yy, xx = np.indices(off.shape); hatch[(xx + yy) % 8 < 2] = True
        im[off] = (im[off] * 0.6 + 70).astype(np.uint8); im[off & hatch] = (120, 120, 120); ov = im.copy()
    blocks = [p for p in polys if not (p and p[0].get('hole'))]
    areas = []
    for p in blocks:
        r = (np.array([s['a'] for s in p]) * k).round().astype(np.int32)
        if len(r) >= 3: cv2.fillPoly(ov, [r], tuple(int(c) for c in rng.integers(90, 255, 3))); areas.append((cv2.contourArea(r.astype(np.float32)), r))
    im = cv2.addWeighted(ov, 0.35, im, 0.65, 0)
    for p in blocks:
        r = (np.array([s['a'] for s in p]) * k).round().astype(np.int32)
        if len(r) >= 3: cv2.polylines(im, [r], True, (110, 110, 110), 1, cv2.LINE_AA)
    mapa = float(mapmask.sum()) if mapmask is not None else None
    if areas:
        a, r = max(areas, key=lambda t: t[0])
        if a > 0.3 * (mapa or im.shape[0] * im.shape[1] * 0.85): cv2.polylines(im, [r], True, (0, 0, 255), 2, cv2.LINE_AA)
    for s, hole in step4(polys):
        col = (255, 255, 0) if hole else ((0, 170, 0) if s['state'] == 'on print' else (0, 140, 255))
        cv2.line(im, tuple((np.array(s['a']) * k).round().astype(int)), tuple((np.array(s['b']) * k).round().astype(int)), col, 2, cv2.LINE_AA)
    cv2.rectangle(im, (0, 0), (im.shape[1], 30), (255, 255, 255), -1); cv2.putText(im, title, (6, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1, cv2.LINE_AA)
    return im


def one(n, variant, M):
    full = cv2.imread(D + f'cufp/22-{n}.jpg', cv2.IMREAD_REDUCED_COLOR_8); H8, W8 = full.shape[:2]
    k = WPANEL / (W8 * 8); base = cv2.resize(full, (WPANEL, int(round(H8 * 8 * k))), interpolation=cv2.INTER_AREA); base = (base * 0.6 + 90).astype(np.uint8)
    bp = HERE + f'runs_plates/legacy/{n}/outlines.json' if n in GUIDED else D + f'picks22_guided/22-{n}/outlines.json'
    vp = HERE + f'runs_plates/{variant}/{n}/outlines.json'
    if not (os.path.exists(bp) and os.path.exists(vp)): return False
    mm = None
    if os.path.exists(MASKS + f'{n}_mask8.png'): mm = cv2.resize(cv2.imread(MASKS + f'{n}_mask8.png', 0), (base.shape[1], base.shape[0]), interpolation=cv2.INTER_NEAREST) > 127
    row = M.get(n, {}); b = row.get('batch', {}); v = row.get(variant, {})
    def t(x, name): return (f"{n} {name}: {x.get('blocks')} blocks, {x.get('holes', 0)} holes, {x.get('exported')} exported, {x.get('editor_lines')} editor lines, green {x.get('green_share')}, "
                            f"largest {x.get('largest_map')} of map" + (f", SUSPECT {x.get('why')}" if x.get('suspect') else ''))
    top = panel(base, json.load(open(bp, encoding='utf8')), k, t(b, 'batch'), None)
    bot = panel(base, json.load(open(vp, encoding='utf8')), k, t(v, variant), mm)
    os.makedirs(HERE + 'thumbs', exist_ok=True)
    cv2.imwrite(HERE + f'thumbs/{n}_{variant}.jpg', np.vstack([top, np.full((6, WPANEL, 3), 255, np.uint8), bot]), [cv2.IMWRITE_JPEG_QUALITY, 82])
    return True


if __name__ == '__main__':
    a = sys.argv[1:]; variant = a.pop(0) if a and not a[0][0].isdigit() else 'new'
    M = json.load(open(HERE + 'measure.json')) if os.path.exists(HERE + 'measure.json') else {}
    pl = a or sorted(os.listdir(HERE + f'runs_plates/{variant}'), key=lambda s: (int(re.match(r'\d+', s).group()), s) if s[0].isdigit() else (9999, s))
    for n in pl:
        if n[0].isdigit(): print(n, one(n, variant, M), flush=True)
