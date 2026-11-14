"""Review page for a plate's low-confidence crossings (14 November 2026), in the style of the 1912 label review pages.

    cd data/sanborn
    python ../../tools/sanborn/guided/bins_page.py N OUTDIR        -> OUTDIR/index.html, data.js, img/
    python ../../tools/sanborn/guided/bins_page.py N --load CSV    -> picks22_guided/22-N/decisions.json

The page: the plate (faded) with today's streets in blue; green dots are high crossings, numbered markers the low ones.
Each low crossing has a card with a full-resolution crop (A = square, B = circle, today's crossing = blue +) and the
choices real (the readers' mean) / A / B / not. Answers are kept in the browser; "Save answers" gives the CSV, which
--load turns into decisions.json for merge_guided.py.
"""
import csv, json, os, sys
import numpy as np
import cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import streets as S  # noqa: E402
N = sys.argv[1]; D = S.SP + f'picks22_guided/22-{N}/'
if sys.argv[2] == '--load':
    dec = json.load(open(D + 'decisions.json', encoding='utf8')) if os.path.exists(D + 'decisions.json') else {}
    for r in csv.DictReader(open(sys.argv[3], encoding='utf-8-sig')):
        if r.get('answer') in ('real', 'A', 'B', 'not'): dec[r['id']] = r['answer']
    json.dump(dec, open(D + 'decisions.json', 'w', encoding='utf8', newline='\n'), indent=1, sort_keys=True)
    print('decisions', len(dec)); sys.exit()
OUT = sys.argv[2].rstrip('/') + '/'; os.makedirs(OUT + 'img', exist_ok=True); K = 3; C = 300
P = S.Plate(N); full = cv2.imread(S.SP + f'cufp/22-{N}.jpg'); ST = P.streets()
def streets_on(im, x0, y0, k, w):
    for s in ST:
        g = s['geom']
        for l in (g.geoms if g.geom_type.startswith('Multi') else [g]):
            q = (P.px_many(np.asarray(l.segmentize(5).coords)[:, :2]) - [x0, y0]) / k; ok = ~np.isnan(q[:, 0])
            for a, b, f in zip(q[:-1], q[1:], ok[:-1] & ok[1:]):
                if f: cv2.line(im, tuple(a.astype(int)), tuple(b.astype(int)), (220, 60, 0), w, cv2.LINE_AA)
base = cv2.resize(full, None, fx=1 / K, fy=1 / K, interpolation=cv2.INTER_AREA); base = (base * 0.75 + 64).astype(np.uint8)
streets_on(base, 0, 0, K, 2); cv2.imwrite(OUT + 'img/plate.jpg', base, [cv2.IMWRITE_JPEG_QUALITY, 82])
bins = json.load(open(D + 'bins.json', encoding='utf8')); items = []; n = 0
for r in bins:
    q = [v for v in (r['A'], r['B']) if v]; m = np.mean([v[:2] for v in q], 0)
    if r['bin'] != 'low':
        items.append(dict(id=r['id'], bin=r['bin'], x=float(m[0]), y=float(m[1]))); continue
    n += 1; x0, y0 = int(m[0]) - C, int(m[1]) - C
    c = np.full((2 * C, 2 * C, 3), 255, np.uint8); H, W = full.shape[:2]
    sx0, sy0, sx1, sy1 = max(0, x0), max(0, y0), min(W, x0 + 2 * C), min(H, y0 + 2 * C)
    c[sy0 - y0:sy1 - y0, sx0 - x0:sx1 - x0] = full[sy0:sy1, sx0:sx1]
    streets_on(c, x0, y0, 1, 1)
    g = next(t for t in json.load(open(D + 'guide_A.json', encoding='utf8')) if t['id'] == r['id'])
    t = P.px(g['E'], g['N'])
    if not np.isnan(t[0]): p = (int(t[0] - x0), int(t[1] - y0)); cv2.drawMarker(c, p, (220, 60, 0), cv2.MARKER_CROSS, 24, 2)
    if r['A']: p = (int(r['A'][0] - x0), int(r['A'][1] - y0)); cv2.rectangle(c, (p[0] - 9, p[1] - 9), (p[0] + 9, p[1] + 9), (0, 0, 230), 2)
    if r['B']: cv2.circle(c, (int(r['B'][0] - x0), int(r['B'][1] - y0)), 10, (0, 150, 0), 2)
    cv2.imwrite(OUT + f'img/{r["id"]}.jpg', c, [cv2.IMWRITE_JPEG_QUALITY, 85])
    items.append(dict(id=r['id'], bin='low', n=n, x=float(m[0]), y=float(m[1]), a=r['a'], b=r['b'], why=r['why'],
                      A=r['A'], B=r['B'], ben=r.get('ben')))
data = dict(plate=N, k=K, w=base.shape[1], h=base.shape[0], items=items)
open(OUT + 'data.js', 'w', encoding='utf8', newline='\n').write('const DATA = ' + json.dumps(data) + ';\n')
page = open(os.path.join(HERE, 'bins_page.html'), encoding='utf8').read().replace('{N}', N)
open(OUT + 'index.html', 'w', encoding='utf8', newline='\n').write(page)
print('page', OUT, 'low', n)
