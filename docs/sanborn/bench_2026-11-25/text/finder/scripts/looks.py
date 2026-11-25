"""Crops of the finder's half-size overlay pictures for looking at: per plate the 2400 x 1600 px window with the most text
and one with a middling amount (rank 40%). python -B <this> OUT_DIR LOOK_DIR N [N ...]"""
import sys, os
sys.dont_write_bytecode = True
import numpy as np, cv2
O, LK = sys.argv[1], sys.argv[2]
for N in sys.argv[3:]:
    code = cv2.imread(os.path.join(O, f'{N}_finder.png'), 0); pic = cv2.imread(os.path.join(O, f'{N}_finder.jpg'))
    H, W = code.shape; tw, th = 2400, 1600; t = np.isin(code, (2, 3, 4)).astype(np.float32)
    cand = []
    for y in range(0, max(1, H - th), 400):
        for x in range(0, max(1, W - tw), 400):
            cand.append((t[y:y + th, x:x + tw].sum(), x, y))
    cand.sort(reverse=True)
    for name, (s, x, y) in (('a', cand[0]), ('b', cand[int(len(cand) * 0.4)])):
        c = pic[y // 2:(y + th) // 2, x // 2:(x + tw) // 2]
        cv2.imwrite(os.path.join(LK, f'{N}_{name}_{x}_{y}.jpg'), c, [cv2.IMWRITE_JPEG_QUALITY, 88]); print(N, name, x, y, int(s))
