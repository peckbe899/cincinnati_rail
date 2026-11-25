"""Q1c (ben-labels, 25 Nov 2026): (a) plate 5's pseudo line label (train_v2/5, used in V2) against Ben's 25 Nov lines;
(b) on 1A, how much of Ben's deleted FALSE lines each network still draws (the map label taught them negative in V1/V2).
    cd data/sanborn; python -B bench_2026-11-25/diag/ben-labels/scripts/pseudo_vs_ben.py
(a) precision = share of pseudo positive pixels within 6 px of one of his printed/drawn lines; recall = share of his
    printed/drawn line pixels (3 px) with a pseudo positive within 6 px; his line pixels the pseudo label makes negative
    or leaves unscored.
(b) response on deleted false lines = share of the 3 px core of his false deletions (diag lines_1A.json, kind 'false')
    where P(line) > 0.5 within 3 px; whole plate and the held-out region.
"""
import sys, os, json
import numpy as np, cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *  # noqa
res = {}
full = scan('5'); H, W = full.shape[:2]; del full; af = alpha_full('5', W, H)
sm = json.load(open(DIAG + '/map_now/5_streetmap.json', encoding='utf8')); pos = [(l['a'], l['b']) for l in sm['lines'] if l['kind'] in ('printed', 'drawn')]
bm = (raster(pos, (H, W), 1.0, LINE) > 0) & af; db = cv2.distanceTransform((~bm).astype(np.uint8), cv2.DIST_L2, 5)
tp = cv2.imread(SP + 'train_v2/5/lines.png', 0); dp = cv2.distanceTransform((tp != 1).astype(np.uint8), cv2.DIST_L2, 5)
res['5_pseudo'] = dict(pseudo_pos_px=int((tp == 1).sum()), precision_6px=round(float((db[tp == 1] <= 6).mean()), 4), recall_6px=round(float((dp[bm] <= 6).mean()), 4),
                       ben_line_px_taught=dict(pos=round(float((tp[bm] == 1).mean()), 4), neg=round(float((tp[bm] == 0).mean()), 4), unscored=round(float((tp[bm] == 255).mean()), 4)))
print(json.dumps(res['5_pseudo']), flush=True)
del tp, dp, db, bm
full = scan('1A'); H, W = full.shape[:2]; del full; af = alpha_full('1A', W, H)
L = json.load(open(DIAG + '/lines_1A.json'))['dels']; fl = [(d['a'], d['b']) for d in L if d['kind'] == 'false']
core = (raster(fl, (H, W), 1.0, LINE) > 0) & af
vm = cv2.imread(SP + 'train_v2/1A/valmask.png', 0) > 0; vf = cv2.resize(vm.astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST) > 0
res['1A_deleted_false_response'] = dict(core_px=int(core.sum()), core_px_heldout=int((core & vf).sum()))
for s in ['baseline', 'V1S1', 'V1S2', 'V2S1', 'V2S2']:
    p = cv2.imread(SP + f'train_v2_runs/eval/{s}/maps1A/1A_lines.png', 0) > 127; near = cv2.dilate(p.astype(np.uint8), np.ones((7, 7), np.uint8)) > 0
    res['1A_deleted_false_response'][s] = dict(whole=round(float(near[core].mean()), 4), heldout=round(float(near[core & vf].mean()), 4) if (core & vf).any() else None)
print(json.dumps(res['1A_deleted_false_response']), flush=True)
wj(os.path.join(DIAG, 'pseudo_vs_ben.json'), res)
