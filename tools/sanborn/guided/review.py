"""Guided reading, completeness review (14 November 2026).

    cd data/sanborn
    python ../../tools/sanborn/guided/review.py N BASIN CROPDIR    -> picks22_guided/22-N/review.json, crops CROPDIR/r/<id>.jpg

After a build (BASIN: the staged deckpage/basin.json), the plate is cut into sections of SEC x SEC plate px. Each section
is drawn at SCALE with the reading grid and the built street centre lines on it (this plate's set red, the rest blue).
Two readers list the printed streets with no line on them and the lines with no street under them (briefs.py review);
merge_guided.py adds a missing street both report, and lists the wrong lines both report.
"""
import json, os, sys
import numpy as np
import cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import streets as S  # noqa: E402
from shapely.geometry import shape  # noqa: E402
SEC, OVER, SCALE = 1500, 150, 0.7
N, BASIN, CROPS = sys.argv[1], sys.argv[2], sys.argv[3].rstrip('/') + '/'
P = S.Plate(N); OUT = S.SP + f'picks22_guided/22-{N}/'; os.makedirs(CROPS + 'r', exist_ok=True)
im = cv2.imread(S.SP + f'cufp/22-{N}.jpg'); H, W = im.shape[:2]
for f in json.load(open(BASIN, encoding='utf8'))['features']:
    p = f['properties']
    if p.get('layer') != 'street' or 'Line' not in f['geometry']['type']: continue
    g = shape(f['geometry'])
    if not g.intersects(P.box): continue
    col = (0, 0, 235) if p.get('set') == f'c{N}' else (235, 110, 0)
    for l in (g.geoms if g.geom_type.startswith('Multi') else [g]):
        if len(l.coords) < 2: continue
        q = P.px_many(np.asarray(l.segmentize(8).coords)[:, :2]); ok = ~np.isnan(q[:, 0])
        for a, b, k in zip(q[:-1], q[1:], ok[:-1] & ok[1:]):
            if k: cv2.line(im, tuple(a.astype(int)), tuple(b.astype(int)), col, 5, cv2.LINE_AA)
rows = []
for y0 in range(0, H, SEC):
    for x0 in range(0, W, SEC):
        x1, y1 = min(W, x0 + SEC + OVER), min(H, y0 + SEC + OVER)
        a = P.A[y0 // 4:y1 // 4, x0 // 4:x1 // 4]
        if a.size == 0 or a.mean() < 0.08: continue
        rows.append(dict(id=f'{N}-r{len(rows) + 1:02d}', box=[x0, y0, x1, y1]))
for r in rows:
    x0, y0, x1, y1 = r['box']; c = cv2.resize(im[y0:y1, x0:x1], None, fx=SCALE, fy=SCALE, interpolation=cv2.INTER_AREA)
    for gx in range((x0 // 100 + 1) * 100, x1, 100):
        X = int((gx - x0) * SCALE); major = gx % 500 == 0
        cv2.line(c, (X, 0), (X, c.shape[0]), (0, 150, 0) if major else (150, 210, 150), 1)
        if major: cv2.putText(c, str(gx), (X + 3, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 110, 0), 2)
    for gy in range((y0 // 100 + 1) * 100, y1, 100):
        Y = int((gy - y0) * SCALE); major = gy % 500 == 0
        cv2.line(c, (0, Y), (c.shape[1], Y), (0, 150, 0) if major else (150, 210, 150), 1)
        if major: cv2.putText(c, str(gy), (3, Y - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 110, 0), 2)
    cv2.imwrite(CROPS + f'r/{r["id"]}.jpg', c, [cv2.IMWRITE_JPEG_QUALITY, 88])
json.dump(rows, open(OUT + 'review.json', 'w', encoding='utf8', newline='\n'), indent=1)
print(N, 'review sections', len(rows))
