"""Put several pictures side by side (dev_block, 26 Nov 2026).

    python -B montage.py OUT.png IN1.png IN2.png ... [--cols 2] [--scale 1.0]"""
import sys
sys.dont_write_bytecode = True
import numpy as np, cv2

a = sys.argv[1:]; cols = int(a[a.index('--cols') + 1]) if '--cols' in a else 2; sc = float(a[a.index('--scale') + 1]) if '--scale' in a else 1.0
fs = [x for i, x in enumerate(a[1:], 1) if not x.startswith('--') and a[i - 1] not in ('--cols', '--scale')]
ims = [cv2.imread(f) for f in fs]
ims = [cv2.resize(i, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA) if sc != 1 else i for i in ims]
h = max(i.shape[0] for i in ims); w = max(i.shape[1] for i in ims)
ims = [cv2.copyMakeBorder(i, 0, h - i.shape[0] + 6, 0, w - i.shape[1] + 6, cv2.BORDER_CONSTANT, value=(255, 255, 255)) for i in ims]
while len(ims) % cols: ims.append(np.full_like(ims[0], 255))
G = np.vstack([np.hstack(ims[k:k + cols]) for k in range(0, len(ims), cols)])
cv2.imwrite(a[0], G); print(a[0], G.shape)
