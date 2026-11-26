"""Zoomed check of a built truth crop: python -B zc.py H4 x0 y0 x1 y1 scale out.jpg
Left: the scan; right: the mask (text red, don't care yellow, other ink grey), both enlarged, with a 10 px grid."""
import sys, os
import numpy as np, cv2
from hcommon import CROPS, OUT, WORK, plate_img


def main():
    cid = sys.argv[1]; x0, y0, x1, y1 = [int(v) for v in sys.argv[2:6]]; s = float(sys.argv[6]); out = sys.argv[7]
    cr = CROPS[cid]; X0, Y0, X1, Y1 = cr['win']
    m = cv2.imread(os.path.join(OUT, f'{cid}_mask.png'), 0)
    x0, y0, x1, y1 = max(x0, X0), max(y0, Y0), min(x1, X1), min(y1, Y1)
    im = plate_img(cr['plate'])[y0:y1, x0:x1].copy()
    mm = m[y0 - Y0:y1 - Y0, x0 - X0:x1 - X0]
    col = np.full_like(im, 250)
    col[mm == 1] = (120, 120, 120); col[mm == 2] = (0, 0, 230); col[mm == 3] = (0, 210, 255)
    a = cv2.resize(im, None, fx=s, fy=s, interpolation=cv2.INTER_NEAREST)
    b = cv2.resize(col, None, fx=s, fy=s, interpolation=cv2.INTER_NEAREST)
    for t in (a, b):
        for gx in range((x0 // 10 + 1) * 10, x1, 10):
            X = int((gx - x0) * s); t[:, X] = (255, 200, 120) if gx % 50 else (255, 90, 0)
        for gy in range((y0 // 10 + 1) * 10, y1, 10):
            Y = int((gy - y0) * s); t[Y, :] = (255, 200, 120) if gy % 50 else (255, 90, 0)
    for gx in range((x0 // 50 + 1) * 50, x1, 50):
        cv2.putText(b, str(gx), (int((gx - x0) * s) + 2, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 0, 0), 1)
    for gy in range((y0 // 50 + 1) * 50, y1, 50):
        cv2.putText(b, str(gy), (2, int((gy - y0) * s) - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 0, 0), 1)
    sep = np.full((a.shape[0], 6, 3), 255, np.uint8)
    cv2.imwrite(out, np.hstack([a, sep, b]), [cv2.IMWRITE_JPEG_QUALITY, 92])


if __name__ == '__main__':
    main()
