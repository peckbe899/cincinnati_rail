"""merge/impl/r2: a picture of a plate's outline-step output, to look at (21 Nov 2026).

    python -B view.py N RUN_DIR OUT.jpg [--scale 0.25] [--box X0 Y0 X1 Y1] [--base OTHER_RUN_DIR]

Exported lines (step 4, N_edges.json): green = green, orange = orange. Sides step 4 leaves out: grey = paper_edge,
dark red = 'not on a line', magenta = 'on rail', thin grey = 'short'. Off the map ground (N_mapground.png): darker.
With --base, the other run's exported lines are drawn first in thick light blue, so where they differ shows.
"""
import json, os, sys
import numpy as np
import cv2
import common as C
N, RUN, OUT = sys.argv[1], sys.argv[2].rstrip('/') + '/', sys.argv[3]; C.must_be_mine(OUT)
opt = lambda k, n=1: sys.argv[sys.argv.index(k) + 1:sys.argv.index(k) + 1 + n] if k in sys.argv else None
sc = float(opt('--scale')[0]) if opt('--scale') else 0.25
im = cv2.imread(C.DATA + f'cufp/22-{N}.jpg'); H, W = im.shape[:2]
x0, y0, x1, y1 = [int(v) for v in opt('--box', 4)] if opt('--box') else (0, 0, W, H)
im = (im[y0:y1, x0:x1] * 0.6 + 100).astype(np.uint8)
mg = RUN + f'{N}_mapground.png'
if os.path.exists(mg):
    m = cv2.resize(cv2.imread(mg, 0), (W, H), interpolation=cv2.INTER_NEAREST)[y0:y1, x0:x1] == 0; im[m] = (im[m] * 0.6).astype(np.uint8)
im = cv2.resize(im, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA)
P = lambda p: (int(round((p[0] - x0) * sc)), int(round((p[1] - y0) * sc)))
if opt('--base'):
    for e in json.load(open(opt('--base')[0].rstrip('/') + f'/{N}_edges.json')): cv2.line(im, P(e['a']), P(e['b']), (255, 200, 120), max(3, int(10 * sc)), cv2.LINE_AA)
for p in json.load(open(RUN + 'outlines.json')):
    for s in p:
        col = (150, 150, 150) if s.get('paper_edge') else {'not on a line': (0, 0, 140), 'on rail': (200, 0, 200), 'short': (120, 120, 120)}.get(s['state'])
        if col: cv2.line(im, P(s['a']), P(s['b']), col, 1, cv2.LINE_AA)
for e in json.load(open(RUN + f'{N}_edges.json')):
    cv2.line(im, P(e['a']), P(e['b']), (0, 160, 0) if e['state'] == 'green' else (0, 140, 255), max(1, int(5 * sc)), cv2.LINE_AA)
cv2.imwrite(OUT, im, [cv2.IMWRITE_JPEG_QUALITY, 88]); print(OUT, im.shape)
