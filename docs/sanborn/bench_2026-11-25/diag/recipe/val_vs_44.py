"""Does the checkpoint-choice score (1A's validation region) track plate 44? For each pair, the trainers' two scores
(area: IoU street on taught pixels; lines: pooled F1 as edgenet.line_counts) computed on the eval's saved maps (whole
plate predicted, so about 0.01 from the trainers' own numbers):
  - on 1A's validation region (train_v2/1A label.png, lines.png, valmask.png), as the trainers score it;
  - on plate 44 against the 21 Nov training-time targets (unet_data/44_label.png; the line target built exactly as
    edgenet.load builds it from 44_verified.json, 44_label.png and the paper), as area_ng1 / lines_ng1 were logged;
then set beside the end-to-end 44 PQ (6-grid mean, eval_v2.json). Reads only; system python; maps of grid0 for 44."""
import json, os, numpy as np, cv2
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
EV = SP + 'train_v2_runs/eval/'; OUT = SP + 'bench_2026-11-25/diag/recipe/'; U = SP + 'unet_data/'
STEPS = ['baseline', 'V1S1', 'V2S1', 'V1S2', 'V2S2']; LINE, GAP, TOL = 3, 4, 3

def area_scores(p, lab, m=None):
    k = lab != 255
    if m is not None: k &= m
    pr = p[k] > 127; gt = lab[k] == 1
    return dict(iou_street=round(float((~pr & ~gt).sum() / max(1, (~pr | ~gt).sum())), 4), accuracy=round(float((pr == gt).mean()), 4), iou_block=round(float((pr & gt).sum() / max(1, (pr | gt).sum())), 4))

def line_counts(p, t, vm=None):   # edgenet.line_counts
    pr = p > 127
    if vm is not None: pr &= vm
    k = np.ones((2 * TOL + 1, 2 * TOL + 1), np.uint8); line = t == 1; scored = t != 255
    near_line = cv2.dilate(line.astype(np.uint8), k) > 0; near_pr = cv2.dilate(pr.astype(np.uint8), k) > 0
    drawn = pr & (scored | near_line)
    c = np.array([drawn.sum(), (drawn & near_line).sum(), line.sum(), (line & near_pr).sum()], np.int64)
    P = c[1] / max(1, c[0]); R = c[3] / max(1, c[2]); return dict(precision=round(float(P), 4), recall=round(float(R), 4), f1=round(float(2 * P * R / max(1e-12, P + R)), 4))

def lines_target_44():   # edgenet.load('44')'s t, without the network inputs
    full = cv2.imread(SP + 'cufp/22-44.jpg', 0); H, W = full.shape[:2]; del full
    lab = cv2.resize(cv2.imread(U + '44_label.png', 0), (W, H), interpolation=cv2.INTER_NEAREST)
    line = np.zeros((H, W), np.uint8)
    for a, b in json.load(open(U + '44_verified.json', encoding='utf8')):
        cv2.line(line, tuple(np.round(a).astype(int)), tuple(np.round(b).astype(int)), 1, LINE)
    alpha = cv2.resize(np.load(SP + 'cufp/44/png_alpha_s4.npy').astype(np.float32), (W, H)) > 0.5
    near = cv2.dilate(line, np.ones((2 * (LINE + GAP) + 1, 2 * (LINE + GAP) + 1), np.uint8)) > 0
    t = np.where(line > 0, 1, 0).astype(np.uint8); t[(lab == 255) & ~near] = 255; t[near & (line == 0)] = 255; t[~alpha] = 255
    return t

lab1 = cv2.imread(SP + 'train_v2/1A/label.png', 0); vm1 = cv2.imread(SP + 'train_v2/1A/valmask.png', 0) > 0
t1 = cv2.imread(SP + 'train_v2/1A/lines.png', 0); H1, W1 = t1.shape
vf = cv2.resize(vm1.astype(np.uint8), (W1, H1), interpolation=cv2.INTER_NEAREST) > 0
ys, xs = np.nonzero(vf.any(1))[0], np.nonzero(vf.any(0))[0]; y0, y1, x0, x1 = ys[0], ys[-1] + 1, xs[0], xs[-1] + 1
tv = t1[y0:y1, x0:x1].copy(); mv = vf[y0:y1, x0:x1]; tv[~mv] = 255
lab44 = cv2.imread(U + '44_label.png', 0); t44 = lines_target_44()
res = {}
for s in STEPS:
    e = json.load(open(EV + f'{s}/eval_v2.json', encoding='utf8'))
    pa1 = cv2.imread(EV + f'{s}/maps1A/1A_area.png', 0); pl1 = cv2.imread(EV + f'{s}/maps1A/1A_lines.png', 0)
    pa44 = cv2.imread(EV + f'{s}/maps44/grid0/44_area.png', 0); pl44 = cv2.imread(EV + f'{s}/maps44/grid0/44_lines.png', 0)
    r = dict(val1A_area=area_scores(pa1, lab1, vm1), val1A_lines=line_counts(pl1[y0:y1, x0:x1], tv, mv),
             t44_area=area_scores(pa44, lab44), t44_lines=line_counts(pl44, t44),
             PQ44_6grid=e['bench44']['v2']['all']['PQ']['mean'] if 'v2' in e['bench44'] else None,
             PQ1A_region=e['bench1A']['v2']['region']['PQ'] if 'v2' in e.get('bench1A', {}) else None)
    if s != 'baseline':
        for k in ('area', 'lines'):
            r[f'trainer_best_{k}'] = e['models'][k]['best']
    res[s] = r; print(s, json.dumps(r), flush=True)
# the baseline's 44 PQ (its eval_v2 holds it under 'baseline' or 'v2')
from scipy.stats import spearmanr
new = [s for s in STEPS if s != 'baseline']
def col(f, S): return [f(res[s]) for s in S]
pq = col(lambda r: r['PQ44_6grid'], STEPS)
summ = {}
for nm, f in [('val1A_area_iou_street', lambda r: r['val1A_area']['iou_street']), ('val1A_lines_f1', lambda r: r['val1A_lines']['f1']),
              ('t44_area_iou_street', lambda r: r['t44_area']['iou_street']), ('t44_lines_f1', lambda r: r['t44_lines']['f1']), ('PQ1A_region', lambda r: r['PQ1A_region'])]:
    v = col(f, STEPS)
    summ[nm] = dict(values=dict(zip(STEPS, v)), spearman_vs_PQ44_all5=round(float(spearmanr(v, pq).correlation), 3) if None not in v and None not in pq else None,
                    spearman_vs_PQ44_new4=round(float(spearmanr(col(f, new), col(lambda r: r['PQ44_6grid'], new)).correlation), 3) if None not in v else None)
summ['PQ44_6grid'] = dict(zip(STEPS, pq))
res['summary'] = summ
json.dump(res, open(OUT + 'val_vs_44.json', 'w'), indent=1); print(json.dumps(summ, indent=1))
