"""Audit pictures of the batch's block lines on a plate (visual-cut, 21 Nov 2026). Reads only; writes into views/.

    python view.py N                       overview of the whole plate, about 1900 px wide, 1000 px grid
    python view.py N X0 Y0 W H [SCALE]     a window in full-size px (default scale: fit 1900 px wide)

Colours: green = editor line on a printed line; orange = editor line not settled; cyan thin = sheet edge (editor's
sheet()) or paper-edge side; dark grey thin = short pieces the export drops; red dot = a line end with no other line
end within 25 px (a corner left open); light blue tint = ground the outline step calls block; red numbers = polygon id
(index in outlines.json). Plate 44 only: magenta = Ben's street map (thick: printed/drawn sides; thin: sheet edge).
"""
import os, sys
import cv2
from vlib import load, draw, HERE
n = sys.argv[1]; D = load(n); os.makedirs(os.path.join(HERE, 'views'), exist_ok=True)
EX = []
if n == '44':   # Ben's street map (ground truth), thick magenta under the editor lines: printed and drawn sides; sheet-edge sides thin
    import json
    from vlib import SP
    for l in json.load(open(SP + 'streetmap/22-44.json', encoding='utf8'))['lines']:
        EX.append((l['a'], l['b'], (255, 0, 255), 9 if l['kind'] != 'sheet_edge' else 3))
if len(sys.argv) == 2:
    s = 1900 / D['W']; im = draw(D, 0, 0, D['W'], D['H'], s, grid=1000, extra=[(a, b, c, t * s * 2.5) for a, b, c, t in EX])
    out = os.path.join(HERE, 'views', f'{n}_overview.jpg')
else:
    x0, y0, w, h = map(int, sys.argv[2:6]); s = float(sys.argv[6]) if len(sys.argv) > 6 else min(1.0, 1900 / w)
    im = draw(D, x0, y0, w, h, s, grid=500 if s >= 0.4 else 1000, extra=[(a, b, c, t * s) for a, b, c, t in EX])
    out = os.path.join(HERE, 'views', f'{n}_{x0}_{y0}_{w}x{h}.jpg')
cv2.imwrite(out, im, [cv2.IMWRITE_JPEG_QUALITY, 88]); print(out, im.shape, 'blocks', len(D['polys']), 'exported', len(D['exp']), 'editor lines', len(D['shown']))
