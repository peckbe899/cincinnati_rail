"""Montage of survey block-number candidates on a plate (scan only, 1:1), skipping drawn dev crops and H windows.
    python -B .../scripts/look_cands.py N OUT.png [max]"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'code'))
import numpy as np, cv2
import bfcommon as C

N, out = sys.argv[1], sys.argv[2]; mx = int(sys.argv[3]) if len(sys.argv) > 3 else 40
im, paper = C.load_scan(N); H, W = im.shape[:2]
crops = C.dev_crops(); wins = [c['win'] for c in crops.values() if c['plate'] == N]
tiles = []
for x, y, r, note in C.candidates(N):
    b = (x - 100, y - 100, x + 100, y + 100)
    if C.in_hwin(N, b, 50): continue
    if any(b[0] < w[2] and b[2] > w[0] and b[1] < w[3] and b[3] > w[1] for w in wins): continue
    X0, Y0 = max(0, b[0]), max(0, b[1]); t = im[Y0:min(H, b[3]), X0:min(W, b[2])].copy()
    t = cv2.copyMakeBorder(t, 0, 200 - t.shape[0], 0, 200 - t.shape[1], cv2.BORDER_CONSTANT, value=(255, 255, 255))
    cv2.putText(t, f'{r} {x},{y}', (3, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 1)
    tiles.append(t)
    if len(tiles) >= mx: break
cols = 8; rows = (len(tiles) + cols - 1) // cols; S = np.full((rows * 202, cols * 202, 3), 255, np.uint8)
for i, t in enumerate(tiles): rr, cc = divmod(i, cols); S[rr * 202:rr * 202 + 200, cc * 202:cc * 202 + 200] = t
cv2.imwrite(out, S); print(len(tiles), 'tiles')
