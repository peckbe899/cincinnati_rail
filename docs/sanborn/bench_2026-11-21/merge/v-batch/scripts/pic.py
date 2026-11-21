"""merge/v-batch: a picture of one plate (or a window of it): left the batch's editor lines, middle B's, right the merged ones.

    python -B pic.py N [X0 Y0 X1 Y1] [--scale 0.25]     -> v-batch/pics/N[_window].jpg

Colours: green = green line, orange = orange line (all three as the editor shows them, edit_server.clean); on the merged
panel also the sides step 4 leaves out: red = 'not on a line', magenta = 'on rail'. Block polygons are shaded.
"""
import json, os, sys
import numpy as np
import cv2
import common as C
BN = C.step4_mod(); ES = C.edit_server()
a = [x for x in sys.argv[1:] if not x.startswith('--')]; n = a[0]; sc = float(sys.argv[sys.argv.index('--scale') + 1]) if '--scale' in sys.argv else 0.25
im = cv2.imread(C.DATA + f'cufp/22-{n}.jpg'); H, W = im.shape[:2]
x0, y0, x1, y1 = (int(v) for v in a[1:5]) if len(a) >= 5 else (0, 0, W, H)
crop = cv2.resize(im[y0:y1, x0:x1], None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA); crop = (crop * 0.55 + 255 * 0.45).astype(np.uint8)


def step4_B(polys):
    return [dict(src='read', name='', a=s['a'], b=s['b'], state='green' if s['state'] == 'on print' else 'orange') for p in polys for s in p if not (s['state'] == 'short' or s.get('paper_edge'))]


def P(p): return tuple(int(round(v)) for v in ((np.array(p) - [x0, y0]) * sc))


def panel(polys, edges, extra=None, title=''):
    c = crop.copy(); ov = c.copy(); rng = np.random.default_rng(1)
    for p in polys:
        if p and not p[0].get('hole') and len(p) >= 3:
            cv2.fillPoly(ov, [np.array([P(s['a']) for s in p], np.int32)], tuple(int(v) for v in rng.integers(150, 250, 3)))
    c = (c * 0.6 + ov * 0.4).astype(np.uint8)
    for s, col in (extra or []): cv2.line(c, P(s['a']), P(s['b']), col, 2, cv2.LINE_AA)
    for e in ES.clean(edges):
        cv2.line(c, P(e['a']), P(e['b']), (0, 140, 0) if e['state'] == 'green' else (0, 140, 255), 2, cv2.LINE_AA)
        for q in (e['a'], e['b']): cv2.circle(c, P(q), 2, (0, 0, 0), -1)
    cv2.putText(c, title, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 2, cv2.LINE_AA); return c


bp = json.load(open(C.G + f'22-{n}/outlines.json', encoding='utf8')); be = json.load(open(C.U + f'{n}_edges.json', encoding='utf8'))
Bp = json.load(open(C.BENCH + f'outline-nesting/runs_plates/final/{n}/outlines.json', encoding='utf8'))
mp = json.load(open(C.ME + f'plates/{n}/outlines.json', encoding='utf8')); me = BN.step4(mp)
ex = [(s, (0, 0, 230) if s['state'] == 'not on a line' else (200, 0, 200)) for p in mp for s in p if s['state'] in ('not on a line', 'on rail') and not s.get('paper_edge')]
out = np.hstack([panel(bp, be, title=f'batch {n}'), np.full((crop.shape[0], 6, 3), 255, np.uint8), panel(Bp, step4_B(Bp), title='B (outline-nesting)'),
                 np.full((crop.shape[0], 6, 3), 255, np.uint8), panel(mp, me, ex, title='merged')])
os.makedirs(C.ME + 'pics', exist_ok=True); f = C.mine(C.ME + f'pics/{n}' + (f'_{x0}_{y0}' if len(a) >= 5 else '') + '.jpg')
cv2.imwrite(f, out, [cv2.IMWRITE_JPEG_QUALITY, 85]); print(f, out.shape)
