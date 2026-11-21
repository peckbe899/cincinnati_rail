"""Independent area checks (half size) for eval-1, eval-6, eval-8, eval-11. Reads repo files, writes nothing there."""
import json
import numpy as np, cv2
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; U = SP + 'unet_data/'
SN = 'C:/Users/peckb/AppData/Local/Temp/claude/8945a8e3044b4e4c/2a2bcb12-80e8-4366-9a59-3be15cce3445/scratchpad/ml_review/evaluation/snap/'
res = {}
iou = lambda a, b: float((a & b).sum() / max(1, (a | b).sum()))
def unet_score(p, lab):
    m = lab != 255; pr = p[m]; gt = lab[m] == 1
    return dict(pixels=int(m.sum()), accuracy=round(float((pr == gt).mean()), 4), iou_street=round(iou(~pr, ~gt), 4))
lab = cv2.imread(U + '44_label.png', 0); h, w = lab.shape
P = {'edge_v1': cv2.imread(U + '44_pred_edge_v1.png', 0) > 127,     # threshold as unet.score: p > 0.5 on 0-255 -> >127.5
     'ng1_imgjpg': cv2.imread(SN + '44_pred_area_ng1_fromimgjpg.png', 0) > 127,
     'ng1_batch': cv2.imread(U + '44_pred_area_ng1.png', 0) > 127}
for k, p in P.items(): res[f'{k}_vs_label'] = unet_score(p, lab)
# Ben's blocks at half size
T = json.load(open(SP + 'streetmap/22-44.json', encoding='utf8'))
tb = np.zeros((h, w), np.uint8)
for b in T['blocks']: cv2.fillPoly(tb, [(np.array(b['ring']) / 2).round().astype(np.int32)], 1)
alpha = cv2.resize(np.load(SP + 'cufp/44/png_alpha_s4.npy').astype(np.float32), (w, h)) > 0.5
for R in (25, 50, 100):
    reg = (cv2.dilate(tb, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * R + 1, 2 * R + 1))) > 0) & alpha
    d = dict(region_share_of_paper=round(float(reg[alpha].mean()), 3))
    for k, p in P.items():
        d[k + '_vs_ben'] = dict(acc=round(float((p[reg] == (tb[reg] == 1)).mean()), 4), iou_street=round(iou(~p & reg, (tb == 0) & reg), 4))
        sc = reg & (lab != 255)
        d[k + '_vs_label_in_region'] = round(float((p[sc] == (lab[sc] == 1)).mean()), 4)
    sc = reg & (lab != 255)
    d['label_vs_ben_on_scored'] = round(float(((lab[sc] == 1) == (tb[sc] == 1)).mean()), 4)
    res[f'region_R{R}'] = d
# Ben's lines at half size on the label's ignore value
bl = np.zeros((h, w), np.uint8); bi = np.zeros((h, w), np.uint8)
for l in T['lines']:
    a = tuple((np.array(l['a']) / 2).round().astype(int)); b = tuple((np.array(l['b']) / 2).round().astype(int))
    cv2.line(bl, a, b, 1, 1)
    if l['kind'] != 'sheet_edge': cv2.line(bi, a, b, 1, 1)
res['ben_line_px_on_label255_all'] = round(float((lab[bl == 1] == 255).mean()), 4)
res['ben_line_px_on_label255_interior'] = round(float((lab[bi == 1] == 255).mean()), 4)
# how much of the 255 at Ben's lines is the 1 px edge band vs larger blank areas: distance from each Ben line px to a scored px
dsc = cv2.distanceTransform((lab == 255).astype(np.uint8), cv2.DIST_L2, 5)  # distance from an ignored px to the nearest scored px
v = dsc[(bi == 1) & (lab == 255)]
res['ignored_ben_interior_px_within_2px_of_scored'] = round(float((v <= 2).mean()), 4)
res['label_block_where_ben_no_block_px_halfsize'] = int(((lab == 1) & (tb == 0) & alpha).sum())
res['label_scored_share_of_paper'] = round(float((lab != 255)[alpha].mean()), 4)
# flips between the two ng1 inputs
res['ng1_flip_share_of_paper'] = round(float((P['ng1_imgjpg'] != P['ng1_batch'])[alpha].mean()), 4)
# area_ng1 on its training plates (from the 00:58 predictions, saved before the batch overwrote some)
for n in ['82A', '80', '43', '45', '44']:
    p = cv2.imread(SN + f'{n}_pred_area_ng1_fromimgjpg.png', 0) > 127; l = cv2.imread(U + f'{n}_label.png', 0)
    res[f'area_ng1_on_{n}'] = unet_score(p, l)
print(json.dumps(res, indent=1))
json.dump(res, open('v_area.json', 'w'), indent=1)
