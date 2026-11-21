import json, numpy as np, cv2, evallib as E
S = 'C:/Users/peckb/AppData/Local/Temp/claude/8945a8e3044b4e4c/2a2bcb12-80e8-4366-9a59-3be15cce3445/scratchpad/ml_review/evaluation/'
res = {}
iou = lambda a, b: float((a & b).sum() / max(1, (a | b).sum()))
# 1. area_ng1 on its training plates vs on held-out 44 (the line network's 7th input is this map)
for n in ['82A', '80', '43', '45', '44']:
    p = cv2.imread(S + f'snap/{n}_pred_area_ng1_fromimgjpg.png', 0) > 127; lab = cv2.imread(E.U + f'{n}_label.png', 0); m = lab != 255
    pe = cv2.imread(E.U + f'{n}_pred_edge_v1.png', 0) > 127
    res[f'area_ng1_{n}'] = dict(role='val' if n == '44' else 'train', accuracy=round(float((p[m] == (lab[m] == 1)).mean()), 4), iou_street=round(iou(~p & m, (lab == 0) & m), 4),
                                edge_v1_guided_accuracy=round(float((pe[m] == (lab[m] == 1)).mean()), 4))
# 2. area vs Ben on 44, restricted to ground within 50 half-size px of one of Ben's closed blocks (his map leaves open ground unclosed)
T = E.truth('44'); lab = cv2.imread(E.U + '44_label.png', 0); h, w = lab.shape
tb = np.zeros((h, w), np.uint8)
for b in T['blocks']: cv2.fillPoly(tb, [(np.array(b['ring']) / 2).round().astype(np.int32)], 1)
alpha = cv2.resize(np.load(E.SP + 'cufp/44/png_alpha_s4.npy').astype(np.float32), (w, h)) > 0.5
reg = (cv2.dilate(tb, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (101, 101))) > 0) & alpha
res['region_share_of_paper'] = round(float(reg[alpha].mean()), 3)
for nm, f in [('area_ng1', S + 'snap/44_pred_area_ng1_fromimgjpg.png'), ('edge_v1_guided', E.U + '44_pred_edge_v1.png')]:
    p = cv2.imread(f, 0) > 127
    res[f'{nm}_vs_ben_in_region'] = dict(accuracy=round(float((p[reg] == (tb[reg] == 1)).mean()), 4), iou_street=round(iou(~p & reg, (tb == 0) & reg), 4), iou_block=round(iou(p & reg, (tb == 1) & reg), 4))
sc = (lab != 255) & reg
res['label_vs_ben_in_region'] = dict(accuracy_on_scored=round(float(((lab == 1) == (tb == 1))[sc].mean()), 4), scored_share=round(float(sc.sum() / reg.sum()), 4))
# 3. training input (N_img.jpg, JPEG q92 of an INTER_AREA half) vs the batch input (INTER_AREA half of the scan, no second JPEG)
full = cv2.imread(E.SP + 'cufp/22-44.jpg'); H, W = full.shape[:2]; r = cv2.resize(full, (W // 2, H // 2), interpolation=cv2.INTER_AREA); j = cv2.imread(E.U + '44_img.jpg')
res['img_jpg_vs_resize'] = dict(same_shape=r.shape == j.shape, mean_abs_diff=round(float(np.abs(r.astype(int) - j.astype(int)).mean()), 3), p99_abs_diff=int(np.percentile(np.abs(r.astype(int) - j.astype(int)), 99)))
print(json.dumps(res, indent=1)); json.dump(res, open(S + 'out/area_checks.json', 'w'), indent=1)
