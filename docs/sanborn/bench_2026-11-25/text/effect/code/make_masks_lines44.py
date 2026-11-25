"""make_masks_lines44.py (text/effect, 25 Nov 2026): the plate-44 text masks for the line tests, beside make_masks.py's.
    cd data/sanborn; python -B bench_2026-11-25/text/effect/code/make_masks_lines44.py

  Sref  bin 8 of unet_data/44_bins.png (the sorting made with Ben's street map and his rail; copy inputs/44_bins_ref.png):
        the stand-in mask numbers_check.py used
  B     word boxes: Sref closed with a 9 px disc so the characters of one number or word join, each group's rotated
        bounding rectangle (cv2.minAreaRect) filled, grown 2 px. What a text detector that hands over boxes would give
  BL    B less the line core (ink a straight 35 px line fits, make_masks.py's 44_linecore) grown 1 px: boxes that never
        take a long straight line's ink. Uses no truth
Groups larger than 1500 px across (none expected) are skipped. Writes masks/44_map_{Sref,B,BL}.png and masks_44_lines.json."""
import os, json
import numpy as np, cv2
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); MK = os.path.join(ROOT, 'masks')
B0 = cv2.imread(os.path.join(ROOT, 'inputs', '44_bins_ref.png'), 0); H, W = B0.shape
S = (B0 == 8)
lc = np.unpackbits(np.load(os.path.join(MK, '44_linecore.npy')))[:H * W].reshape(H, W) > 0
J = cv2.morphologyEx(S.astype(np.uint8), cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))
n, lab, st, _ = cv2.connectedComponentsWithStats(J, connectivity=8)
Bx = np.zeros((H, W), np.uint8); ys, xs = np.nonzero(lab); order = np.argsort(lab[ys, xs], kind='stable'); ys, xs = ys[order], xs[order]
cuts = np.searchsorted(lab[ys, xs], np.arange(1, n + 1)); skipped = 0
for i in range(1, n):
    a, b = cuts[i - 1], cuts[i]
    if b - a < 6: continue
    if max(st[i, 2], st[i, 3]) > 1500: skipped += 1; continue
    r = cv2.minAreaRect(np.c_[xs[a:b], ys[a:b]].astype(np.float32)); (cx, cy), (rw, rh), ang = r
    box = cv2.boxPoints(((cx, cy), (rw + 4, rh + 4), ang)); cv2.fillPoly(Bx, [np.round(box).astype(np.int32)], 1)
B = Bx > 0; BL = B & ~(cv2.dilate(lc.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0)
rec = dict(groups=int(n - 1), skipped_large=skipped)
for k, m in (('Sref', S), ('B', B), ('BL', BL)):
    cv2.imwrite(os.path.join(MK, f'44_map_{k}.png'), m.astype(np.uint8) * 255)
    rec[k] = dict(px=int(m.sum()), ink_px=int((m & (B0 > 0)).sum()), by_bin={str(b): int(c) for b, c in enumerate(np.bincount(B0[m], minlength=10)) if c})
print(json.dumps(rec, indent=1)); json.dump(rec, open(os.path.join(MK, 'masks_44_lines.json'), 'w'), indent=1)
