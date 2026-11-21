"""Montage of full-size crops for checking by eye (rail-rules, 21 Nov 2026). Read-only on the repo; writes OUT.jpg only.
    cd data/sanborn
    python bench_2026-11-21/rail-rules/montage.py LIST.json OUT.jpg [--half 220] [--cell 300] [--cols 6] [--max 36]
LIST.json: [{plate, a:[x,y], b:[x,y], label?, mark?}]. Each tile is centred on the middle of a..b, at least `half` px
each way, and shows the plate's proposed bins (batch/N_bins.png if it exists, else unet_data/N_bins.png: railroad ink red,
streetcar ink orange), the batch's tracks thin grey, the proposed tracks (batch/tracks/N_rail_rule.json) black
(railroad) / blue (streetcar), and the item: a..b as a green line, or a green ring when mark is set."""
import sys, os, json
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__))
L = json.load(open(sys.argv[1])); out = sys.argv[2]
arg = lambda k, d: type(d)(sys.argv[sys.argv.index(k) + 1]) if k in sys.argv else d
half = arg('--half', 220); cell = arg('--cell', 300); cols = arg('--cols', 6); mx = arg('--max', 36)
L = L[:mx]; cache = {}; tiles = []
for x in L:
    N = x['plate']
    if N not in cache:
        bp = os.path.join(HERE, 'batch', f'{N}_bins.png'); bp = bp if os.path.exists(bp) else f'unet_data/{N}_bins.png'
        tp = os.path.join(HERE, 'batch', 'tracks', f'{N}_rail_rule.json')
        cache = {N: (cv2.imread(f'cufp/22-{N}.jpg'), cv2.imread(bp, 0), json.load(open(f'unet_data/{N}_rail_rule.json', encoding='utf8'))['tracks'],
                     json.load(open(tp, encoding='utf8'))['tracks'] if os.path.exists(tp) else [])}
    im, B, old, new = cache[N]; H, W = im.shape[:2]
    a, b = np.array(x['a'], float), np.array(x['b'], float); c = (a + b) / 2; r = max(half, int(np.hypot(*(a - b)) / 2) + 60)
    x0, y0, x1, y1 = int(max(0, c[0] - r)), int(max(0, c[1] - r)), int(min(W, c[0] + r)), int(min(H, c[1] + r))
    t = im[y0:y1, x0:x1].copy(); bb = B[y0:y1, x0:x1]; t[bb == 4] = (0, 0, 230); t[bb == 5] = (0, 150, 255); off = np.array([x0, y0])
    for tr in old: cv2.polylines(t, [np.round(np.asarray(tr['pts']) - off).astype(np.int32)], False, (150, 150, 150), 5)
    for tr in new: cv2.polylines(t, [np.round(np.asarray(tr['pts']) - off).astype(np.int32)], False, (0, 0, 0) if tr['kind'] == 'railroad' else (200, 60, 0), 2)
    if x.get('mark'): cv2.circle(t, tuple(np.round(c - off).astype(int).tolist()), 26, (0, 200, 0), 3)
    else: cv2.line(t, tuple(np.round(a - off).astype(int).tolist()), tuple(np.round(b - off).astype(int).tolist()), (0, 200, 0), 1)
    s = cell / max(t.shape[:2]); t = cv2.resize(t, (max(1, int(t.shape[1] * s)), max(1, int(t.shape[0] * s))), interpolation=cv2.INTER_AREA)
    t = cv2.copyMakeBorder(t, 0, cell - t.shape[0], 0, cell - t.shape[1], cv2.BORDER_CONSTANT, value=(255, 255, 255))
    cv2.rectangle(t, (0, 0), (cell - 1, 18), (255, 255, 255), -1)
    cv2.putText(t, f"{len(tiles)} {N} ({int(c[0])},{int(c[1])}) {x.get('label', '')}", (3, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)
    tiles.append(t)
while len(tiles) % cols: tiles.append(np.full((cell, cell, 3), 255, np.uint8))
rows = [np.hstack([cv2.copyMakeBorder(t, 2, 2, 2, 2, cv2.BORDER_CONSTANT, value=(80, 80, 80)) for t in tiles[i:i + cols]]) for i in range(0, len(tiles), cols)]
cv2.imwrite(out, np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 88]); print('wrote', out, len(L), 'tiles')
