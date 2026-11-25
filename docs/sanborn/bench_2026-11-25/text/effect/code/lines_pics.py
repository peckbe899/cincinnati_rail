"""lines_pics.py (text/effect, 25 Nov 2026): what a text mask did to plate 44's editor lines, for one chain, mask, mode
and grid. A stored line is 'gone' when under 50% of its samples lie within 3 px of the masked run's lines; a masked-run
line is 'new' likewise. False/true as lines_score.py (under 20% of samples within 8 px of Ben's lines = false).
Writes crops/lines_<CHAIN>__<MASK>__<MODE>_g<G>_overview.jpg (quarter size: gone false lines red, gone true lines blue,
new lines orange, the mask magenta) and full-size crops of up to 6 gone true lines and 4 gone false lines (..._true_<k>.png, ..._false_<k>.png: plain above
overlay; Ben's lines green, the gone line blue, the masked run's lines orange, the mask magenta).
    cd data/sanborn; python -B bench_2026-11-25/text/effect/code/lines_pics.py CHAIN MASK MODE [G]"""
import json, os, sys
import numpy as np, cv2
from scipy.spatial import cKDTree
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; E = SP + 'bench_2026-11-25/text/effect/'
chain, mask, mode = sys.argv[1:4]; G = int(sys.argv[4]) if len(sys.argv) > 4 else 0
STORED = SP + 'bench_2026-11-25/diag/swap/runs_baseline44/base__grid{g}/' if chain == 'base' else SP + f'train_v2_runs/eval/{chain}/runs44/v2__grid{{g}}/'
H, W = 7219, 10768


def lines(rd): return [e for e in json.load(open(rd + '44_shown.json', encoding='utf8')) if e.get('state') != 'sheet']
def samp(e):
    a, b = np.array(e['a'], float), np.array(e['b'], float); n = max(2, int(np.ceil(np.hypot(*(b - a))))); return a + np.linspace(0, 1, n)[:, None] * (b - a)
def tree(Ls): return cKDTree(np.concatenate([samp(e) for e in Ls]))


A = lines(STORED.format(g=G)); B = lines(E + f'bench/{chain}__{mask}__{mode}/runs44/v2__grid{G}/')
TA, TB = tree(A), tree(B)
SM = json.load(open(SP + 'streetmap/22-44.json', encoding='utf8')); TBen = tree(SM['lines'])
isfalse = lambda e: (TBen.query(samp(e))[0] <= 8).mean() < 0.2
gone = [e for e in A if (TB.query(samp(e))[0] <= 3).mean() < 0.5]; new = [e for e in B if (TA.query(samp(e))[0] <= 3).mean() < 0.5]
gf = [e for e in gone if isfalse(e)]; gt = [e for e in gone if not isfalse(e)]; nf = [e for e in new if isfalse(e)]
print(f'{chain} {mask} {mode} grid{G}: stored {len(A)} lines, masked {len(B)}; gone {len(gone)} ({len(gf)} false, {len(gt)} true); new {len(new)} ({len(nf)} false)')
im = cv2.imread(SP + 'cufp/22-44.jpg'); M = cv2.imread(E + f'masks/44_map_{mask}.png', 0) > 0
small = cv2.resize(im, (W // 4, H // 4), interpolation=cv2.INTER_AREA); small = (small * 0.5 + 127).astype(np.uint8)
ms = cv2.resize(M.astype(np.uint8), (W // 4, H // 4), interpolation=cv2.INTER_AREA) > 0; small[ms] = (220, 120, 220)
for l in SM['lines']: cv2.line(small, tuple((np.array(l['a']) / 4).round().astype(int).tolist()), tuple((np.array(l['b']) / 4).round().astype(int).tolist()), (0, 170, 0), 1)
for Ls, col in ((gf, (0, 0, 230)), (gt, (230, 80, 0)), (new, (0, 150, 255))):
    for e in Ls: cv2.line(small, tuple((np.array(e['a']) / 4).round().astype(int).tolist()), tuple((np.array(e['b']) / 4).round().astype(int).tolist()), col, 3)
tag = f'{chain}__{mask}__{mode}_g{G}'
cv2.imwrite(E + f'crops/lines_{tag}_overview.jpg', small, [cv2.IMWRITE_JPEG_QUALITY, 85])
for k, (e, what) in enumerate([(e, 'true') for e in sorted(gt, key=lambda e: -np.hypot(*(np.array(e['b']) - np.array(e['a']))))[:6]] + [(e, 'false') for e in sorted(gf, key=lambda e: -np.hypot(*(np.array(e['b']) - np.array(e['a']))))[:4]]):
    P = samp(e); x0, y0 = (P.min(0) - 90).astype(int); x1, y1 = (P.max(0) + 90).astype(int)
    x0, y0, x1, y1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
    if x1 - x0 > 900: xm = (x0 + x1) // 2; x0, x1 = xm - 450, xm + 450
    if y1 - y0 > 700: ym = (y0 + y1) // 2; y0, y1 = ym - 350, ym + 350
    raw = im[y0:y1, x0:x1].copy(); ov = raw.copy(); mm = M[y0:y1, x0:x1]; ov[mm] = (0.4 * ov[mm] + 0.6 * np.array([255, 0, 255])).astype(np.uint8)
    for l in SM['lines']: cv2.line(ov, tuple((np.array(l['a']) - [x0, y0]).round().astype(int).tolist()), tuple((np.array(l['b']) - [x0, y0]).round().astype(int).tolist()), (0, 170, 0), 1)
    for l in B: cv2.line(ov, tuple((np.array(l['a']) - [x0, y0]).round().astype(int).tolist()), tuple((np.array(l['b']) - [x0, y0]).round().astype(int).tolist()), (0, 150, 255), 2)
    cv2.line(ov, tuple((np.array(e['a']) - [x0, y0]).round().astype(int).tolist()), tuple((np.array(e['b']) - [x0, y0]).round().astype(int).tolist()), (230, 80, 0), 2)
    pic = np.vstack([raw, np.full((5, raw.shape[1], 3), 255, np.uint8), ov]); cv2.imwrite(E + f'crops/lines_{tag}_{what}_{k}.png', pic)
    print('gone', what, 'line', k, [round(v) for v in e['a']], [round(v) for v in e['b']], 'len', round(float(np.hypot(*(np.array(e['b']) - np.array(e['a']))))))
