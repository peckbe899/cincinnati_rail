"""Stack check pictures into one sheet. python -B stack.py OUT COLS IMG1 IMG2 ..."""
import sys, numpy as np, cv2
out, cols = sys.argv[1], int(sys.argv[2]); ims = [cv2.imread(p) for p in sys.argv[3:]]
rows = []
for i in range(0, len(ims), cols):
    r = ims[i:i + cols]; h = max(x.shape[0] for x in r)
    rows.append(np.hstack([cv2.copyMakeBorder(x, 0, h - x.shape[0], 0, 10, cv2.BORDER_CONSTANT, value=(255, 255, 255)) for x in r]))
w = max(r.shape[1] for r in rows)
cv2.imwrite(out, np.vstack([cv2.copyMakeBorder(r, 0, 10, 0, w - r.shape[1], cv2.BORDER_CONSTANT, value=(255, 255, 255)) for r in rows]), [cv2.IMWRITE_JPEG_QUALITY, 90])
