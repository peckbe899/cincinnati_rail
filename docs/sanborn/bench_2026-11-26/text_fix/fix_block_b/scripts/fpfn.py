"""Where a new mask differs from the base on dev crops: green = new text px the truth calls text, red = new text px the
truth calls not text, orange = new text on don't care, blue = truth text still missed, grey = other ink.
    python -B .../scripts/fpfn.py BASE_DIR NEW_DIR OUT.png ZOOM DB## ..."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'code'))
import numpy as np, cv2
import bfcommon as C
bd, nd, out, z, ids = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), sys.argv[5:]
crops = C.dev_crops(); rows = []
for tid in ids:
    c = crops[tid]; N = c['plate']; x0, y0, x1, y1 = c['win']
    T = cv2.imread(os.path.join(C.DEVB, 'truth', f'{tid}_mask.png'), 0)
    a = cv2.imread(os.path.join(bd, f'{N}_text.png'), 0)[y0:y1, x0:x1]; b = cv2.imread(os.path.join(nd, f'{N}_text.png'), 0)[y0:y1, x0:x1]
    ta, tb = np.isin(a, (2, 3)), np.isin(b, (2, 3)); im = cv2.imread(f'cufp/22-{N}.jpg')[y0:y1, x0:x1]
    o = np.full(im.shape, 255, np.uint8); o[b > 0] = (200, 200, 200)
    new = tb & ~ta; o[new & (T == 2)] = (0, 170, 0); o[new & (T == 1)] = (0, 0, 255); o[new & (T == 3)] = (0, 160, 255); o[(T == 2) & ~tb] = (255, 100, 0)
    o[ta & ~tb] = (255, 0, 255)
    r = np.concatenate([im, o], 1); r = cv2.resize(r, None, fx=z, fy=z, interpolation=cv2.INTER_NEAREST)
    cv2.putText(r, tid, (3, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1); rows.append(r)
Wm = max(r.shape[1] for r in rows)
cv2.imwrite(out, np.concatenate([cv2.copyMakeBorder(r, 0, 4, 0, Wm - r.shape[1], cv2.BORDER_CONSTANT, value=(0, 0, 0)) for r in rows], 0))
