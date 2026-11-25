"""lines_panel.py (diag/swap, 25 Nov 2026): a 2x2 panel of line maps on a crop of plate 44 (full px box, drawn at 1/2):
drawn line px (P > 0.5) red where within 3 px of Ben's lines... no: green = on one of Ben's lines (3 px), red = off them;
Ben's lines that no drawn px reaches (3 px) blue. Each tile is labelled.
    python -B lines_panel.py OUT.jpg x0 y0 x1 y1 LABEL=PNG LABEL=PNG LABEL=PNG LABEL=PNG
"""
import sys, json
import numpy as np, cv2
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
out = sys.argv[1]; x0, y0, x1, y1 = [int(v) for v in sys.argv[2:6]]; items = [a.split('=', 1) for a in sys.argv[6:]]
sm = json.load(open(SP + 'streetmap/22-44.json', encoding='utf8'))
L = np.zeros((y1 - y0, x1 - x0), np.uint8)
for l in sm['lines']: cv2.line(L, (int(round(l['a'][0])) - x0, int(round(l['a'][1])) - y0), (int(round(l['b'][0])) - x0, int(round(l['b'][1])) - y0), 1, 1)
K = np.ones((7, 7), np.uint8); nearL = cv2.dilate(L, K) > 0
scan = cv2.imread(SP + 'cufp/22-44.jpg')[y0:y1, x0:x1].astype(np.float32) * 0.5 + 110
tiles = []
for lab, f in items:
    p = cv2.imread(f, 0)[y0:y1, x0:x1] > 127; near_p = cv2.dilate(p.astype(np.uint8), K) > 0
    im = scan.copy(); im[p & nearL] = (0, 170, 0); im[p & ~nearL] = (0, 0, 230); im[(L > 0) & ~near_p] = (255, 90, 0)
    im = cv2.resize(im.clip(0, 255).astype(np.uint8), None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)
    cv2.putText(im, lab, (6, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2); tiles.append(im)
while len(tiles) % 2: tiles.append(np.full_like(tiles[0], 255))
rows = [np.hstack(tiles[i:i + 2]) for i in range(0, len(tiles), 2)]
cv2.imwrite(out, np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 85]); print(out)
