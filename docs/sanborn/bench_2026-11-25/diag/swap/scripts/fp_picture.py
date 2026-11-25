"""fp_picture.py (diag/swap, 25 Nov 2026): plate 44 at 1/8 size with a run's predicted blocks coloured by what they are
(fp_anatomy.py's kinds), Ben's blocks outlined white, and the ground Ben did not decide hatched dark.
  blue = matched to one of Ben's blocks, orange = merge, red = false block on undecided ground (void), magenta = other false
    python -B fp_picture.py RUN_DIR OUT.jpg [x0 y0 x1 y1 full px crop, drawn at 1/4]
"""
import json, sys
import numpy as np, cv2
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
sys.path.insert(0, SP + 'bench_2026-11-25/diag/swap/scripts')
import fp_anatomy as FA  # noqa: E402
B, T = FA.B, FA.T

run, out = sys.argv[1].replace('\\', '/').rstrip('/') + '/', sys.argv[2]
crop = [int(v) for v in sys.argv[3:7]] if len(sys.argv) >= 7 else None
an = FA.anatomy(run); kind = {it['j']: it['kind'] for it in an['items']}
polys = json.load(open(run + 'outlines.json', encoding='utf8')); rings = [np.array([s['a'] for s in p], float) for p in polys]
sc = 0.25 if crop else 0.125
im = cv2.imread(SP + 'cufp/22-44.jpg', cv2.IMREAD_REDUCED_COLOR_4 if crop else cv2.IMREAD_REDUCED_COLOR_8).astype(np.float32)
im = (im * 0.6 + 100).astype(np.uint8); ov = im.copy()
void = cv2.resize((T['alpha2'] & ~T['decided']).astype(np.uint8), (im.shape[1], im.shape[0]), interpolation=cv2.INTER_NEAREST) > 0
ov[void] = (ov[void] * 0.6).astype(np.uint8)
col = dict(match=(200, 120, 0), merge=(0, 140, 255), void=(0, 0, 230), street=(200, 0, 200), piece=(200, 0, 200), mixed=(200, 0, 200))
for j, r in enumerate(rings, 1):
    if polys[j - 1] and polys[j - 1][0].get('hole'): continue
    k = kind.get(j, 'match'); q = (r * sc).round().astype(np.int32)
    cv2.fillPoly(ov, [q], col[k])
im = cv2.addWeighted(ov, 0.45, im, 0.55, 0)
for j, r in enumerate(rings, 1):
    if polys[j - 1] and polys[j - 1][0].get('hole'): continue
    cv2.polylines(im, [(r * sc).round().astype(np.int32)], True, col[kind.get(j, 'match')], 2)
for r in T['rings']: cv2.polylines(im, [(r * sc).round().astype(np.int32)], True, (255, 255, 255), 1)
if crop:
    x0, y0, x1, y1 = [int(v * sc) for v in crop]; im = im[y0:y1, x0:x1]
cv2.putText(im, f"{run.split('/')[-3]}/{run.split('/')[-2]}  PQ {an['PQ']}  fp {an['fp_bench44']} {an['fp_by_kind']}", (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
cv2.imwrite(out, im, [cv2.IMWRITE_JPEG_QUALITY, 88]); print(out, an['fp_by_kind'])
