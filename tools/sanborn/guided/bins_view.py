"""Draw a plate's crossing bins for Ben to judge (14 November 2026).

    cd data/sanborn
    python ../../tools/sanborn/guided/bins_view.py N OUT.jpg

Faded scan with today's streets in blue (through the plate's current model). High crossings: green dots. Low: a
numbered orange label, reader A's point as a square and B's as a circle, joined if both found it. Ben's calls go in
picks22_guided/22-N/decisions.json as {"<id>": "real" | "A" | "B" | "not"}; the numbers map to ids in OUT.txt.
"""
import json, os, sys
import numpy as np
import cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import streets as S  # noqa: E402
N, OUT = sys.argv[1], sys.argv[2]; K = 3
P = S.Plate(N); D = S.SP + f'picks22_guided/22-{N}/'
im = cv2.imread(S.SP + f'cufp/22-{N}.jpg'); im = cv2.resize(im, None, fx=1 / K, fy=1 / K, interpolation=cv2.INTER_AREA)
im = (im * 0.75 + 64).astype(np.uint8)
for s in P.streets():
    g = s['geom']
    for l in (g.geoms if g.geom_type.startswith('Multi') else [g]):
        q = P.px_many(np.asarray(l.segmentize(5).coords)[:, :2]) / K; ok = ~np.isnan(q[:, 0])
        for a, b, k in zip(q[:-1], q[1:], ok[:-1] & ok[1:]):
            if k: cv2.line(im, tuple(a.astype(int)), tuple(b.astype(int)), (220, 60, 0), 2, cv2.LINE_AA)
bins = json.load(open(D + 'bins.json', encoding='utf8')); lines = []; n = 0
pt = lambda r: (int(r[0] / K), int(r[1] / K))
for r in bins:
    if r['bin'] == 'high':
        q = [v for v in (r['A'], r['B']) if v]; c = pt(np.mean([v[:2] for v in q], 0))
        cv2.circle(im, c, 6, (0, 160, 0), -1); continue
    if r['bin'] != 'low': continue
    n += 1; col = (0, 120, 255)
    if r['A'] and r['B']: cv2.line(im, pt(r['A']), pt(r['B']), col, 2)
    if r['A']: c = pt(r['A']); cv2.rectangle(im, (c[0] - 5, c[1] - 5), (c[0] + 5, c[1] + 5), col, 2)
    if r['B']: cv2.circle(im, pt(r['B']), 6, col, 2)
    c = pt(r['A'] or r['B']); t = f'L{n}'
    cv2.putText(im, t, (c[0] + 8, c[1] - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 4, cv2.LINE_AA)
    cv2.putText(im, t, (c[0] + 8, c[1] - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 70, 200), 2, cv2.LINE_AA)
    lines.append(f"{t}\t{r['id']}\t{r['a']} x {r['b']}\t{r['why']}")
cv2.imwrite(OUT, im, [cv2.IMWRITE_JPEG_QUALITY, 85])
open(OUT.rsplit('.', 1)[0] + '.txt', 'w', encoding='utf8', newline='\n').write('\n'.join(lines) + '\n')
print('high', sum(r['bin'] == 'high' for r in bins), 'low', n)
