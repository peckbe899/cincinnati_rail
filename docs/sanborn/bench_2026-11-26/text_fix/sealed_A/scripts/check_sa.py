"""Check pictures for the sealed A truth (26 Nov 2026): scan left, truth right. Scan and truth only (no bin, no finder).

    cd data/sanborn
    python -B bench_2026-11-26/text_fix/sealed_A/scripts/check_sa.py targets ID [ID ...]     one cell per target word
    python -B bench_2026-11-26/text_fix/sealed_A/scripts/check_sa.py tiles ID [--tile 375 250] [--scale 2]
    python -B bench_2026-11-26/text_fix/sealed_A/scripts/check_sa.py zoom ID x0 y0 x1 y1 [--scale 4] [--name N]

Truth colours: text red, not-text ink blue, don't care orange; outside the scored scope of a targeted crop the scan is
shown faded with no class colour, and the scope edge is drawn green. Word boxes thin magenta with their annotation line
number (target words thicker). A faint 10 px grid (labels every 50 px, full-plate px) on both panels.
targets: each target word's box grown by 35 px, at 4-8x. Writes sealed_A/pics/check/."""
import json, os, sys
sys.dont_write_bytecode = True
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common import plate_img
SA = os.path.normpath(os.path.join(HERE, '..')); TRD = os.path.join(SA, 'truth')
OUTD = os.path.join(SA, 'pics', 'check'); os.makedirs(OUTD, exist_ok=True)
arg = sys.argv


def opt(name, n=1, d=None):
    if name not in arg: return d
    i = arg.index(name); v = arg[i + 1:i + 1 + n]; return v if n > 1 else v[0]


crops = json.load(open(os.path.join(TRD, 'crops.json'), encoding='utf8'))


def load(tid):
    M = cv2.imread(os.path.join(TRD, f'{tid}_mask.png'), 0)
    W = json.load(open(os.path.join(TRD, f'{tid}_words.json'), encoding='utf8'))
    c = crops[tid]; X0, Y0, X1, Y1 = c['win']
    scope = np.ones(M.shape, bool)
    if c.get('kind') == 'targeted':
        scope[:] = False; pad = int(c.get('scope_pad', 25))
        for w in W['words']:
            if w.get('target'):
                a0, b0, a1, b1 = w['aabb']
                scope[max(0, b0 - pad - Y0):max(0, b1 + pad - Y0 + 1), max(0, a0 - pad - X0):max(0, a1 + pad - X0 + 1)] = True
    return M, W['words'], scope


def panel(tid, x0, y0, x1, y1, sc):
    c = crops[tid]; N = c['plate']; X0, Y0, X1, Y1 = c['win']
    M, words, scope = load(tid)
    im = plate_img(N)[y0:y1, x0:x1].copy()
    tt = np.full((y1 - y0, x1 - x0), 255, np.uint8); ss = np.zeros((y1 - y0, x1 - x0), bool)
    ax0, ay0, ax1, ay1 = max(x0, X0), max(y0, Y0), min(x1, X1), min(y1, Y1)
    if ax1 > ax0 and ay1 > ay0:
        tt[ay0 - y0:ay1 - y0, ax0 - x0:ax1 - x0] = M[ay0 - Y0:ay1 - Y0, ax0 - X0:ax1 - X0]
        ss[ay0 - y0:ay1 - y0, ax0 - x0:ax1 - x0] = scope[ay0 - Y0:ay1 - Y0, ax0 - X0:ax1 - X0]
    o = (im.astype(np.float32) * 0.35 + 255 * 0.65).astype(np.uint8)
    for v, col in {1: (200, 90, 0), 2: (0, 0, 230), 3: (0, 160, 255)}.items(): o[(tt == v) & ss] = col
    A = cv2.resize(im, None, fx=sc, fy=sc, interpolation=cv2.INTER_NEAREST)
    B = cv2.resize(o, None, fx=sc, fy=sc, interpolation=cv2.INTER_NEAREST)
    if not ss.all():   # scope edge
        e = cv2.resize(ss.astype(np.uint8), (B.shape[1], B.shape[0]), interpolation=cv2.INTER_NEAREST)
        edge = (cv2.dilate(e, np.ones((3, 3), np.uint8)) - e) > 0; B[edge] = (0, 170, 0)
    for w in words:
        q = (np.array(w['poly']) - [x0, y0]) * sc
        if q[:, 0].max() < 0 or q[:, 1].max() < 0 or q[:, 0].min() > B.shape[1] or q[:, 1].min() > B.shape[0]: continue
        cv2.polylines(B, [np.round(q).astype(np.int32)], True, (220, 0, 220) if w.get('target') else (220, 120, 230), 2 if w.get('target') else 1)
        k = q[np.argmin(q[:, 1])]
        cv2.putText(B, str(w['annot_line']), (int(k[0]) + 2, int(k[1]) - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (150, 0, 150), 1)
    g = 10 if sc >= 3 else 50
    for P_ in (A, B):
        for gx in range((x0 // g + 1) * g, x1, g):
            X = int((gx - x0) * sc); P_[:, X] = (P_[:, X].astype(int) * 3 // 4 + np.array([0, 40, 0])).clip(0, 255).astype(np.uint8)
        for gy in range((y0 // g + 1) * g, y1, g):
            Y = int((gy - y0) * sc); P_[Y, :] = (P_[Y, :].astype(int) * 3 // 4 + np.array([0, 40, 0])).clip(0, 255).astype(np.uint8)
    for gx in range((x0 // 50 + 1) * 50, x1, 50): cv2.putText(A, str(gx), (int((gx - x0) * sc) + 2, 11), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 200), 1)
    for gy in range((y0 // 50 + 1) * 50, y1, 50): cv2.putText(A, str(gy), (2, int((gy - y0) * sc) - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 200), 1)
    return np.hstack([A, np.full((A.shape[0], 6, 3), 255, np.uint8), B])


def grid(cells, cols):
    cols = min(cols, len(cells)); CW = max(c.shape[1] for c in cells); CH = max(c.shape[0] for c in cells); rows = (len(cells) + cols - 1) // cols
    G = np.full((rows * (CH + 4), cols * (CW + 4), 3), 190, np.uint8)
    for i, C in enumerate(cells):
        r, c = divmod(i, cols); G[r * (CH + 4):r * (CH + 4) + C.shape[0], c * (CW + 4):c * (CW + 4) + C.shape[1]] = C
    return G


if __name__ == '__main__':
    mode = arg[1]
    if mode == 'targets':
        for tid in [a for a in arg[2:] if not a.startswith('--')]:
            M, words, scope = load(tid); cells = []
            for w in words:
                if not w.get('target'): continue
                a0, b0, a1, b1 = w['aabb']; m = 35
                x0, y0, x1, y1 = a0 - m, b0 - m, a1 + m, b1 + m
                sc = max(4, min(8, 420 / max(x1 - x0, y1 - y0)))
                P = panel(tid, x0, y0, x1, y1, sc)
                C = np.full((P.shape[0] + 16, P.shape[1], 3), 255, np.uint8); C[16:] = P
                cv2.putText(C, f"{tid} line {w['annot_line']} {w['reading']!s} ({w['kind']}) ink {w['ink_px']} text {w.get('scored_text_px')} x{sc:.1f}",
                            (2, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)
                cells.append(C)
            for k in range(0, len(cells), 6):
                f = os.path.join(OUTD, f'tg_{tid}_{k // 6}.png'); cv2.imwrite(f, grid(cells[k:k + 6], 2 if cells[0].shape[1] > 500 else 3)); print(f)
    elif mode == 'tiles':
        tid = arg[2]; tw, th = [int(v) for v in opt('--tile', 2, ['375', '250'])]; sc = float(opt('--scale', d='2'))
        X0, Y0, X1, Y1 = crops[tid]['win']
        for r, yy in enumerate(range(Y0, Y1, th)):
            for cc, xx in enumerate(range(X0, X1, tw)):
                P = panel(tid, xx, yy, min(X1, xx + tw), min(Y1, yy + th), sc)
                f = os.path.join(OUTD, f'tile_{tid}_r{r}c{cc}.png'); cv2.imwrite(f, P); print(f)
    else:
        tid = arg[2]; x0, y0, x1, y1 = [int(v) for v in arg[3:7]]; sc = float(opt('--scale', d='4'))
        f = os.path.join(OUTD, f"zoom_{tid}_{opt('--name', d=f'{x0}_{y0}')}.png"); cv2.imwrite(f, panel(tid, x0, y0, x1, y1, sc)); print(f)
