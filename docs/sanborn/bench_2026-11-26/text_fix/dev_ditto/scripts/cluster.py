"""Labelling aid: group the ink in a targeted crop's scope that no word box covers yet into clusters, scan only
(dev_ditto, 26 Nov 2026).

    cd data/sanborn
    python -B bench_2026-11-26/text_fix/dev_ditto/scripts/cluster.py TRUTHDIR ID [--gap 4] [--scale 4]
    python -B bench_2026-11-26/text_fix/dev_ditto/scripts/cluster.py TRUTHDIR ID --emit "3=lot:57 5=story:2 7=lotdim:25' 9=house:?:unsure"

Small pieces (box side < 46 px) meeting the scope and not inside a word box are grouped (pieces within --gap px of
each other join). Each cluster: number, box (full-plate px, inclusive), px. Picture TRUTHDIR/check/ID_clusters.png:
the scope regions, ink dark, word boxes (targets green, others magenta), clusters cyan with their number.
--emit appends 'B x0 y0 x1 y1 | reading | kind [| flags]' lines to annot/ID.txt for the clusters named (n=kind:reading[:flags]).
Clusters not named stay not text (lines' stubs, specks, ticks, dashes, hooks). Never reads a finder output or bins."""
import json, os, sys
sys.dont_write_bytecode = True
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common import window
import build_dd

a = sys.argv; TD = os.path.abspath(a[1]); tid = a[2]
gap = int(a[a.index('--gap') + 1]) if '--gap' in a else 4
sc = float(a[a.index('--scale') + 1]) if '--scale' in a else 4
crops = json.load(open(os.path.join(TD, 'crops.json'))); c = crops[tid]; p = c['plate']; X0, Y0, X1, Y1 = c['win']
words, _ = build_dd.parse(os.path.join(TD, 'annot', f'{tid}.txt'))
pad = int(c.get('scope_pad', 25))
def wbox(w):
    if w['box']: return [int(v) for v in w['geo']]
    x1, y1, x2, y2, h = w['geo']; return [int(min(x1, x2) - h / 2), int(min(y1, y2) - h / 2), int(max(x1, x2) + h / 2), int(max(y1, y2) + h / 2)]
allw = [(wbox(w), build_dd.is_target(w), w) for w in words]
if c.get('scope') == 'window': scopes = [[X0, Y0, X1 - 1, Y1 - 1]]
else: scopes = [[max(X0, b[0] - pad), max(Y0, b[1] - pad), min(X1 - 1, b[2] + pad), min(Y1 - 1, b[3] + pad)] for b, t, _ in allw if t]
img, lab, ink, _ = window(p, X0, Y0, X1, Y1)
n, lb, st, _ = cv2.connectedComponentsWithStats(ink.astype(np.uint8), connectivity=8)
scm = np.zeros(ink.shape, bool)
for s in scopes: scm[s[1] - Y0:s[3] - Y0 + 1, s[0] - X0:s[2] - X0 + 1] = True
keep = np.zeros(n, bool)
for k in np.unique(lb[scm & ink]):
    if k == 0: continue
    bx, by, bw, bh, A = st[k]
    if max(bw, bh) >= 46: continue
    b = [bx + X0, by + Y0, bx + bw - 1 + X0, by + bh - 1 + Y0]
    if any(b[0] >= q[0] - 1 and b[1] >= q[1] - 1 and b[2] <= q[2] + 1 and b[3] <= q[3] + 1 for q, _, _ in allw): continue
    keep[k] = True
m = keep[lb].astype(np.uint8)
g = cv2.dilate(m, np.ones((2 * gap + 1, 2 * gap + 1), np.uint8))
nc, cl, cst, _ = cv2.connectedComponentsWithStats(g, connectivity=8)
cls = []
for i in range(1, nc):
    mm = (cl == i) & (m > 0)
    if not mm.any(): continue
    ys, xs = np.nonzero(mm)
    cls.append(dict(n=len(cls), box=[int(xs.min() + X0), int(ys.min() + Y0), int(xs.max() + X0), int(ys.max() + Y0)], px=int(mm.sum())))
if '--emit' in a:
    spec = a[a.index('--emit') + 1].split()
    with open(os.path.join(TD, 'annot', f'{tid}.txt'), 'a', encoding='utf8') as f:
        for s in spec:
            i, rest = s.split('=', 1); parts = rest.split(':'); kind = parts[0]; rd = parts[1] if len(parts) > 1 else '?'
            fl = ' '.join(parts[2:]) if len(parts) > 2 else ''
            b = cls[int(i)]['box']; f.write(f"B {b[0]} {b[1]} {b[2]} {b[3]} | {rd} | {kind}" + (f' | {fl}' if fl else '') + '\n')
    print('appended', len(spec), 'lines'); sys.exit()
for d in cls: print(f"{d['n']:3d} {d['box'][0]},{d['box'][1]}-{d['box'][2]},{d['box'][3]} px {d['px']}")
# picture: merged scope regions
reg = []
for s in scopes:
    for q in reg:
        if not (s[2] + 5 < q[0] or q[2] + 5 < s[0] or s[3] + 5 < q[1] or q[3] + 5 < s[1]):
            q[0], q[1], q[2], q[3] = min(q[0], s[0]), min(q[1], s[1]), max(q[2], s[2]), max(q[3], s[3]); break
    else: reg.append(list(s))
cells = []
for x0, y0, x1, y1 in reg:
    k = min(sc, 1300 / max(1, x1 - x0 + 1))
    im = img[y0 - Y0:y1 - Y0 + 1, x0 - X0:x1 - X0 + 1]; I = ink[y0 - Y0:y1 - Y0 + 1, x0 - X0:x1 - X0 + 1]
    o = (im.astype(np.float32) * 0.6 + 255 * 0.4).astype(np.uint8); o[I] = (im[I] * 0.45).astype(np.uint8)
    B = cv2.resize(o, None, fx=k, fy=k, interpolation=cv2.INTER_NEAREST)
    R = lambda b: ((int((b[0] - x0) * k) - 1, int((b[1] - y0) * k) - 1), (int((b[2] + 1 - x0) * k), int((b[3] + 1 - y0) * k)))
    for b, t, w in allw:
        p0, p1 = R(b); cv2.rectangle(B, p0, p1, (0, 170, 0) if t else (200, 0, 200), 1)
    for d in cls:
        b = d['box']
        if b[2] < x0 or b[0] > x1 or b[3] < y0 or b[1] > y1: continue
        p0, p1 = R(b); cv2.rectangle(B, p0, p1, (230, 190, 0), 1)
        cv2.putText(B, str(d['n']), (p1[0] + 1, p0[1] + 9), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (220, 80, 0), 1)
    C = cv2.copyMakeBorder(B, 12, 2, 2, 2, cv2.BORDER_CONSTANT, value=(255, 255, 255))
    cv2.putText(C, f'{tid} {x0},{y0}-{x1},{y1}', (2, 10), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 0), 1)
    cells.append(C)
rows, row, rw = [], [], 0
for C in cells:
    if rw + C.shape[1] > 1400 and row: rows.append(row); row, rw = [], 0
    row.append(C); rw += C.shape[1] + 4
rows.append(row)
H = sum(max(C.shape[0] for C in r) + 4 for r in rows); Wd = max(sum(C.shape[1] + 4 for C in r) for r in rows)
G = np.full((H, Wd, 3), 190, np.uint8); y = 0
for r in rows:
    x = 0
    for C in r: G[y:y + C.shape[0], x:x + C.shape[1]] = C; x += C.shape[1] + 4
    y += max(C.shape[0] for C in r) + 4
f = os.path.join(TD, 'check', f'{tid}_clusters.png'); cv2.imwrite(f, G); print(f, G.shape)
