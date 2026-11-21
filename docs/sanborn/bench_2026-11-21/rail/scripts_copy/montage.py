"""Montage of full-size crops around listed rule tracks, with the batch's bins and rule tracks drawn (bench_2026-11-21/rail).
Read-only on the repo.
    cd data/sanborn
    python bench_2026-11-21/rail/montage.py LIST.json OUT.jpg [--plates 14,5] [--half 300] [--cell 300] [--cols 6] [--max 30]
LIST.json: [{plate, a:[x,y], b:[x,y], ...}] (census hook_candidates.json format). Bins: unet_data/N_bins.png and
unet_data/N_rail_rule.json, unless --bins DIR is given (then DIR/N_bins.png and DIR/N_rail_rule.json)."""
import sys, json, os
import numpy as np, cv2
sys.path.insert(0, 'bench_2026-11-21/rail'); from crops import overlay
L = json.load(open(sys.argv[1])); out = sys.argv[2]
arg = lambda k, d: type(d)(sys.argv[sys.argv.index(k) + 1]) if k in sys.argv else d
plates = arg('--plates', '').split(',') if '--plates' in sys.argv else None
half = arg('--half', 300); cell = arg('--cell', 300); cols = arg('--cols', 6); mx = arg('--max', 30); bd = arg('--bins', '')
L = [x for x in L if plates is None or x['plate'] in plates][:mx]
cache = {}; tiles = []
for x in L:
    N = x['plate']
    if N not in cache:
        bp = os.path.join(bd, f'{N}_bins.png') if bd else f'unet_data/{N}_bins.png'; rp = os.path.join(bd, f'{N}_rail_rule.json') if bd else f'unet_data/{N}_rail_rule.json'
        if '--rules' in sys.argv: rp = os.path.join(sys.argv[sys.argv.index('--rules') + 1], f'{N}_rail_rule.json')
        cache = {N: (cv2.imread(f'cufp/22-{N}.jpg'), cv2.imread(bp, 0), json.load(open(rp, encoding='utf8'))['tracks'])}
    im, B, R = cache[N]; H, W = im.shape[:2]
    c = (np.array(x['a']) + np.array(x['b'])) / 2; r = max(half, int(np.hypot(*(np.array(x['a']) - np.array(x['b']))) / 2) + 60)
    x0, y0, x1, y1 = int(max(0, c[0] - r)), int(max(0, c[1] - r)), int(min(W, c[0] + r)), int(min(H, c[1] + r))
    t = overlay(im, B, R, None, x0, y0, x1, y1)
    if x.get('mark'): cv2.circle(t, (int(c[0] - x0), int(c[1] - y0)), 28, (0, 200, 0), 3)   # the sampled point
    t = cv2.resize(t, (cell, cell), interpolation=cv2.INTER_AREA)
    cv2.rectangle(t, (0, 0), (cell - 1, 22), (255, 255, 255), -1); cv2.putText(t, f"{N} ({int(c[0])},{int(c[1])}) {x.get('len', '')}", (3, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1)
    tiles.append(t)
while len(tiles) % cols: tiles.append(np.full((cell, cell, 3), 255, np.uint8))
rows = [np.hstack([cv2.copyMakeBorder(t, 2, 2, 2, 2, cv2.BORDER_CONSTANT, value=(80, 80, 80)) for t in tiles[i:i + cols]]) for i in range(0, len(tiles), cols)]
cv2.imwrite(out, np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 88]); print('wrote', out, len(L), 'tiles')
