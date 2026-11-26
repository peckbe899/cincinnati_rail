"""Skeptic (26 Nov 2026): finder2 on H3 before (out/full_c, 23:22) and after (out/final, 00:01) the window in which it
zoomed FYFFE on plate 47 (pics/dev/zbig_47_fyffe.png, 23:49). Street/block words, and F1 inside / outside its two tuned
windows on 47. Reads only; prints.   cd data/sanborn; python -B .../sk_h3_leak.py"""
import json, sys
sys.dont_write_bytecode = True
import numpy as np, cv2
from matplotlib.path import Path as MP
B = 'bench_2026-11-25/text_v1'
W = json.load(open(f'{B}/truth-check/heldout_fixed/H3_words.json', encoding='utf8'))
t = cv2.imread(f'{B}/truth-check/heldout_fixed/H3_mask.png', 0); x0, y0, x1, y1 = 7040, 4560, 8540, 5560
H, Wd = t.shape; gx, gy = np.meshgrid(np.arange(Wd), np.arange(H))
tw = [[8360, 5400, 9160, 6100], [7040, 5000, 7220, 5100]]; inw = np.zeros(t.shape, bool)
for X0, Y0, X1, Y1 in tw: inw[max(0, Y0 - y0):min(H, Y1 - y0), max(0, X0 - x0):min(Wd, X1 - x0)] = True
print('tuned-window area inside H3 px', int(inw.sum()), 'truth text px there', int((inw & (t == 2)).sum()), 'of', int((t == 2).sum()))
def f1(p, mask):
    tp = (p & (t == 2) & mask).sum(); fp = (p & (t == 1) & mask).sum(); fn = (~p & (t == 2) & mask).sum(); P_ = tp / max(1, tp + fp); R_ = tp / max(1, tp + fn)
    return round(2 * P_ * R_ / max(1e-9, P_ + R_), 4), int(tp), int(fp), int(fn)
for v in ['full_c', 'final']:
    c = cv2.imread(f'{B}/finder2/out/{v}/47_text.png', cv2.IMREAD_UNCHANGED)[y0:y1, x0:x1]; p = np.isin(c, (2, 3)); out = []
    for w in W['words']:
        if w['kind'] not in ('street', 'block'): continue
        P = np.array(w['poly'], float) - [x0, y0]
        m = MP(P).contains_points(np.c_[gx.ravel(), gy.ravel()], radius=0.5).reshape(H, Wd)
        n = (m & (t == 2)).sum(); out.append((w['reading'], round((m & (t == 2) & p).sum() / max(1, n), 3)))
    print(v, out, '| F1 in tuned windows', f1(p, inw), '| outside', f1(p, ~inw), '| all', f1(p, np.ones_like(inw)))
a = cv2.imread(f'{B}/finder2/out/full_c/47_text.png', cv2.IMREAD_UNCHANGED)[y0:y1, x0:x1]; b = cv2.imread(f'{B}/finder2/out/final/47_text.png', cv2.IMREAD_UNCHANGED)[y0:y1, x0:x1]
d = a != b; print('px differing full_c vs final inside H3', int(d.sum()), '| of them inside the tuned windows', int((d & inw).sum()))
