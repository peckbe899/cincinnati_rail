"""Q4 (ben-labels, 25 Nov 2026): the proposed line-net label (deleted lines as weighted hard negatives, text resisted,
inkless lines unscored), built in memory, and how much of TODAY's false response it would put under a negative weight.
No training: a static estimate. Nothing is written but this folder's estimate.json.
    cd data/sanborn; python -B bench_2026-11-25/diag/ben-labels/scripts/estimate.py

PROPOSED TARGET (full size; 1 line, 0 not, 255 not scored) and weights, on a plate with Ben's checked lines:
  P1 positives: his printed and drawn lines with ink support >= 0.3 (share of points with ink within 2 px), LINE 3 px,
     weight POS 3. Inkless lines (support < 0.3) and sheet_edge lines: not scored with the GAP margin (as 'sheet_edge').
  P2 GAP margin beside a positive: not scored, as today, EXCEPT text (P4).
  P3 other taught ground: as today (negative, 1; NEG_INK 4 on ink).
  P4 text: T = ink_bins bin 8, dilated 1 px, on the paper, more than PROTECT (2) px from a positive pixel. Negative
     everywhere on the paper (margin and untaught ground too). Weight W_TEXT_NEAR (10) within 40 px of a positive,
     W_TEXT_FAR (6) beyond.
  P5 deleted lines: his 'wrong' network lines that are not duplicates of a final line (under 60% of their points within
     6 px of a final line), and moved lines' old place (more than 8 px from the new): their WRONG_PX (11) px strip, only
     where it is more than 8 px from every final line, is negative everywhere on the paper; weight W_DEL (16) on ink, 4
     off ink. Duplicates (on a final line) are left as they are (positive).
FALSE response = line map P > 0.5 on the paper more than 6 px from every final line (as false_response.py).
Reported per map: shares of the false pixels the current and the proposed target make positive / negative / unscored,
their mean weight, the share under a weight of 6 or more ('hard'), the share covered by T and by the deleted strips, and
the false pixels' share of the plate's whole loss weight (a proxy for how much of the gradient points at them).
"""
import sys, os, json
import numpy as np, cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *  # noqa
W_TEXT_NEAR, W_TEXT_FAR, W_DEL, PROTECT, FAR, DUP_PX = 10.0, 6.0, 16.0, 2, 6, 6
EV = SP + 'train_v2_runs/eval/'; STEPS = ['baseline', 'V1S1', 'V1S2', 'V2S1', 'V2S2']
def pts(a, b, step=2.0):
    a, b = np.asarray(a, float), np.asarray(b, float); L = np.hypot(*(b - a)); n = max(2, int(L / step) + 1)
    return a + np.linspace(0, 1, n)[:, None] * (b - a)
def weights(t, ink):
    w = np.zeros(t.shape, np.float32); w[t == 0] = 1.0; w[(t == 0) & ink] = NEG_INK; w[t == 1] = POS; return w
def build(N, smf, tf, bf):
    full = scan(N); H, W = full.shape[:2]; ink = ink_edgenet(full); af = alpha_full(N, W, H)
    inner = cv2.erode(af.astype(np.uint8), np.ones((9, 9), np.uint8)) > 0; inkin = ink & inner; del full
    dink = cv2.distanceTransform((~inkin).astype(np.uint8), cv2.DIST_L2, 5)
    sm = json.load(open(smf, encoding='utf8')); L = sm['lines']
    fin = raster([(l['a'], l['b']) for l in L], (H, W), 1.0, 1); dfin = cv2.distanceTransform((fin == 0).astype(np.uint8), cv2.DIST_L2, 5); del fin
    sup = []
    for l in L:
        q = pts(l['a'], l['b']); x = np.clip(q[:, 0].round().astype(int), 0, W - 1); y = np.clip(q[:, 1].round().astype(int), 0, H - 1); sup.append(float((dink[y, x] <= 2).mean()))
    del dink
    t = cv2.imread(tf, 0); t2 = t.copy(); w = weights(t, ink)
    pos = [(l['a'], l['b']) for l, s in zip(L, sup) if l['kind'] in ('printed', 'drawn') and s >= 0.3]
    nop = [(l['a'], l['b']) for l, s in zip(L, sup) if l['kind'] in ('printed', 'drawn') and s < 0.3]
    posm = raster(pos, (H, W), 1.0, LINE) > 0
    if nop:   # P1: inkless lines not scored, with the margin, never over an inked positive
        nb = cv2.dilate(raster(nop, (H, W), 1.0, LINE), np.ones((2 * (LINE + GAP) + 1,) * 2, np.uint8)) > 0; t2[nb & ~posm & (t2 == 1)] = 255
        near_pos = cv2.dilate(posm.astype(np.uint8), np.ones((2 * (LINE + GAP) + 1,) * 2, np.uint8)) > 0; t2[nb & ~near_pos] = 255
    dpos = cv2.distanceTransform((t2 != 1).astype(np.uint8), cv2.DIST_L2, 5)
    bins = cv2.imread(bf, 0); T = (cv2.dilate((bins == 8).astype(np.uint8), np.ones((3, 3), np.uint8)) > 0) & af & (dpos > PROTECT); del bins
    # P5 deleted lines and moved lines' old place
    B = ben(N)['lines']; D = []
    for s in B:
        if s.get('verdict') == 'wrong' and s.get('src') != 'sheet': cand = (s['a0'], s['b0'])
        elif s.get('moved') and not s.get('added') and s.get('verdict') != 'wrong' and mid_dist(s['a0'], s['b0'], s['a'], s['b']) > 8: cand = (s['a0'], s['b0'])
        else: continue
        q = pts(*cand); x = np.clip(q[:, 0].round().astype(int), 0, W - 1); y = np.clip(q[:, 1].round().astype(int), 0, H - 1)
        if (dfin[y, x] <= DUP_PX).mean() < 0.6: D.append(cand)
    Dm = (raster(D, (H, W), 1.0, WRONG_PX) > 0) & (dfin > 8) & af
    t2[T] = 0; t2[Dm] = 0
    w2 = weights(t2, ink); w2[T] = np.where(dpos[T] <= 40, W_TEXT_NEAR, W_TEXT_FAR); w2[Dm] = np.where(ink[Dm], W_DEL, 4.0)
    tot = lambda ww: float(ww.sum())
    info = dict(pos_lines=len(pos), inkless_lines_unscored=len(nop), deleted_strips=len(D), text_px=int(T.sum()), deleted_px=int(Dm.sum()),
                weight_pos_now=round(tot(w[t == 1])), weight_neg_now=round(tot(w[t == 0])), weight_pos_new=round(tot(w2[t2 == 1])), weight_neg_new=round(tot(w2[t2 == 0])),
                neg_to_pos_now=round(tot(w[t == 0]) / max(1, tot(w[t == 1])), 2), neg_to_pos_new=round(tot(w2[t2 == 0]) / max(1, tot(w2[t2 == 1])), 2),
                text_weight_share_of_neg_now=round(tot(w[T & (t == 0)]) / max(1, tot(w[t == 0])), 4), text_weight_share_of_neg_new=round(tot(w2[T]) / max(1, tot(w2[t2 == 0])), 4),
                deleted_weight_share_of_neg_now=round(tot(w[Dm & (t == 0)]) / max(1, tot(w[t == 0])), 4), deleted_weight_share_of_neg_new=round(tot(w2[Dm]) / max(1, tot(w2[t2 == 0])), 4),
                pos_px_now=int((t == 1).sum()), pos_px_new=int((t2 == 1).sum()))
    return dict(H=H, W=W, af=af, dfin=dfin, t=t, w=w, t2=t2, w2=w2, T=T, D=Dm, info=info)
def assess(P, p, region=None, extra=None):
    F = (p > 127) & P['af'] & (P['dfin'] > FAR)
    if region is not None: F &= region
    n = int(F.sum()); r = dict(false_px=n)
    for k, t, w in (('now', P['t'], P['w']), ('proposed', P['t2'], P['w2'])):
        v = t[F]; ww = w[F]
        r[k] = dict(pos=round(float((v == 1).mean()), 4), neg=round(float((v == 0).mean()), 4), unscored=round(float((v == 255).mean()), 4), mean_weight=round(float(ww.mean()), 3),
                    hard=round(float((ww >= 6).mean()), 4), loss_mass_share=round(float(ww.sum() / max(1.0, w.sum())), 4))
    r['covered_by_text'] = round(float(P['T'][F].mean()), 4); r['covered_by_deleted'] = round(float(P['D'][F].mean()), 4)
    dd = P['dfin'][F]; tx = P['T'][F]
    r['text_false_by_dist'] = {'6-9 (margin)': round(float((tx & (dd <= 9)).sum() / max(1, tx.sum())), 4), '9-20': round(float((tx & (dd > 9) & (dd <= 20)).sum() / max(1, tx.sum())), 4),
                               '20-40': round(float((tx & (dd > 20) & (dd <= 40)).sum() / max(1, tx.sum())), 4), '>40': round(float((tx & (dd > 40)).sum() / max(1, tx.sum())), 4)}
    if extra is not None:
        te, we = extra; v = te[F]; ww = np.zeros(v.shape, np.float32)
        r['other_label'] = dict(pos=round(float((v == 1).mean()), 4), neg=round(float((v == 0).mean()), 4), unscored=round(float((v == 255).mean()), 4))
    return r
res = {}
P = build('1A', SP + 'train_v2/1A/streetmap.json', SP + 'train_v2/1A/lines.png', DIAG + '/bins_1A_now.png'); res['1A'] = dict(label_now='train_v2/1A/lines.png (map; trained in V1, V2)', info=P['info'])
vm = cv2.imread(SP + 'train_v2/1A/valmask.png', 0) > 0; vf = cv2.resize(vm.astype(np.uint8), (P['W'], P['H']), interpolation=cv2.INTER_NEAREST) > 0
for s in STEPS:
    p = cv2.imread(EV + f'{s}/maps1A/1A_lines.png', 0); res['1A'][s] = dict(whole=assess(P, p), heldout=assess(P, p, vf)); print('1A', s, json.dumps(res['1A'][s]), flush=True)
print('1A info', json.dumps(P['info']), flush=True); del P
P = build('5', DIAG + '/map_now/5_streetmap.json', DIAG + '/map_now/5_lines.png', DIAG + '/bins_5_now.png'); res['5'] = dict(label_now='map recipe on Ben\'s 25 Nov lines (diag map_now; not trained); other_label = train_v2/5 pseudo (V2)', info=P['info'])
tp = cv2.imread(SP + 'train_v2/5/lines.png', 0); p = cv2.imread(SP + 'unet_data/5_lines_lines_ng1.png', 0)
res['5']['baseline'] = assess(P, p, extra=(tp, None)); print('5 baseline', json.dumps(res['5']['baseline']), flush=True); print('5 info', json.dumps(P['info']), flush=True); del P, tp
P = build('44', SP + 'streetmap/22-44.json', DIAG + '/map_now/44_lines.png', SP + 'unet_data/44_bins.png'); res['44'] = dict(label_now='map recipe (hypothetical: 44 is never trained)', info=P['info'])
for s in STEPS:
    p = cv2.imread(EV + f'{s}/maps44/grid0/44_lines.png', 0); res['44'][s] = assess(P, p); print('44', s, json.dumps(res['44'][s]), flush=True)
print('44 info', json.dumps(P['info']), flush=True)
wj(os.path.join(DIAG, 'estimate.json'), res)
