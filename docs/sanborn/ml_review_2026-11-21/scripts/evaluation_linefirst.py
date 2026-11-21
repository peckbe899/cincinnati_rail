"""Prototype (scratch only): blocks as the regions the LINE map encloses, kept where the area network says block.
    python linefirst.py LINES_PNG AREA_PNG TAG
For each gap-closing radius r: line map > 0.5 dilated by r; connected regions of what is left; a region is a block when
its mean P(block) > 0.5 and it is >= 6000 px; then grown back by r so it reaches the line's middle. IoU against Ben's 55."""
import sys, json, numpy as np, cv2, evallib as E
from shapely.geometry import Polygon
LP, AP, TAG = sys.argv[1:4]; T = E.truth('44'); W, H = T['size']; ben = [Polygon(b['ring']) for b in T['blocks']]
pl = cv2.imread(LP, 0) > 127; pa = cv2.resize(cv2.imread(AP, 0), (W, H), interpolation=cv2.INTER_LINEAR).astype(np.float32) / 255
alpha = cv2.resize(np.load(E.SP + 'cufp/44/png_alpha_s4.npy').astype(np.float32), (W, H)) > 0.5
out = {}
for r in (2, 4, 8):
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1)); wall = cv2.dilate(pl.astype(np.uint8), k) > 0
    free = (~wall & alpha).astype(np.uint8); n, cc, st, _ = cv2.connectedComponentsWithStats(free, connectivity=4)
    mean = np.bincount(cc.ravel(), weights=pa.ravel(), minlength=n) / np.maximum(1, np.bincount(cc.ravel(), minlength=n))
    keep = (mean > 0.5) & (st[:, cv2.CC_STAT_AREA] >= 6000); keep[0] = False
    polys = []
    for i in np.nonzero(keep)[0]:
        x, y, w, h = st[i, :4]; m = (cc[y:y + h, x:x + w] == i).astype(np.uint8); m = cv2.dilate(m, k) if r else m
        cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        c = max(cs, key=cv2.contourArea)[:, 0, :] + [x, y]
        if len(c) >= 3:
            p = Polygon(c); p = p if p.is_valid else p.buffer(0); polys.append(p)
    m_, _ = E.block_match(polys, ben); out[r] = m_; print(TAG, 'r', r, m_)
json.dump(out, open(f'out/linefirst_{TAG}.json', 'w'), indent=1)
