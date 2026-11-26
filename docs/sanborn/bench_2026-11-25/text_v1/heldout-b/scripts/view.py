"""Look at the raw scan (no finder, no words output). python -B view.py PLATE x0 y0 x1 y1 scale out.jpg [grid]
Writes a crop of cufp/22-PLATE.jpg resized by `scale`, with a light grid every `grid` full px (default 100) labelled
in full-plate px, so positions can be read off the picture."""
import sys, os
import numpy as np, cv2

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))   # data/sanborn


def main():
    p = sys.argv[1]; x0, y0, x1, y1 = [int(v) for v in sys.argv[2:6]]; s = float(sys.argv[6]); out = sys.argv[7]
    grid = int(sys.argv[8]) if len(sys.argv) > 8 else 100
    im = cv2.imread(os.path.join(ROOT, 'cufp', f'22-{p}.jpg'))
    c = im[y0:y1, x0:x1]
    c = cv2.resize(c, None, fx=s, fy=s, interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC)
    if grid > 0:
        for gx in range((x0 // grid + 1) * grid, x1, grid):
            X = int((gx - x0) * s); cv2.line(c, (X, 0), (X, c.shape[0]), (255, 160, 0), 1)
            cv2.putText(c, str(gx), (X + 2, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 0), 1)
        for gy in range((y0 // grid + 1) * grid, y1, grid):
            Y = int((gy - y0) * s); cv2.line(c, (0, Y), (c.shape[1], Y), (255, 160, 0), 1)
            cv2.putText(c, str(gy), (2, Y - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 0), 1)
    cv2.imwrite(out, c, [cv2.IMWRITE_JPEG_QUALITY, 92])


if __name__ == '__main__':
    main()
