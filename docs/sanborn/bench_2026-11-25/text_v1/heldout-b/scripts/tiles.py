"""Reading tiles of a held-out crop, from the raw scan only.  python -B tiles.py H3 tw th scale [ctx]
work/<crop>_read_RC.jpg: tile R,C of the window (tw x th full px, plus ctx px of context shown dimmed), enlarged by
`scale`, with a faint grid every 50 full px labelled in full-plate px on the edges."""
import sys, os
import numpy as np, cv2
from hcommon import CROPS, WORK, plate_img


def render(p, x0, y0, x1, y1, s, inner=None, grid=50, ink=None):
    im = plate_img(p)
    c = im[y0:y1, x0:x1].copy()
    if inner is not None:                                   # dim the context outside the tile proper
        ix0, iy0, ix1, iy1 = inner; m = np.ones(c.shape[:2], bool); m[iy0 - y0:iy1 - y0, ix0 - x0:ix1 - x0] = False
        c[m] = (0.55 * c[m] + 0.45 * 255).astype(np.uint8)
    c = cv2.resize(c, None, fx=s, fy=s, interpolation=cv2.INTER_CUBIC)
    for gx in range((x0 // grid + 1) * grid, x1, grid):
        X = int(round((gx - x0) * s)); col = (255, 120, 0) if gx % 100 == 0 else (255, 200, 120)
        for Y in range(0, c.shape[0], 6): c[Y:Y + 2, X] = col
        cv2.putText(c, str(gx), (X + 2, 11), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (200, 0, 0), 1)
    for gy in range((y0 // grid + 1) * grid, y1, grid):
        Y = int(round((gy - y0) * s)); col = (255, 120, 0) if gy % 100 == 0 else (255, 200, 120)
        for X in range(0, c.shape[1], 6): c[Y, X:X + 2] = col
        cv2.putText(c, str(gy), (2, Y - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (200, 0, 0), 1)
    return c


def main():
    cid = sys.argv[1]; tw, th = int(sys.argv[2]), int(sys.argv[3]); s = float(sys.argv[4])
    ctx = int(sys.argv[5]) if len(sys.argv) > 5 else 20
    cr = CROPS[cid]; p = cr['plate']; X0, Y0, X1, Y1 = cr['win']
    for r, ty in enumerate(range(Y0, Y1, th)):
        for cc, tx in enumerate(range(X0, X1, tw)):
            ex, ey = min(tx + tw, X1), min(ty + th, Y1)
            img = render(p, tx - ctx, ty - ctx, ex + ctx, ey + ctx, s, inner=(tx, ty, ex, ey))
            cv2.imwrite(os.path.join(WORK, f'{cid}_read_{r}{cc}.jpg'), img, [cv2.IMWRITE_JPEG_QUALITY, 92])
            print(cid, r, cc, tx, ty, ex, ey)


if __name__ == '__main__':
    main()
