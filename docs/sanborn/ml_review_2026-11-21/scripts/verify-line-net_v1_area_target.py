"""Read-only verification (system python, CPU): area_ng1 quality on its training plates vs 44 (from scratch snapshots),
44 line target rebuilt as edgenet.load does, lines_v2's saved 44 map re-scored on today's target, Ben's drawn lines vs target."""
import json, os, sys, glob, time
import numpy as np, cv2
R = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; D = R + 'unet_data/'
S = 'C:/Users/peckb/AppData/Local/Temp/claude/8945a8e3044b4e4c/2a2bcb12-80e8-4366-9a59-3be15cce3445/scratchpad/ml_review/verify-line-net/'
out = {}
# ---- 1. area_ng1 quality (snapshots taken before the batch reaches the placed plates)
for n in ('82A', '80', '43', '45', '44'):
    lab = cv2.imread(D + f'{n}_label.png', 0); p = cv2.imread(S + f'snap/{n}_pred_area_ng1.png', 0).astype(np.float32) / 255
    m = lab != 255; pr = p > 0.5; gt = lab == 1; st = (lab == 0)
    a = np.load(R + f'cufp/{n}/png_alpha_s4.npy').astype(np.float32); a = cv2.resize(a, (p.shape[1], p.shape[0])) > 0.5
    uns = (p > 0.1) & (p < 0.9)
    out[f'area/{n}'] = dict(acc=round(float((pr[m] == gt[m]).mean()), 4),
                           iou_street=round(float((~pr & st).sum() / max(1, ((~pr & m) | st).sum())), 4),
                           street_called_block=round(float((pr & st).sum() / st.sum()), 4),
                           block_called_street=round(float((~pr & gt).sum() / gt.sum()), 4),
                           unsure_labelled=round(float(uns[m].mean()), 4), unsure_paper=round(float(uns[a].mean()), 4),
                           street_share_of_labelled=round(float(st.sum() / m.sum()), 4))
    print(n, out[f'area/{n}'], flush=True)
# ---- 2. unplaced plates: unsure over the paper, split by source (cut PNG vs whole PDF sheet)
un = {}
for f in glob.glob(D + '*_pred_area_ng1.png'):
    n = os.path.basename(f).split('_pred_')[0]
    if n in ('82A', '80', '43', '45', '44'): continue
    if time.time() - os.path.getmtime(f) < 120: continue
    p = cv2.imread(f, 0)
    if p is None: continue
    p = p.astype(np.float32) / 255
    a = np.load(R + f'cufp/{n}/png_alpha_s4.npy').astype(np.float32); a = cv2.resize(a, (p.shape[1], p.shape[0])) > 0.5
    src = 'pdf' if os.path.exists(R + f'cufp/{n}/source.json') else 'cut'
    un[n] = dict(unsure_paper=round(float(((p > 0.1) & (p < 0.9))[a].mean()), 4), src=src)
mx = max(out[f'area/{n}']['unsure_paper'] for n in ('82A', '80', '43', '45'))
out['unplaced'] = un
out['unplaced_summary'] = dict(n=len(un), max_train_unsure_paper=mx, n_above_train_max=sum(v['unsure_paper'] > mx for v in un.values()),
                               n_above_0p2=sum(v['unsure_paper'] > 0.2 for v in un.values()), n_above_44=sum(v['unsure_paper'] > out['area/44']['unsure_paper'] for v in un.values()),
                               by_src={s: dict(n=sum(v['src'] == s for v in un.values()), above_train_max=sum(v['src'] == s and v['unsure_paper'] > mx for v in un.values()),
                                               median=float(np.median([v['unsure_paper'] for v in un.values() if v['src'] == s])) if any(v['src'] == s for v in un.values()) else None) for s in ('cut', 'pdf')})
print(out['unplaced_summary'], flush=True)
# ---- 3. 44 target as edgenet.load builds it (LINE 3, GAP 4)
LINE, GAP, TOL = 3, 4, 3
full = cv2.imread(R + 'cufp/22-44.jpg'); H, W = full.shape[:2]
hsv = cv2.cvtColor(full, cv2.COLOR_BGR2HSV); ink = (hsv[:, :, 2] < 120) | ((hsv[:, :, 1] < 90) & (hsv[:, :, 2] < 170)); del hsv, full
lab = cv2.resize(cv2.imread(D + '44_label.png', 0), (W, H), interpolation=cv2.INTER_NEAREST)
line = np.zeros((H, W), np.uint8)
for a_, b_ in json.load(open(D + '44_verified.json', encoding='utf8')):
    cv2.line(line, tuple(np.round(a_).astype(int)), tuple(np.round(b_).astype(int)), 1, LINE)
alpha = cv2.resize(np.load(R + 'cufp/44/png_alpha_s4.npy').astype(np.float32), (W, H)) > 0.5
near = cv2.dilate(line, np.ones((2 * (LINE + GAP) + 1, 2 * (LINE + GAP) + 1), np.uint8)) > 0
t = np.where(line > 0, 1, 0).astype(np.uint8); t[(lab == 255) & ~near] = 255; t[near & (line == 0)] = 255; t[~alpha] = 255
out['44_target'] = dict(line_px=int((t == 1).sum()), line_share=round(float((t == 1).mean()), 4))
def score(p, t):
    pr = p > 0.5; k = np.ones((2 * TOL + 1, 2 * TOL + 1), np.uint8); ln = t == 1; sc = t != 255
    nl = cv2.dilate(ln.astype(np.uint8), k) > 0; npr = cv2.dilate(pr.astype(np.uint8), k) > 0; dr = pr & (sc | nl)
    return dict(precision=round(float((dr & nl).sum() / max(1, dr.sum())), 4), recall=round(float((ln & npr).sum() / max(1, ln.sum())), 4), unscored_share_of_drawing=round(float(1 - dr.sum() / max(1, pr.sum())), 4))
pv = cv2.imread(D + '44_lines_lines_v2.png', 0).astype(np.float32) / 255
out['lines_v2_saved_on_today_target'] = score(pv, t); print('lines_v2 today', out['lines_v2_saved_on_today_target'], flush=True)
# margin geometry: distance from line centre to the far side of the margin
dist = cv2.distanceTransform((line == 0).astype(np.uint8), cv2.DIST_L2, 5)
mg = near & (line == 0)
out['margin'] = dict(max_dist_from_line_px=round(float(dist[mg].max()), 2), median=round(float(np.median(dist[mg])), 2), ink_share=round(float(ink[mg & alpha].mean()), 4))
dv = dist[(pv > 0.5)]
out['lines_v2_drawing_in_4_8px_band'] = round(float(((dv > TOL) & (dv <= 8)).mean()), 4)
# ---- 4. Ben's drawn / printed street sides vs the target
sm = json.load(open(R + 'streetmap/22-44.json', encoding='utf8'))
for kind in ('printed', 'drawn'):
    bm = np.zeros((H, W), np.uint8)
    for l_ in sm['lines']:
        if l_['kind'] == kind: cv2.line(bm, tuple(np.round(l_['a']).astype(int)), tuple(np.round(l_['b']).astype(int)), 1, 3)
    m = (bm > 0) & alpha
    tm = t[m]; neg = tm == 0
    out[f'ben_{kind}'] = dict(px=int(m.sum()), on_ink=round(float(ink[m].mean()), 4), scored_neg=round(float(neg.mean()), 4), scored_pos=round(float((tm == 1).mean()), 4),
                              unscored=round(float((tm == 255).mean()), 4), on_label_block=round(float((lab[m] == 1).mean()), 4),
                              neg_px=int(neg.sum()), neg_ink_px=int((neg & ink[m]).sum()),
                              within_tol_of_target=round(float((cv2.dilate((t == 1).astype(np.uint8), np.ones((7, 7), np.uint8)) > 0)[m].mean()), 4))
    print(kind, out[f'ben_{kind}'], flush=True)
pos_w = 3.0 * out['44_target']['line_px']
negw = out['ben_drawn']['neg_ink_px'] * 4 + (out['ben_drawn']['neg_px'] - out['ben_drawn']['neg_ink_px']) * 1
negw_all = (out['ben_drawn']['neg_ink_px'] + out['ben_printed']['neg_ink_px']) * 4 + (out['ben_drawn']['neg_px'] - out['ben_drawn']['neg_ink_px'] + out['ben_printed']['neg_px'] - out['ben_printed']['neg_ink_px'])
out['wrong_way_weight_vs_pos'] = dict(drawn_only=round(negw / pos_w, 4), drawn_plus_printed=round(negw_all / pos_w, 4))
print(out['wrong_way_weight_vs_pos'])
json.dump(out, open(S + 'v1_area_target.json', 'w'), indent=1)
