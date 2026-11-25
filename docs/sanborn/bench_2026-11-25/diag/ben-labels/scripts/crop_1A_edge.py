"""Picture: the drawn lines along 1A's sheet edge (sheet_edge_rows_1A.json), Ben's line magenta.  python -B .../crop_1A_edge.py"""
import sys, os, json
import numpy as np, cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *  # noqa
full = scan('1A'); H, W = full.shape[:2]; rows = [r for r in json.load(open(DIAG + '/sheet_edge_rows_1A.json')) if r['kind'] == 'drawn' and r['along_edge']]
tiles = []
for r in rows[:8]:
    a, b = np.array(r['a']), np.array(r['b']); c = ((a + b) / 2).round().astype(int); hf = 200
    x0, y0 = max(0, c[0] - hf), max(0, c[1] - hf); t = full[y0:y0 + 2 * hf, x0:x0 + 2 * hf].copy()
    cv2.line(t, tuple((a - [x0, y0]).round().astype(int)), tuple((b - [x0, y0]).round().astype(int)), (255, 0, 255), 1)
    t = cv2.copyMakeBorder(t, 0, 2 * hf - t.shape[0], 0, 2 * hf - t.shape[1], cv2.BORDER_CONSTANT, value=(60, 60, 60))
    cv2.putText(t, f"ink {r['ink']:.2f} edge {r['edge_dist']:.0f} L {r['length']}", (4, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2); tiles.append(t)
while len(tiles) % 4: tiles.append(np.full((400, 400, 3), 60, np.uint8))
cv2.imwrite(os.path.join(DIAG, 'sheet_edge_drawn_1A.jpg'), np.vstack([np.hstack(tiles[i:i + 4]) for i in range(0, len(tiles), 4)]), [cv2.IMWRITE_JPEG_QUALITY, 85])
print(len(rows), [ (r['length'], r['edge_dist'], r['ink']) for r in rows])
