"""1:1 tiles of a truth crop with a faint 50 px grid (labels every 100 px, full-plate coordinates), for reading the words
and placing them by eye.  python -B gridtiles.py T1 [--tw 750 --th 500]  -> truth/work/T1_grid_RC.jpg"""
import sys, os, json
import numpy as np, cv2
from common import INV, plate_img

CROPS = json.load(open(os.path.join(INV, 'truth', 'crops.json')))
WORK = os.path.join(INV, 'truth', 'work'); os.makedirs(WORK, exist_ok=True)


def gridtile(p, x0, y0, x1, y1):
    im = plate_img(p); H, W = im.shape[:2]
    t = np.full((y1 - y0, x1 - x0, 3), 255, np.uint8)
    a0, b0, a1, b1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
    t[b0 - y0:b1 - y0, a0 - x0:a1 - x0] = im[b0:b1, a0:a1]
    for gx in range((x0 // 50 + 1) * 50, x1, 50):
        col = (230, 160, 0) if gx % 100 == 0 else (240, 210, 150)
        t[:, gx - x0] = (t[:, gx - x0] * 0.5 + np.array(col) * 0.5).astype(np.uint8)
        if gx % 100 == 0: cv2.putText(t, str(gx), (gx - x0 + 2, 11), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (200, 0, 0), 1)
    for gy in range((y0 // 50 + 1) * 50, y1, 50):
        col = (230, 160, 0) if gy % 100 == 0 else (240, 210, 150)
        t[gy - y0, :] = (t[gy - y0, :] * 0.5 + np.array(col) * 0.5).astype(np.uint8)
        if gy % 100 == 0: cv2.putText(t, str(gy), (2, gy - y0 - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (200, 0, 0), 1)
    return t


if __name__ == '__main__':
    a = sys.argv; tid = a[1]
    tw = int(a[a.index('--tw') + 1]) if '--tw' in a else 750; th = int(a[a.index('--th') + 1]) if '--th' in a else 500
    sc = float(a[a.index('--scale') + 1]) if '--scale' in a else 1.0
    c = CROPS[tid]; X0, Y0, X1, Y1 = c['win']
    for r, ty in enumerate(range(Y0, Y1, th)):
        for cc, tx in enumerate(range(X0, X1, tw)):
            t = gridtile(c['plate'], tx - 25, ty - 25, min(tx + tw, X1) + 25, min(ty + th, Y1) + 25)
            if sc != 1.0: t = cv2.resize(t, None, fx=sc, fy=sc, interpolation=cv2.INTER_CUBIC)
            cv2.imwrite(os.path.join(WORK, f'{tid}_{"grid" if sc == 1.0 else "zoom"}_{r}{cc}.jpg'), t, [cv2.IMWRITE_JPEG_QUALITY, 92])
