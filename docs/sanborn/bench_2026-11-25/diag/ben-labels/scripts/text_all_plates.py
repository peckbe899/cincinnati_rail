"""Q2c (ben-labels, 25 Nov 2026): how text (ink_bins bin 8) is taught on EVERY train_v2 plate, as the line net was trained.
    cd data/sanborn; python -B bench_2026-11-25/diag/ben-labels/scripts/text_all_plates.py
Per plate (train_v2/N/lines.png; bins unet_data/N_bins.png, for 1A, 5 and 43 the re-runs in this folder):
  text40: text pixels within 40 px of a positive: share negative / unscored, mean loss weight (edgenet.build's);
  text_all: every text pixel on the paper: share negative / unscored / positive;
  pos_on_text: share of the positive pixels with text ink within 1 px (a positive drawn through numbers);
  neg_weight_on_text: share of the plate's negative loss weight that sits on text.
Aggregates: weighted by the crops each plate got in V1 (lines_v2a_s1.json) and V2 (lines_v2b_s1.json).
"""
import sys, os, json
import numpy as np, cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *  # noqa
PL = ['43', '45', '80', '82A', '1A', '5', '54A', '53', '7', '51', '58', '66', '68', '76', '79', '89']
BF = {'1A': DIAG + '/bins_1A_now.png', '5': DIAG + '/bins_5_now.png', '43': DIAG + '/bins_43_now.png'}
res = {}
for N in PL:
    full = scan(N); H, W = full.shape[:2]; ink = ink_edgenet(full); del full; af = alpha_full(N, W, H)
    t = cv2.imread(SP + f'train_v2/{N}/lines.png', 0); bins = cv2.imread(BF.get(N, SP + f'unet_data/{N}_bins.png'), 0)
    if bins is None or bins.shape != t.shape: print(N, 'bins missing or wrong size'); continue
    text = (bins == 8) & af; d = cv2.distanceTransform((t != 1).astype(np.uint8), cv2.DIST_L2, 5)
    w = np.zeros((H, W), np.float32); w[t == 0] = 1.0; w[(t == 0) & ink] = NEG_INK; w[t == 1] = POS
    m40 = text & (d > 2) & (d <= 40); tdil = cv2.dilate((bins == 8).astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
    meta = json.load(open(SP + f'train_v2/{N}/meta.json', encoding='utf8'))
    r = dict(source=meta['source'], text_px=int(text.sum()), text_share_of_ink=round(float(text.sum() / max(1, ((bins > 0) & af).sum())), 3),
             text40=dict(neg=round(float((t[m40] == 0).mean()), 4), unscored=round(float((t[m40] == 255).mean()), 4), mean_weight=round(float(w[m40].mean()), 3), px=int(m40.sum())),
             text_all=dict(neg=round(float((t[text] == 0).mean()), 4), unscored=round(float((t[text] == 255).mean()), 4), pos=round(float((t[text] == 1).mean()), 4)),
             pos_on_text=round(float((tdil & (t == 1)).sum() / max(1, (t == 1).sum())), 4),
             neg_weight_on_text=round(float(w[text & (t == 0)].sum() / max(1, w[t == 0].sum())), 4),
             paper_scored=round(float(((t != 255) & af).sum() / max(1, af.sum())), 4))
    res[N] = r; print(N, json.dumps(r), flush=True)
for v, mf in (('V1', 'lines_v2a_s1.json'), ('V2', 'lines_v2b_s1.json')):
    cd = json.load(open(SP + 'train_v2_runs/models/' + mf, encoding='utf8'))['crops_drawn']; tot = sum(cd.values())
    agg = {k: round(sum(res[p][k[0]][k[1]] * n for p, n in cd.items() if p in res) / tot, 4) for k in [('text40', 'neg'), ('text40', 'unscored'), ('text40', 'mean_weight'), ('text_all', 'unscored')]}
    agg = {f'{a}.{b}': v_ for (a, b), v_ in agg.items()} | {'pos_on_text': round(sum(res[p]['pos_on_text'] * n for p, n in cd.items() if p in res) / tot, 4), 'crops': cd}
    res['_' + v] = agg; print(v, json.dumps(agg), flush=True)
cd = {'43': 1, '45': 1, '80': 1, '82A': 1}
res['_baseline_plates'] = {'text40.unscored': round(sum(res[p]['text40']['unscored'] for p in cd) / 4, 4), 'text40.mean_weight': round(sum(res[p]['text40']['mean_weight'] for p in cd) / 4, 3), 'pos_on_text': round(sum(res[p]['pos_on_text'] for p in cd) / 4, 4), 'note': 'equal weight over 43, 45, 80, 82A (train_noguide.py samples plates equally)'}
print('baseline plates', json.dumps(res['_baseline_plates']))
wj(os.path.join(DIAG, 'text_all_plates.json'), res)
