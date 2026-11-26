"""rot.py X0 Y0 X1 Y1 f out.jpg: a window shown three ways side by side: as printed, turned 90 clockwise, turned 90 anticlockwise (reading aid)"""
import sys, cv2, numpy as np
X0, Y0, X1, Y1 = map(int, sys.argv[1:5]); f = float(sys.argv[5]); out = sys.argv[6]
plate = sys.argv[7] if len(sys.argv) > 7 else '90'
im = cv2.imread(f'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/cufp/22-{plate}.jpg')[Y0:Y1, X0:X1]
s = cv2.resize(im, None, fx=f, fy=f, interpolation=cv2.INTER_CUBIC)
a = cv2.rotate(s, cv2.ROTATE_90_CLOCKWISE); b = cv2.rotate(s, cv2.ROTATE_90_COUNTERCLOCKWISE)
H = max(s.shape[0], a.shape[0]); pad = lambda x: cv2.copyMakeBorder(x, 0, H - x.shape[0], 0, 10, cv2.BORDER_CONSTANT, value=(255, 255, 255))
cv2.imwrite(out, np.hstack([pad(s), pad(a), pad(b)]), [cv2.IMWRITE_JPEG_QUALITY, 92])
