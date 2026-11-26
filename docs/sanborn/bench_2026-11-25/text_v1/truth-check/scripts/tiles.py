"""tiles.py CROP [--tw 375 --th 250 --s 2 --fixed --boxes] - side-by-side tiles: scan | truth overlay, with a grid in
full-plate coordinates. Text red, not text blue, don't care yellow, word boxes green (with --boxes).
Also:  tiles.py CROP --zoom X0 Y0 X1 Y1 S  (plate coords) for one zoom."""
import sys, os, argparse
import numpy as np, cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tc


def panel(cid, x0, y0, x1, y1, s, fixed, boxes, gstep):
    c = tc.crops_all()[cid]; wx, wy = c['win'][:2]
    sc = tc.scan(cid); tr = tc.truth(cid, fixed); W = tc.words(cid, fixed)['words']
    a, b, cc, d = x0 - wx, y0 - wy, x1 - wx, y1 - wy
    a, b = max(0, a), max(0, b); cc, d = min(sc.shape[1], cc), min(sc.shape[0], d)
    s1 = sc[b:d, a:cc]; t1 = tr[b:d, a:cc]
    L = cv2.resize(s1, None, fx=s, fy=s, interpolation=cv2.INTER_NEAREST)
    R = cv2.resize(tc.overlay(s1, t1), None, fx=s, fy=s, interpolation=cv2.INTER_NEAREST)
    if boxes: tc.draw_boxes(R, W, np.array([wx + a, wy + b]), s)
    for im in (L, R): tc.grid(im, s, gstep, (wx + a - (wx + a) % 1, wy + b))
    sep = np.full((L.shape[0], 6, 3), 255, np.uint8)
    return np.hstack([L, sep, R])


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('cid')
    ap.add_argument('--tw', type=int, default=375); ap.add_argument('--th', type=int, default=250)
    ap.add_argument('--s', type=float, default=2); ap.add_argument('--fixed', action='store_true')
    ap.add_argument('--boxes', action='store_true'); ap.add_argument('--zoom', nargs=5, type=float)
    ap.add_argument('--grid', type=int, default=50); ap.add_argument('--name', default='')
    a = ap.parse_args()
    os.makedirs(tc.PICS, exist_ok=True)
    c = tc.crops_all()[a.cid]; x0, y0, x1, y1 = c['win']; tag = 'fx' if a.fixed else 'v'
    if a.zoom:
        X0, Y0, X1, Y1, S = a.zoom
        im = panel(a.cid, int(X0), int(Y0), int(X1), int(Y1), S, a.fixed, a.boxes, a.grid)
        p = os.path.join(tc.PICS, f'{a.cid}_z{a.name}_{int(X0)}_{int(Y0)}.png'); cv2.imwrite(p, im); print(p); return
    r = 0
    for ty in range(y0, y1, a.th):
        cl = 0
        for tx in range(x0, x1, a.tw):
            im = panel(a.cid, tx, ty, min(x1, tx + a.tw), min(y1, ty + a.th), a.s, a.fixed, a.boxes, a.grid)
            p = os.path.join(tc.PICS, f'{a.cid}_{tag}_{r}{cl}.jpg'); cv2.imwrite(p, im, [cv2.IMWRITE_JPEG_QUALITY, 92]); cl += 1
        r += 1
    print('rows', r, 'cols', cl)


if __name__ == '__main__':
    main()
