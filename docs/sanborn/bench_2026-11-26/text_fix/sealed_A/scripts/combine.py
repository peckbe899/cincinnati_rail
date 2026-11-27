"""Stack check pictures into sheets (sealed builder A). python -B combine.py OUTPREFIX COLS PER f1.png f2.png ..."""
import sys, cv2, numpy as np
out, cols, per = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]); fs = sys.argv[4:]
for k in range(0, len(fs), per):
    ims = [cv2.imread(f) for f in fs[k:k + per]]
    CW = max(i.shape[1] for i in ims); CH = max(i.shape[0] for i in ims); rows = (len(ims) + cols - 1) // cols
    G = np.full((rows * (CH + 6), cols * (CW + 6), 3), 120, np.uint8)
    for i, C in enumerate(ims):
        r, c = divmod(i, cols); G[r * (CH + 6):r * (CH + 6) + C.shape[0], c * (CW + 6):c * (CW + 6) + C.shape[1]] = C
    f = f'{out}_{k // per}.png'; cv2.imwrite(f, G); print(f, G.shape)
