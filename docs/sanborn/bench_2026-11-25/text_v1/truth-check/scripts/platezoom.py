"""platezoom.py PLATE X0 Y0 X1 Y1 S NAME - a plain zoom of the scan (any part of the plate), for reading."""
import sys, os, cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tc
p, x0, y0, x1, y1, s, name = sys.argv[1], *map(int, sys.argv[2:6]), float(sys.argv[6]), sys.argv[7]
im = tc.plate_img(p)[y0:y1, x0:x1]
im = cv2.resize(im, None, fx=s, fy=s, interpolation=cv2.INTER_CUBIC)
out = os.path.join(tc.PICS, f'pz_{name}.png'); cv2.imwrite(out, im); print(out)
