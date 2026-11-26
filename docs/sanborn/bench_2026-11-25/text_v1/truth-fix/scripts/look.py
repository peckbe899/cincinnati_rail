"""Pictures for checking truth v2 by eye (25 Nov 2026).

    cd data/sanborn
    python -B bench_2026-11-25/text_v1/truth-fix/scripts/look.py zoom T1 x0 y0 x1 y1 [--scale 2] [--name N] [--truth DIR] [--noboxes]
    python -B bench_2026-11-25/text_v1/truth-fix/scripts/look.py tiles T1 [--tile 750 500] [--scale 1] [--truth DIR]

Left: the scan. Right: the truth - text red, non-text ink blue, don't care orange, paper the faded scan; word boxes thin
magenta with their annotation line number. Coordinates are full-plate px. Writes text_v1/truth-fix/pics/."""
import json, os, sys
sys.dont_write_bytecode = True
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); FIX = os.path.normpath(os.path.join(HERE, '..'))
ROOT = os.path.normpath(os.path.join(FIX, '..', '..', '..'))
PICS = os.path.join(FIX, 'pics'); os.makedirs(PICS, exist_ok=True)
arg = sys.argv


def opt(name, n=1, d=None):
    if name not in arg: return d
    i = arg.index(name); v = arg[i + 1:i + 1 + n]; return v if n > 1 else v[0]


TRD = opt('--truth', d=os.path.join(FIX, '..', 'truth'))
crops = json.load(open(os.path.join(TRD, 'crops.json')))
_c = {}


def plate(N):
    if N not in _c: _c[N] = cv2.imread(os.path.join(ROOT, 'cufp', f'22-{N}.jpg'))
    return _c[N]


def panel(tid, x0, y0, x1, y1, sc, boxes=True):
    c = crops[tid]; N = c['plate']; X0, Y0, X1, Y1 = c['win']
    t = cv2.imread(os.path.join(TRD, f'{tid}_mask.png'), 0)
    im = plate(N)[y0:y1, x0:x1].copy()
    tt = np.zeros((y1 - y0, x1 - x0), np.uint8)
    ax0, ay0, ax1, ay1 = max(x0, X0), max(y0, Y0), min(x1, X1), min(y1, Y1)
    if ax1 > ax0 and ay1 > ay0: tt[ay0 - y0:ay1 - y0, ax0 - x0:ax1 - x0] = t[ay0 - Y0:ay1 - Y0, ax0 - X0:ax1 - X0]
    o = (im.astype(np.float32) * 0.35 + 255 * 0.65).astype(np.uint8)
    for v, col in {1: (200, 90, 0), 2: (0, 0, 230), 3: (0, 160, 255)}.items(): o[tt == v] = col
    A = cv2.resize(im, None, fx=sc, fy=sc, interpolation=cv2.INTER_NEAREST if sc >= 1 else cv2.INTER_AREA)
    B = cv2.resize(o, None, fx=sc, fy=sc, interpolation=cv2.INTER_NEAREST if sc >= 1 else cv2.INTER_AREA)
    if boxes:
        W = json.load(open(os.path.join(TRD, f'{tid}_words.json'), encoding='utf8'))['words']
        for w in W:
            q = (np.array(w['poly']) - [x0, y0]) * sc
            if q[:, 0].max() < 0 or q[:, 1].max() < 0 or q[:, 0].min() > B.shape[1] or q[:, 1].min() > B.shape[0]: continue
            cv2.polylines(B, [np.round(q).astype(np.int32)], True, (220, 120, 230), 1)
            k = q[np.argmin(q[:, 1])]
            cv2.putText(B, str(w['annot_line']), (int(k[0]) + 2, int(k[1]) - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.33, (150, 0, 150), 1)
    fine = int(opt('--fine', d='0'))
    if fine:   # faint grid lines every `fine` px over both panels, labelled every 50 px
        for gx in range((x0 // fine + 1) * fine, x1, fine):
            X = int((gx - x0) * sc); A[:, X] = A[:, X] // 2 + (0, 0, 120); B[:, X] = B[:, X] // 2 + (0, 100, 0)
        for gy in range((y0 // fine + 1) * fine, y1, fine):
            Y = int((gy - y0) * sc); A[Y, :] = A[Y, :] // 2 + (0, 0, 120); B[Y, :] = B[Y, :] // 2 + (0, 100, 0)
        for gx in range((x0 // 50 + 1) * 50, x1, 50): cv2.putText(B, str(gx), (int((gx - x0) * sc) + 2, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 120, 0), 1)
        for gy in range((y0 // 50 + 1) * 50, y1, 50): cv2.putText(B, str(gy), (2, int((gy - y0) * sc) - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 120, 0), 1)
    # 50 px grid ticks with full-plate coordinates on the scan panel
    for gx in range((x0 // 50 + 1) * 50, x1, 50):
        X = int((gx - x0) * sc); A[:6, X] = (0, 0, 255)
        if gx % 100 == 0: cv2.putText(A, str(gx), (X + 2, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 200), 1)
    for gy in range((y0 // 50 + 1) * 50, y1, 50):
        Y = int((gy - y0) * sc); A[Y, :6] = (0, 0, 255)
        if gy % 100 == 0: cv2.putText(A, str(gy), (2, Y - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 200), 1)
    return np.hstack([A, np.full((A.shape[0], 6, 3), 255, np.uint8), B])


if __name__ == '__main__':
    mode, tid = arg[1], arg[2]; sc = float(opt('--scale', d='1' if mode == 'tiles' else '2')); bx = '--noboxes' not in arg
    if mode == 'zoom':
        x0, y0, x1, y1 = [int(v) for v in arg[3:7]]
        P = panel(tid, x0, y0, x1, y1, sc, bx); name = opt('--name', d=f'{x0}_{y0}')
        f = os.path.join(PICS, f'zoom_{tid}_{name}.png'); cv2.imwrite(f, P); print(f)
    else:
        tw, th = [int(v) for v in opt('--tile', 2, ['750', '500'])]
        X0, Y0, X1, Y1 = crops[tid]['win']
        for r, yy in enumerate(range(Y0, Y1, th)):
            for cc, xx in enumerate(range(X0, X1, tw)):
                P = panel(tid, xx, yy, min(X1, xx + tw), min(Y1, yy + th), sc, bx)
                f = os.path.join(PICS, f'tile_{tid}_r{r}c{cc}.png'); cv2.imwrite(f, P); print(f)
