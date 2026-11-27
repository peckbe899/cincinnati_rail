"""Picture of the scopes of a targeted crop at zoom Z (scan), with the uncovered glyph clusters of scope_pieces.py
boxed in blue and numbered, typed words in magenta, scopes in green. python -B scope_view.py OUT.jpg Z CROP"""
import os, sys, json, subprocess
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import numpy as np, cv2
from common import INV, window
out, Z, cid = sys.argv[1], float(sys.argv[2]), sys.argv[3]
crops = json.load(open(os.path.join(INV, 'truth', 'crops.json'), encoding='utf8')); c = crops[cid]
W = json.load(open(os.path.join(INV, 'truth', f'{cid}_words.json'), encoding='utf8'))['words']
S = c['scope']; x0 = min(r[0] for r in S) - 30; y0 = min(r[1] for r in S) - 30; x1 = max(r[2] for r in S) + 30; y1 = max(r[3] for r in S) + 30
txt = subprocess.run([sys.executable, '-B', os.path.join(HERE, 'scope_pieces.py'), cid], capture_output=True, text=True).stdout
cl = []
for ln in txt.splitlines():
    if ln.strip().startswith('x '):
        f = ln.split(); a = list(map(int, f[1].split('-'))); b = list(map(int, f[3].split('-'))); cl.append((a[0], b[0], a[1], b[1]))
im = window(c['plate'], x0, y0, x1, y1)[0]; x0, y0 = max(0, x0), max(0, y0)
t = cv2.resize(im, None, fx=Z, fy=Z, interpolation=cv2.INTER_CUBIC)
P = lambda x, y: (int(round((x - x0) * Z)), int(round((y - y0) * Z)))
for r in S: cv2.rectangle(t, P(r[0], r[1]), P(r[2], r[3]), (0, 170, 0), 1)
for w in W: cv2.polylines(t, [np.array([P(*q) for q in w['poly']], np.int32)], True, (255, 0, 170) if w['target'] else (170, 0, 170), 1)
for i, (a, b, cc, d) in enumerate(cl):
    cv2.rectangle(t, P(a - 1, b - 1), P(cc + 1, d + 1), (255, 90, 0), 1)
    cv2.putText(t, str(i), (P(a, b)[0], P(a, b)[1] - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 0), 1)
cv2.putText(t, f'{cid} p{c["plate"]} [{x0},{y0}] x{Z:g}', (2, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 0, 200), 1)
cv2.imwrite(out, t, [cv2.IMWRITE_JPEG_QUALITY, 90])
for i, q in enumerate(cl): print(i, q)
