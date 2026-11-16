"""A piece of a plate's scan with a reading grid in plate pixels, for marking block lines by eye (14 November 2026).

    cd data/sanborn
    python ../../tools/sanborn/unet/crop.py N X0 Y0 X1 Y1 OUT.jpg [SCALE]

Grid every 50 px (faint), every 100 px labelled. With picks22_guided/22-N/streets_marked.json present, the marked
block lines are drawn on it (green), so a reading can be checked against the print.
"""
import json, os, sys
import numpy as np
import cv2
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import _ws  # noqa: E402
N, x0, y0, x1, y1, out = sys.argv[1], *map(int, sys.argv[2:6]), sys.argv[6]; sc = float(sys.argv[7]) if len(sys.argv) > 7 else 1.0
full = cv2.imread(_ws.DATA + f'cufp/22-{N}.jpg'); H, W = full.shape[:2]
c = np.full((y1 - y0, x1 - x0, 3), 255, np.uint8); a, b, e, f = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
c[b - y0:f - y0, a - x0:e - x0] = full[b:f, a:e]
c = cv2.resize(c, None, fx=sc, fy=sc, interpolation=cv2.INTER_CUBIC if sc > 1 else cv2.INTER_AREA)
mf = _ws.DATA + f'unet_data/{N}_marked_refined.json'   # the marked edges after they were moved onto the printed lines (make_labels.py)
if os.path.exists(mf) and '--bare' not in sys.argv:
    for s in json.load(open(mf, encoding='utf8')):
        for key in ('left', 'right'):
            q = ((np.array(s[key], float) - [x0, y0]) * sc).round().astype(np.int32)
            cv2.polylines(c, [q], False, (0, 170, 0), 2, cv2.LINE_AA)
of = _ws.DATA + f'picks22_guided/22-{N}/outlines.json'  # --outlines: the networks' block sides that test as on the print (outlines.py), thin magenta, as a hint
if '--outlines' in sys.argv and os.path.exists(of):
    for poly in json.load(open(of, encoding='utf8')):
        for r in poly:
            if r['state'] == 'on print': cv2.line(c, *[tuple(((np.array(r[k], float) - [x0, y0]) * sc).round().astype(int)) for k in ('a', 'b')], (200, 0, 200), 1, cv2.LINE_AA)
for g in range((x0 // 50 + 1) * 50, x1, 50):
    X = int((g - x0) * sc); big = g % 100 == 0; cv2.line(c, (X, 0), (X, c.shape[0]), (0, 0, 255) if big else (150, 150, 255), 1)
    if big: cv2.putText(c, str(g), (X + 2, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 180), 1); cv2.putText(c, str(g), (X + 2, c.shape[0] - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 180), 1)
for g in range((y0 // 50 + 1) * 50, y1, 50):
    Y = int((g - y0) * sc); big = g % 100 == 0; cv2.line(c, (0, Y), (c.shape[1], Y), (0, 0, 255) if big else (150, 150, 255), 1)
    if big: cv2.putText(c, str(g), (2, Y - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 180), 1); cv2.putText(c, str(g), (c.shape[1] - 40, Y - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 180), 1)
cv2.imwrite(out, c, [cv2.IMWRITE_JPEG_QUALITY, 90])
