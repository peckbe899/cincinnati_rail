"""outline-quality: picture of an outlines.json on plate 44 at quarter size, beside Ben's lines.
    python draw_sides.py RUN_DIR [OUT.jpg] [x0 y0 x1 y1 (full px crop, drawn at half size)]
Ben's lines thin magenta; exported sides: on print green, other states orange, bridges cyan (thick), short pieces
grey, paper-edge sides dark blue. Writes OUT (default RUN_DIR/sides.jpg)."""
import json, sys
import numpy as np, cv2
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
run = sys.argv[1].rstrip('/') + '/'; out = sys.argv[2] if len(sys.argv) > 2 else run + 'sides.jpg'
crop = [int(v) for v in sys.argv[3:7]] if len(sys.argv) >= 7 else None
polys = json.load(open(run + 'outlines.json')); sm = json.load(open(SP + 'streetmap/22-44.json'))
if crop:
    x0, y0, x1, y1 = crop; sc = 0.5; im = cv2.imread(SP + 'cufp/22-44.jpg')[y0:y1, x0:x1]; im = cv2.resize(im, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA); off = np.array([x0, y0], float)
else:
    sc = 0.25; im = cv2.imread(SP + 'cufp/22-44.jpg', cv2.IMREAD_REDUCED_COLOR_4); off = np.zeros(2)
im = (im * 0.55 + 110).astype(np.uint8)
P = lambda p: tuple(((np.array(p, float) - off) * sc).round().astype(int))
for l in sm['lines']: cv2.line(im, P(l['a']), P(l['b']), (200, 0, 200), 1, cv2.LINE_AA)
for p in polys:
    for s in p:
        if s['state'] == 'short': col, th = (140, 140, 140), 1
        elif s.get('paper_edge'): col, th = (120, 40, 0), 1
        elif s.get('bridge'): col, th = (230, 200, 0), 3
        elif s['state'] == 'on print': col, th = (0, 150, 0), 2
        else: col, th = (0, 140, 255), 2
        cv2.line(im, P(s['a']), P(s['b']), col, th, cv2.LINE_AA)
cv2.imwrite(out, im, [cv2.IMWRITE_JPEG_QUALITY, 85]); print(out)
