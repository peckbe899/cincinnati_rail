"""Labelling aid for a targeted crop: every ink piece in the scored scope, numbered, scan only (dev_ditto, 26 Nov 2026).

    cd data/sanborn
    python -B bench_2026-11-26/text_fix/dev_ditto/scripts/scope.py TRUTHDIR ID [--scale 5] [--u 3,4,7]

Reads TRUTHDIR/crops.json and TRUTHDIR/annot/ID.txt (the targets: kind ditto or flag target; for scope 'window' the
whole window). Lists every 8-connected ink piece (L < 140 on the paper) that meets the scope, with its box (full-plate
px, inclusive), pixel count and whether a word box of the annotation already covers it (W) or not (-). Pieces whose box
is 46 px or more on a side are marked BIG (lines; left not text unless a word box takes a part). Writes
TRUTHDIR/check/ID_scope.png: each scope cluster at --scale, scan with thin boxes: targets green, other words magenta,
uncovered small pieces cyan with their number. --u 3,4,7 prints the union box of those pieces (for a B line).
Never reads a finder output or bins."""
import json, os, sys
sys.dont_write_bytecode = True
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common import window
import build_dd

a = sys.argv; TD = os.path.abspath(a[1]); tid = a[2]
sc = float(a[a.index('--scale') + 1]) if '--scale' in a else 5
crops = json.load(open(os.path.join(TD, 'crops.json'))); c = crops[tid]; p = c['plate']; X0, Y0, X1, Y1 = c['win']
words, boxes = build_dd.parse(os.path.join(TD, 'annot', f'{tid}.txt'))
pad = int(c.get('scope_pad', 25))
def wbox(w):
    if w['box']: return [int(v) for v in w['geo']]
    x1, y1, x2, y2, h = w['geo']; return [int(min(x1, x2) - h / 2), int(min(y1, y2) - h / 2), int(max(x1, x2) + h / 2), int(max(y1, y2) + h / 2)]
tg = [wbox(w) for w in words if build_dd.is_target(w)]
if c.get('scope') == 'window': scopes = [[X0, Y0, X1 - 1, Y1 - 1]]
else: scopes = [[max(X0, b[0] - pad), max(Y0, b[1] - pad), min(X1 - 1, b[2] + pad), min(Y1 - 1, b[3] + pad)] for b in tg]
img, lab, ink, (wx0, wy0, wx1, wy1) = window(p, X0, Y0, X1, Y1)
n, lb, st, cen = cv2.connectedComponentsWithStats(ink.astype(np.uint8), connectivity=8)
sc_m = np.zeros(ink.shape, bool)
for s in scopes: sc_m[s[1] - Y0:s[3] - Y0 + 1, s[0] - X0:s[2] - X0 + 1] = True
ids = np.unique(lb[sc_m & ink]); ids = ids[ids > 0]
allw = [(wbox(w), build_dd.is_target(w), w) for w in words]
pcs = []
for k in ids:
    bx, by, bw, bh, A = st[k]; b = [int(bx + X0), int(by + Y0), int(bx + bw - 1 + X0), int(by + bh - 1 + Y0)]
    cov = any(b[0] >= q[0] - 1 and b[1] >= q[1] - 1 and b[2] <= q[2] + 1 and b[3] <= q[3] + 1 for q, _, _ in allw)
    big = max(bw, bh) >= 46
    pcs.append(dict(n=len(pcs), k=int(k), box=b, px=int(A), big=big, cov=cov))
for d in pcs:
    print(f"{d['n']:3d} {'BIG' if d['big'] else '   '} {'W' if d['cov'] else '-'} {d['box'][0]},{d['box'][1]}-{d['box'][2]},{d['box'][3]} px {d['px']}")
if '--u' in a:
    sel = [int(v) for v in a[a.index('--u') + 1].split(',')]; bb = np.array([pcs[i]['box'] for i in sel])
    print('union:', bb[:, 0].min(), bb[:, 1].min(), bb[:, 2].max(), bb[:, 3].max())
# clusters of overlapping scopes
cl = []
for s in scopes:
    for q in cl:
        if not (s[2] < q[0] or q[2] < s[0] or s[3] < q[1] or q[3] < s[1]):
            q[0], q[1], q[2], q[3] = min(q[0], s[0]), min(q[1], s[1]), max(q[2], s[2]), max(q[3], s[3]); break
    else: cl.append(list(s))
cells = []
for q in cl:
    x0, y0, x1, y1 = q
    k = min(sc, 900 / max(1, x1 - x0 + 1))
    im = img[y0 - Y0:y1 - Y0 + 1, x0 - X0:x1 - X0 + 1].copy()
    o = (im.astype(np.float32) * 0.6 + 255 * 0.4).astype(np.uint8); I = ink[y0 - Y0:y1 - Y0 + 1, x0 - X0:x1 - X0 + 1]
    o[I] = (im[I] * 0.45).astype(np.uint8)
    B = cv2.resize(o, None, fx=k, fy=k, interpolation=cv2.INTER_NEAREST)
    for gx in range((x0 // 10 + 1) * 10, x1 + 1, 10):
        X = int((gx - x0) * k); B[:, X] = (B[:, X] * 0.7 + np.array([200, 200, 255]) * 0.3).astype(np.uint8)
        if gx % 50 == 0: cv2.putText(B, str(gx), (X + 1, 9), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 0, 200), 1)
    for gy in range((y0 // 10 + 1) * 10, y1 + 1, 10):
        Y = int((gy - y0) * k); B[Y, :] = (B[Y, :] * 0.7 + np.array([200, 200, 255]) * 0.3).astype(np.uint8)
        if gy % 50 == 0: cv2.putText(B, str(gy), (1, Y - 1), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 0, 200), 1)
    R = lambda b: ((int((b[0] - x0) * k) - 1, int((b[1] - y0) * k) - 1), (int((b[2] + 1 - x0) * k), int((b[3] + 1 - y0) * k)))
    for b, t, w in allw:
        p0, p1 = R(b); cv2.rectangle(B, p0, p1, (0, 170, 0) if t else (200, 0, 200), 1)
        cv2.putText(B, str(w['line']), (p0[0], p0[1] - 1), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 120, 0) if t else (150, 0, 150), 1)
    for d in pcs:
        b = d['box']
        if b[2] < x0 or b[0] > x1 or b[3] < y0 or b[1] > y1 or d['cov'] or d['big']: continue
        p0, p1 = R(b); cv2.rectangle(B, p0, p1, (230, 190, 0), 1)
        cv2.putText(B, str(d['n']), (p1[0] + 1, p0[1] + 8), cv2.FONT_HERSHEY_SIMPLEX, 0.33, (200, 100, 0), 1)
    C = cv2.copyMakeBorder(B, 12, 2, 2, 2, cv2.BORDER_CONSTANT, value=(255, 255, 255))
    cv2.putText(C, f'{tid} {p} {x0},{y0}-{x1},{y1}', (2, 10), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 0), 1)
    cells.append(C)
CW = max(x.shape[1] for x in cells); tot = []
row, rw = [], 0
for C in cells:
    if rw + C.shape[1] > 1400 and row: tot.append(row); row, rw = [], 0
    row.append(C); rw += C.shape[1] + 4
tot.append(row)
H = sum(max(C.shape[0] for C in r) + 4 for r in tot); Wd = max(sum(C.shape[1] + 4 for C in r) for r in tot)
G = np.full((H, Wd, 3), 190, np.uint8); y = 0
for r in tot:
    x = 0
    for C in r: G[y:y + C.shape[0], x:x + C.shape[1]] = C; x += C.shape[1] + 4
    y += max(C.shape[0] for C in r) + 4
os.makedirs(os.path.join(TD, 'check'), exist_ok=True); f = os.path.join(TD, 'check', f'{tid}_scope.png'); cv2.imwrite(f, G); print(f, G.shape)
