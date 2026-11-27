"""Zoom sheet with a 10 px grid (sealed builder A). Scan only.
    python -B .../zsheet.py OUT.png W H SCALE COLS N:x:y:label [...]   cells centred on x, y"""
import os, sys
sys.dont_write_bytecode = True
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from view import zoom
out, W, H, sc, cols = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), float(sys.argv[4]), int(sys.argv[5])
cells = []
for a in sys.argv[6:]:
    N, x, y, lab = a.split(':', 3); x, y = int(x), int(y)
    A = zoom(N, x - W // 2, y - H // 2, x + W // 2, y + H // 2, sc, grid=10)
    for gx in range(((x - W // 2) // 50 + 1) * 50, x + W // 2, 50):
        if gx % 100: cv2.putText(A, str(gx), (int((gx - x + W // 2) * sc) + 2, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.33, (0, 120, 0), 1)
    for gy in range(((y - H // 2) // 50 + 1) * 50, y + H // 2, 50):
        if gy % 100: cv2.putText(A, str(gy), (2, int((gy - y + H // 2) * sc) - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.33, (0, 120, 0), 1)
    C = np.full((A.shape[0] + 16, A.shape[1], 3), 255, np.uint8); C[16:] = A
    cv2.putText(C, f'{N} {lab} @{x},{y} x{sc}', (2, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 0, 0), 1); cells.append(C)
CH = max(c.shape[0] for c in cells); CW = max(c.shape[1] for c in cells); rows = (len(cells) + cols - 1) // cols
G = np.full((rows * (CH + 4), cols * (CW + 4), 3), 160, np.uint8)
for i, C in enumerate(cells):
    r, c = divmod(i, cols); G[r * (CH + 4):r * (CH + 4) + C.shape[0], c * (CW + 4):c * (CW + 4) + C.shape[1]] = C
cv2.imwrite(out, G); print(out, G.shape)
