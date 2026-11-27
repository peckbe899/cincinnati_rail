"""Per dev crop: straight-run non-text called text, non-text called text, text found; baseline mask dir vs new.
    python -B .../scripts/crop_diff.py BASE_DIR NEW_DIR"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'code'))
import numpy as np, cv2
import bfcommon as C
bd, nd = sys.argv[1], sys.argv[2]; crops = C.dev_crops(); tot = np.zeros(6, int)
for tid, c in sorted(crops.items()):
    T = cv2.imread(os.path.join(C.DEVB, 'truth', f'{tid}_mask.png'), 0); x0, y0, x1, y1 = c['win']; N = c['plate']
    a = np.isin(cv2.imread(os.path.join(bd, f'{N}_text.png'), 0)[y0:y1, x0:x1], (2, 3)); b = np.isin(cv2.imread(os.path.join(nd, f'{N}_text.png'), 0)[y0:y1, x0:x1], (2, 3))
    s = C.lineish(T == 1); t1 = T == 1; t2 = T == 2
    v = np.array([(s & a).sum(), (s & b).sum(), (t1 & a).sum(), (t1 & b).sum(), (t2 & a).sum(), (t2 & b).sum()]); tot += v
    if (v[0] != v[1]) or (v[2] != v[3]) or (v[4] != v[5]):
        print(f'{tid} {N:>4s} {c["scale_ft_per_inch"]}  straight {v[0]}->{v[1]}  nontext {v[2]}->{v[3]}  text {v[4]}->{v[5]} of {int(t2.sum())}')
print('total', tot.tolist())
