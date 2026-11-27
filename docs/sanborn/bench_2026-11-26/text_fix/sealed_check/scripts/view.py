"""Check pictures for the sealed cross-check: the scan beside the truth (scan and truth only; no method output).
    cd data/sanborn
    python -B .../view.py targets  KIND [--z 6] [--per 6] [--truth DIR] [--tag T]     every target word of a kind
    python -B .../view.py suspects FILE.json CHECK [--z 6] [--per 24] [--maxpx N]      suspects of one check
    python -B .../view.py tiles    CROP [--tw 375 --th 250 --z 2]                     tiles of a crop
    python -B .../view.py box      CROP x0 y0 x1 y1 [--z 6]                           one zoom
Colours on the truth side: text red, not text dark grey, don't care orange, paper white; outside a targeted scope the
picture is tinted blue; word boxes magenta (targets thicker); the box being checked green. Scan side: red ticks every
10 px, longer every 50, and the full-plate coordinates of the top-left corner in the label."""
import os, sys, json, math, argparse
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import numpy as np, cv2
from common import FINAL, window

PICS = os.path.join(HERE, '..', 'pics')
ap = argparse.ArgumentParser(); ap.add_argument('mode'); ap.add_argument('args', nargs='*')
ap.add_argument('--z', type=float, default=6); ap.add_argument('--per', type=int, default=0); ap.add_argument('--truth', default=FINAL)
ap.add_argument('--tag', default=''); ap.add_argument('--maxpx', type=int, default=10 ** 9); ap.add_argument('--minpx', type=int, default=0)
ap.add_argument('--tw', type=int, default=375); ap.add_argument('--th', type=int, default=250); ap.add_argument('--margin', type=int, default=0)
ap.add_argument('--cols', type=int, default=0); ap.add_argument('--fixed', type=int, default=0); ap.add_argument('--crop'); ap.add_argument('--start', type=int, default=0)
a = ap.parse_args()
CROPS = json.load(open(os.path.join(a.truth, 'crops.json'), encoding='utf8'))
_tc = {}


def truth(tid):
    if tid not in _tc:
        M = cv2.imread(os.path.join(a.truth, f'{tid}_mask.png'), 0)
        R = json.load(open(os.path.join(a.truth, f'{tid}_words.json'), encoding='utf8'))
        _tc[tid] = (M, R)
    return _tc[tid]


def cell(tid, box, z, margin, label=''):
    c = CROPS[tid]; p = c['plate']; X0, Y0, X1, Y1 = c['win']; M, R = truth(tid)
    x0, y0, x1, y1 = box[0] - margin, box[1] - margin, box[2] + margin, box[3] + margin
    im, _, ink, (wx0, wy0, wx1, wy1) = window(p, x0, y0, x1, y1)
    T = np.full(ink.shape, 255, np.uint8)  # 255 = outside the crop window
    ax0, ay0, ax1, ay1 = max(wx0, X0), max(wy0, Y0), min(wx1, X1), min(wy1, Y1)
    if ax1 > ax0 and ay1 > ay0: T[ay0 - wy0:ay1 - wy0, ax0 - wx0:ax1 - wx0] = M[ay0 - Y0:ay1 - Y0, ax0 - X0:ax1 - X0]
    col = (im * 0.3 + 255 * 0.7).astype(np.uint8)
    col[(T == 0) & ink] = (200, 200, 200)
    col[T == 1] = (70, 70, 70); col[T == 2] = (0, 0, 230); col[(T == 3) & ink] = (0, 170, 255)
    S = np.zeros(ink.shape, bool)
    if R.get('scope'):
        for r in R['scope']:
            S[max(0, r[1] - wy0):max(0, r[3] - wy0 + 1), max(0, r[0] - wx0):max(0, r[2] - wx0 + 1)] = True
    else: S[(T != 255)] = True
    col[~S] = (col[~S] * 0.55 + np.array([255, 190, 140]) * 0.45).astype(np.uint8)
    A = cv2.resize(im, None, fx=z, fy=z, interpolation=cv2.INTER_NEAREST if z >= 3 else cv2.INTER_CUBIC)
    B = cv2.resize(col, None, fx=z, fy=z, interpolation=cv2.INTER_NEAREST)
    for w in R['words']:
        P = (np.array(w['poly']) - [wx0, wy0]) * z
        if P[:, 0].max() < 0 or P[:, 1].max() < 0 or P[:, 0].min() > B.shape[1] or P[:, 1].min() > B.shape[0]: continue
        cv2.polylines(B, [np.round(P).astype(np.int32)], True, (255, 0, 200) if w.get('target') else (170, 0, 140), 2 if w.get('target') else 1)
    g = [(box[0] - wx0) * z, (box[1] - wy0) * z, (box[2] - wx0) * z, (box[3] - wy0) * z]
    if margin > 0: cv2.rectangle(B, (int(g[0]) - 2, int(g[1]) - 2), (int(g[2]) + 2, int(g[3]) + 2), (0, 190, 0), 1)
    for gx in range((wx0 // 10 + 1) * 10, wx1, 10):
        X = int((gx - wx0) * z); A[:4 if gx % 50 else 10, X] = (0, 0, 220); A[-(4 if gx % 50 else 10):, X] = (0, 0, 220)
    for gy in range((wy0 // 10 + 1) * 10, wy1, 10):
        Y = int((gy - wy0) * z); A[Y, :4 if gy % 50 else 10] = (0, 0, 220); A[Y, -(4 if gy % 50 else 10):] = (0, 0, 220)
    t = np.full((A.shape[0] + 16, 2 * A.shape[1] + 6, 3), 255, np.uint8); t[16:, :A.shape[1]] = A; t[16:, A.shape[1] + 6:] = B
    cv2.putText(t, f'{label} [{wx0},{wy0}] x{z:g}', (2, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (120, 0, 0), 1)
    return t


def sheet(cells, path, cols):
    if not cells: return
    rows = [cells[i:i + cols] for i in range(0, len(cells), cols)]
    cw = max(c.shape[1] for c in cells); H = sum(max(c.shape[0] for c in r) + 6 for r in rows)
    out = np.full((H, cols * (cw + 8), 3), 255, np.uint8); y = 0
    for r in rows:
        x = 0
        for c in r: out[y:y + c.shape[0], x:x + c.shape[1]] = c; x += cw + 8
        y += max(c.shape[0] for c in r) + 6
    os.makedirs(os.path.dirname(path), exist_ok=True); cv2.imwrite(path, out); print(path, out.shape[1], 'x', out.shape[0], len(cells), 'cells')


if a.mode == 'targets':
    kind = a.args[0]; L = []
    for tid, c in CROPS.items():
        if a.crop and not tid.startswith(a.crop): continue
        for w in truth(tid)[1]['words']:
            if w.get('target') and w['kind'] == kind: L.append((tid, w))
    per = a.per or (6 if kind == 'block' else 20); cols = a.cols or (2 if kind == 'block' else 5)
    m = a.margin or (30 if kind == 'block' else 14)
    for s in range(0, len(L), per):
        cells = [cell(t, w['aabb'], a.z, m, f"{w['id']} {w['reading']} ink {w['ink_px']} txt {w['text_px_final']}") for t, w in L[s:s + per]]
        sheet(cells, os.path.join(PICS, f'tg_{kind}{a.tag}_{s // per:02d}.png'), cols)
elif a.mode == 'suspects':
    S = [s for s in json.load(open(a.args[0]))['suspects'] if s['check'] == a.args[1] and a.minpx <= s.get('px', 0) <= a.maxpx]
    if a.crop: S = [s for s in S if s['crop'] in a.crop.split(',')]
    per = a.per or 24; cols = a.cols or 6; m = a.margin or 12
    for s0 in range(a.start, len(S), per):
        def fx(b):
            if not a.fixed: return b
            cx, cy = (b[0] + b[2]) // 2, (b[1] + b[3]) // 2; return [cx - a.fixed, cy - a.fixed, cx + a.fixed, cy + a.fixed]
        cells = [cell(s['crop'], fx(s['box']), a.z, 0 if a.fixed else m, f"{k}:{s['crop']} {s.get('px', '')}") for k, s in enumerate(S[s0:s0 + per], s0)]
        sheet(cells, os.path.join(PICS, f'sus_{a.args[1]}{a.tag}_{s0 // per:02d}.png'), cols)
elif a.mode == 'tiles':
    tid = a.args[0]; X0, Y0, X1, Y1 = CROPS[tid]['win']
    for r, y in enumerate(range(Y0, Y1, a.th)):
        for cc, x in enumerate(range(X0, X1, a.tw)):
            t = cell(tid, [x, y, min(X1, x + a.tw), min(Y1, y + a.th)], a.z, a.margin, f'{tid} r{r}c{cc}')
            p = os.path.join(PICS, 'tiles', f'{tid}_r{r}c{cc}.png'); os.makedirs(os.path.dirname(p), exist_ok=True); cv2.imwrite(p, t)
    print('tiles written')
elif a.mode == 'box':
    tid = a.args[0]; b = [int(v) for v in a.args[1:5]]
    t = cell(tid, b, a.z, a.margin, tid)
    p = os.path.join(PICS, f'box_{tid}_{b[0]}_{b[1]}{a.tag}.png'); cv2.imwrite(p, t); print(p, t.shape[1], 'x', t.shape[0])
