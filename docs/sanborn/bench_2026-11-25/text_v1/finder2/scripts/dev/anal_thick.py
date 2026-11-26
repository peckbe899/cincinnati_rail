"""dev (finder2): how much of each truth v2 class / word kind survives an opening of the ink with an ellipse of d px
(the thick core). T1-T7 only. cd data/sanborn; python -B <this>"""
import json, os, sys
sys.dont_write_bytecode = True
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); TRUTH = os.path.normpath(os.path.join(HERE, '..', '..', '..', 'truth'))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, '..', '..', '..', 'code')))
from score_text import poly_fill
crops = json.load(open(os.path.join(TRUTH, 'crops.json')))
E = lambda k: cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
res = {}
for tid in ('T1', 'T2', 'T3', 'T4', 'T6', 'T7'):
    c = crops[tid]; x0, y0, x1, y1 = c['win']; tr = cv2.imread(os.path.join(TRUTH, f'{tid}_mask.png'), 0)
    ink = ((tr == 1) | (tr == 2) | (tr == 3)).astype(np.uint8)
    W = json.load(open(os.path.join(TRUTH, f'{tid}_words.json'), encoding='utf8'))['words']
    for d in (4, 5, 6, 7):
        core = cv2.morphologyEx(ink, cv2.MORPH_OPEN, E(d)) > 0
        for cls in (1, 2):
            a = res.setdefault((d, f'class{cls}'), [0, 0]); m = tr == cls; a[0] += int(m.sum()); a[1] += int((m & core).sum())
        for w in W:
            if not w.get('poly'): continue
            pm = poly_fill(tr.shape, w['poly'], np.array([x0, y0])) & (tr == 2)
            h = w.get('height') or 0; key = (d, w['kind'] + (' h55+' if h >= 55 else (' h35-55' if h >= 35 else ' h<35')))
            a = res.setdefault(key, [0, 0]); a[0] += int(pm.sum()); a[1] += int((pm & core).sum())
for k in sorted(res, key=lambda k: (k[1], k[0])):
    v = res[k]
    if v[0] > 300: print(f'{k[1]:18s} d {k[0]}  px {v[0]:7d}  in core {v[1] / v[0]:.3f}')
