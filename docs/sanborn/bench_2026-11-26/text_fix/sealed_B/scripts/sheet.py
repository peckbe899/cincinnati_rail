"""Contact sheet of zoomed scan windows (scan only), each with full-plate px ticks, for finding and reading targets.
python -B sheet.py OUT.jpg COLS "TITLE|PLATE|X0|Y0|X1|Y1|SCALE[|GRID]" ...   (one quoted spec per panel)"""
import os, sys
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import numpy as np, cv2
from view import render


def sheet(specs, cols):
    panels = []
    for s in specs:
        f = s.split('|'); title, p = f[0], f[1]; x0, y0, x1, y1 = map(int, f[2:6]); sc = float(f[6]); g = int(f[7]) if len(f) > 7 else None
        im = render(p, x0, y0, x1, y1, sc, g)
        t = np.full((im.shape[0] + 18, im.shape[1], 3), 255, np.uint8); t[18:] = im
        cv2.putText(t, f'{title}  p{p} [{x0},{y0},{x1},{y1}] x{sc:g}', (2, 13), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 0, 160), 1)
        panels.append(t)
    rows = []
    for i in range(0, len(panels), cols):
        r = panels[i:i + cols]; h = max(p.shape[0] for p in r)
        r = [cv2.copyMakeBorder(p, 0, h - p.shape[0], 0, 6, cv2.BORDER_CONSTANT, value=(255, 255, 255)) for p in r]
        rows.append(np.hstack(r))
    w = max(r.shape[1] for r in rows)
    rows = [cv2.copyMakeBorder(r, 0, 6, 0, w - r.shape[1], cv2.BORDER_CONSTANT, value=(255, 255, 255)) for r in rows]
    return np.vstack(rows)


if __name__ == '__main__':
    out, cols = sys.argv[1], int(sys.argv[2])
    cv2.imwrite(out, sheet(sys.argv[3:], cols), [cv2.IMWRITE_JPEG_QUALITY, 90])
