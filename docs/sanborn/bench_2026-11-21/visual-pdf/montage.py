"""Pair overlays side by side for checking: python montage.py SRC_DIR SUFFIX OUT_PREFIX [W]  (e.g. maparea_check _map_area.jpg mont/ma 760)"""
import glob, os, sys
import numpy as np, cv2
src, suf, outp = sys.argv[1], sys.argv[2], sys.argv[3]; W = int(sys.argv[4]) if len(sys.argv) > 4 else 760
fs = sorted(glob.glob(os.path.join(src, '*' + suf)), key=lambda p: int(''.join(c for c in os.path.basename(p).split('_')[0] if c.isdigit())))
os.makedirs(os.path.dirname(outp) or '.', exist_ok=True)
ims = []
for f in fs:
    im = cv2.imread(f); s = W / im.shape[1]; ims.append(cv2.resize(im, None, fx=s, fy=s, interpolation=cv2.INTER_AREA))
for k in range(0, len(ims), 2):
    pair = ims[k:k + 2]
    h = max(p.shape[0] for p in pair)
    pair = [cv2.copyMakeBorder(p, 0, h - p.shape[0], 0, 4, cv2.BORDER_CONSTANT, value=(255, 255, 255)) for p in pair]
    cv2.imwrite(f'{outp}_{k // 2:02d}.jpg', np.hstack(pair), [cv2.IMWRITE_JPEG_QUALITY, 85])
print(len(ims), 'images')
