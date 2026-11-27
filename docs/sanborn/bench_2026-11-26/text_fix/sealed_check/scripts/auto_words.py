"""Propose word lines for glyph pieces cut by the scope edge (sealed cross-check helper; scan only, decides nothing).
    cd data/sanborn
    python -B .../auto_words.py EDGE.json [--out PROPOSALS.json]
For each edge piece (edge_glyphs.py), the glyph ink near it (ink less straight runs of 41 px or more) is grouped by a
5 x 5 dilation; the group holding the piece gives a rotated box (cv2.minAreaRect), written as an annotation centre line
x1 y1 x2 y2 h (reading direction = the long side, left to right or reading upwards). A sheet shows every proposal on the
scan at 5x (pics/auto_words_NN.png) so that each one is accepted with its reading and kind, or rejected, by eye."""
import os, sys, json, math, argparse
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import numpy as np, cv2
from common import FINAL, window, line_mask, jdump
ap = argparse.ArgumentParser(); ap.add_argument('edge'); ap.add_argument('--out', default=os.path.join(HERE, '..', 'checks', 'auto_words.json')); a = ap.parse_args()
crops = json.load(open(os.path.join(FINAL, 'crops.json'), encoding='utf8'))
E = json.load(open(a.edge))['suspects']; props = []; cells = []
seen = set()
for k, s in enumerate(E):
    c = crops[s['crop']]; X0, Y0, X1, Y1 = c['win']; P = 60
    im, _, ink, (wx0, wy0, _, _) = window(c['plate'], X0 - P, Y0 - P, X1 + P, Y1 + P)
    ln = line_mask(ink, 41, nang=72); ln = cv2.dilate(ln.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
    gl = ink & ~ln
    n, lb = cv2.connectedComponents(cv2.dilate(gl.astype(np.uint8), np.ones((5, 5), np.uint8)), connectivity=8)
    bx = s['box']; sub = lb[bx[1] - wy0:bx[3] - wy0, bx[0] - wx0:bx[2] - wx0][gl[bx[1] - wy0:bx[3] - wy0, bx[0] - wx0:bx[2] - wx0]]
    if not len(sub): props.append(dict(k=k, crop=s['crop'], status='no glyph ink')); continue
    g = np.bincount(sub[sub > 0]).argmax() if (sub > 0).any() else 0
    key = (s['crop'], int(g))
    m = (lb == g) & gl; ys, xs = np.nonzero(m)
    if len(xs) > 3000 or (xs.max() - xs.min()) > 220 or (ys.max() - ys.min()) > 220:
        props.append(dict(k=k, crop=s['crop'], status='group too big')); continue
    (cx, cy), (w, h), ang = cv2.minAreaRect(np.stack([xs, ys], 1).astype(np.float32))
    if h > w: w, h = h, w; ang += 90
    while ang > 90: ang -= 180
    while ang <= -90: ang += 180
    if ang > 80: ang -= 180     # near vertical: read upwards
    u = np.array([math.cos(math.radians(ang)), math.sin(math.radians(ang))])
    p1 = np.array([cx + wx0, cy + wy0]) - u * w / 2; p2 = np.array([cx + wx0, cy + wy0]) + u * w / 2
    line = f'{p1[0]:.0f} {p1[1]:.0f} {p2[0]:.0f} {p2[1]:.0f} {h + 2:.0f}'
    dup = key in seen; seen.add(key)
    props.append(dict(k=k, crop=s['crop'], status='dup' if dup else 'ok', line=line, group_px=int(len(xs)), bbox=[int(xs.min() + wx0), int(ys.min() + wy0), int(xs.max() + wx0 + 1), int(ys.max() + wy0 + 1)]))
    if dup: continue
    x0, y0, x1, y1 = xs.min() - 12, ys.min() - 12, xs.max() + 13, ys.max() + 13
    z = 5; A = cv2.resize(im[max(0, y0):y1, max(0, x0):x1], None, fx=z, fy=z, interpolation=cv2.INTER_NEAREST)
    rect = cv2.boxPoints(((cx - max(0, x0), cy - max(0, y0)), (w + 2, h + 2), ang)) * z
    cv2.polylines(A, [np.round(rect).astype(np.int32)], True, (255, 0, 200), 2)
    # the scope edge in green
    R = json.load(open(os.path.join(FINAL, f"{s['crop']}_words.json"), encoding='utf8'))
    for r in R['scope']:
        q = (np.array([[r[0], r[1]], [r[2], r[1]], [r[2], r[3]], [r[0], r[3]]]) - [wx0 + max(0, x0), wy0 + max(0, y0)]) * z
        cv2.polylines(A, [np.round(q).astype(np.int32)], True, (0, 170, 0), 1)
    t = np.full((A.shape[0] + 16, max(A.shape[1], 260), 3), 255, np.uint8); t[16:, :A.shape[1]] = A
    cv2.putText(t, f"{k}:{s['crop']} {line}", (2, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (120, 0, 0), 1); cells.append(t)
jdump(props, a.out)
per = 24; cols = 6
for s0 in range(0, len(cells), per):
    cs = cells[s0:s0 + per]; rows = [cs[i:i + cols] for i in range(0, len(cs), cols)]
    cw = min(520, max(c.shape[1] for c in cs)); H = sum(min(420, max(c.shape[0] for c in r)) + 6 for r in rows)
    out = np.full((H, cols * (cw + 8), 3), 255, np.uint8); y = 0
    for r in rows:
        x = 0; rh = min(420, max(c.shape[0] for c in r))
        for c in r: cc = c[:rh, :cw]; out[y:y + cc.shape[0], x:x + cc.shape[1]] = cc; x += cw + 8
        y += rh + 6
    p = os.path.join(HERE, '..', 'pics', f'auto_words_{s0 // per:02d}.png'); cv2.imwrite(p, out); print(p, out.shape[1], 'x', out.shape[0])
from collections import Counter
print(Counter(p['status'] for p in props))
