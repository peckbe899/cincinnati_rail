"""make_boxes44.py (text/effect, 25 Nov 2026): word boxes from a cleaner text mask (default I2), for the line tests.
    cd data/sanborn; python -B bench_2026-11-25/text/effect/code/make_boxes44.py [SRC_NAME]       (masks/44_map_<SRC>.png)
  B2   SRC closed with a 9 px disc so the characters of one number or word join; each group's rotated bounding rectangle
       (cv2.minAreaRect) filled, grown 2 px: what a text detector that hands over word boxes gives
  B2L  B2 less every long line's ink: line core (straight 35 px in the ink grown 1 px) and the gap-tolerant straight
       lines of make_masks2.py, grown 1 px. Boxes that never take a line's ink. Uses no truth
Writes masks/44_map_B2.png, 44_map_B2L.png and masks/boxes44.json."""
import os, sys, json
import numpy as np, cv2
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); MK = os.path.join(ROOT, 'masks')
src = sys.argv[1] if len(sys.argv) > 1 else 'I2'
S = cv2.imread(os.path.join(MK, f'44_map_{src}.png'), 0) > 0; H, W = S.shape
unp = lambda f: np.unpackbits(np.load(os.path.join(MK, f)))[:H * W].reshape(H, W) > 0
lines = cv2.dilate((unp('44_linecore.npy') | unp('44_glc.npy')).astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
J = cv2.morphologyEx(S.astype(np.uint8), cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))
n, lab, st, _ = cv2.connectedComponentsWithStats(J, connectivity=8)
ys, xs = np.nonzero(lab); l = lab[ys, xs]; o = np.argsort(l, kind='stable'); ys, xs, l = ys[o], xs[o], l[o]; cuts = np.searchsorted(l, np.arange(1, n + 1))
B = np.zeros((H, W), np.uint8)
for i in range(1, n):
    a, b = cuts[i - 1], cuts[i]
    if b - a < 6: continue
    (cx, cy), (rw, rh), ang = cv2.minAreaRect(np.c_[xs[a:b], ys[a:b]].astype(np.float32))
    cv2.fillPoly(B, [np.round(cv2.boxPoints(((cx, cy), (rw + 4, rh + 4), ang))).astype(np.int32)], 1)
B = B > 0; BL = B & ~lines
B0 = cv2.imread(os.path.join(ROOT, 'inputs', '44_bins_ref.png'), 0); rec = dict(src=src, groups=int(n - 1))
for k, m in (('B2', B), ('B2L', BL)):
    cv2.imwrite(os.path.join(MK, f'44_map_{k}.png'), m.astype(np.uint8) * 255)
    rec[k] = dict(px=int(m.sum()), by_ref_bin={str(b): int(c) for b, c in enumerate(np.bincount(B0[m], minlength=10)) if c})
print(json.dumps(rec)); json.dump(rec, open(os.path.join(MK, 'boxes44.json'), 'w'), indent=1)
