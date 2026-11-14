"""Review page for a plate's crossings (14 November 2026), in the style of the 1912 label review pages.

    cd data/sanborn
    python ../../tools/sanborn/guided/bins_page.py N OUTDIR        -> OUTDIR/index.html, data.js, img/
    python ../../tools/sanborn/guided/bins_page.py N --load CSV    -> picks22_guided/22-N/decisions.json

The page lists every crossing of the guide by bin (low, none found, high, same point) and shows the plate at full
resolution in an inspector (drag to pan). Two separate questions per crossing: is it drawn on the plate (yes / no), and
if yes where (the readers' mean, A, B, or Ben's own click in the inspector). "Add a crossing" places one the guide
did not offer: click the plate and name today's two streets. Answers are kept in the browser; "Save answers" gives
the CSV, which --load turns into decisions.json for merge_guided.py.
"""
import csv, json, os, sys
import numpy as np
import cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import streets as S  # noqa: E402
N = sys.argv[1]; D = S.SP + f'picks22_guided/22-{N}/'
if sys.argv[2] == '--load':
    dec = json.load(open(D + 'decisions.json', encoding='utf8')) if os.path.exists(D + 'decisions.json') else {}
    items, added = dec.get('items', {}), []
    for r in csv.DictReader(open(sys.argv[3], encoding='utf-8-sig')):
        if r['id'].startswith('add'):
            if r['a'] and r['b'] and r['x']: added.append(dict(a=r['a'], b=r['b'], x=float(r['x']), y=float(r['y'])))
        elif r['drawn'] == 'no': items[r['id']] = dict(drawn=False)
        elif r['drawn'] == 'yes' and r['where'] in ('mean', 'A', 'B'): items[r['id']] = dict(drawn=True, where=r['where'])
        elif r['drawn'] == 'yes' and r['where'] == 'manual' and r['x']: items[r['id']] = dict(drawn=True, where='manual', x=float(r['x']), y=float(r['y']))
    json.dump(dict(items=items, added=added), open(D + 'decisions.json', 'w', encoding='utf8', newline=chr(10)), indent=1, sort_keys=True)
    print('decisions', len(items), 'added', len(added)); sys.exit()
OUT = sys.argv[2].rstrip('/') + '/'; os.makedirs(OUT + 'img', exist_ok=True); K = 3
P = S.Plate(N); full = cv2.imread(S.SP + f'cufp/22-{N}.jpg'); ST = P.streets()
def streets_on(im, k, w):
    for s in ST:
        g = s['geom']
        for l in (g.geoms if g.geom_type.startswith('Multi') else [g]):
            q = P.px_many(np.asarray(l.segmentize(5).coords)[:, :2]) / k; ok = ~np.isnan(q[:, 0])
            for a, b, f in zip(q[:-1], q[1:], ok[:-1] & ok[1:]):
                if f: cv2.line(im, tuple(a.astype(int)), tuple(b.astype(int)), (220, 60, 0), w, cv2.LINE_AA)
base = cv2.resize(full, None, fx=1 / K, fy=1 / K, interpolation=cv2.INTER_AREA); base = (base * 0.75 + 64).astype(np.uint8)
streets_on(base, K, 2); cv2.imwrite(OUT + 'img/plate.jpg', base, [cv2.IMWRITE_JPEG_QUALITY, 82])
cv2.imwrite(OUT + 'img/clean.jpg', full, [cv2.IMWRITE_JPEG_QUALITY, 88])
lined = full.copy(); streets_on(lined, 1, 2); cv2.imwrite(OUT + 'img/lined.jpg', lined, [cv2.IMWRITE_JPEG_QUALITY, 88])
items = []
for r in json.load(open(D + 'bins.json', encoding='utf8')):
    t = P.px(r['E'], r['N']); pred = None if np.isnan(t[0]) else [round(float(t[0]), 1), round(float(t[1]), 1)]
    items.append(dict(id=r['id'], bin=r['bin'], a=r['a'], b=r['b'], why=r['why'], A=r['A'], B=r['B'], pred=pred, ben=r.get('ben'),
                      notes=[n for n in r.get('notes', []) if n]))
data = dict(plate=N, k=K, W=full.shape[1], H=full.shape[0], items=items, streets=sorted({s['name'] for s in ST}))
open(OUT + 'data.js', 'w', encoding='utf8', newline=chr(10)).write('const DATA = ' + json.dumps(data) + ';' + chr(10))
page = open(os.path.join(HERE, 'bins_page.html'), encoding='utf8').read().replace('{N}', N)
open(OUT + 'index.html', 'w', encoding='utf8', newline=chr(10)).write(page)
print('page', OUT, len(items), 'crossings')
