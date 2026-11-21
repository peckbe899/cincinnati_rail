# read-only checks: tint coverage (hue vs amount), TTA outputs, in-sample vs held-out area accuracy, open blocks on 44
import cv2, numpy as np, json
SP = r'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; U = SP + 'unet_data/'
RT = r'C:/Users/peckb/AppData/Local/Temp/claude/8945a8e3044b4e4c/2a2bcb12-80e8-4366-9a59-3be15cce3445/scratchpad/ml_review/research-training/'
rows = json.load(open(RT + 'b_colour.json')); LAB = {'43', '44', '45', '80', '82A'}
tl = {r['plate']: r['tinted_share'] for r in rows}; labmax = max(tl[p] for p in LAB if p in tl)
print('plates', len(rows), 'labelled tint', {p: tl.get(p) for p in sorted(LAB)}, 'n above max labelled', sum(v > labmax for p, v in tl.items() if p not in LAB), 'n>0.40', sum(v > 0.40 for v in tl.values()))
print('tint min/median/p90/max', min(tl.values()), np.median(list(tl.values())), round(float(np.percentile(list(tl.values()), 90)), 3), max(tl.values()))
# hue distribution among saturated bins (s bins 2..7 of 8 ~ s>64): labelled vs the 19 high-tint plates
def huedist(r):
    h = np.array(r['hist']).reshape(18, 8)[:, 2:].sum(1); return h / max(1e-9, h.sum())
L = np.mean([huedist(r) for r in rows if r['plate'] in LAB], 0); Hh = [r for r in rows if r['tinted_share'] > 0.40]
Hd = np.mean([huedist(r) for r in Hh], 0)
print('hue bin (10 deg each, OpenCV 0-180) share among saturated px, labelled :', np.round(L, 3).tolist())
print('                                                     high-tint (>0.40):', np.round(Hd, 3).tolist())
tv = lambda a, b: round(float(0.5 * np.abs(a - b).sum()), 3)
print('total-variation distance of hue mix, high-tint mean vs labelled mean:', tv(L, Hd), '| between labelled plates:', [tv(huedist(r), L) for r in rows if r['plate'] in LAB],
      '| per high-tint plate:', sorted([tv(huedist(r), L) for r in Hh]))
# TTA
lab = cv2.imread(U + '44_label.png', 0); ok = lab != 255; gt = lab == 1
for nm in ('c_tta_44_id', 'c_tta_44_mean'):
    p = np.load(RT + nm + '.npy').astype(np.float32) / 255; pr = p > 0.5
    iou_s = float(((~pr) & (~gt) & ok).sum() / ((~pr | ~gt) & ok).sum())
    print(nm, 'acc', round(float((pr == gt)[ok].mean()), 4), 'iou_street', round(iou_s, 4))
# Ben closed-block agreement for TTA vs single
sm = json.load(open(SP + 'streetmap/22-44.json', encoding='utf8')); h, w = lab.shape; blk = np.zeros((h, w), np.uint8)
for b in sm['blocks']: cv2.fillPoly(blk, [np.round(np.array(b['ring']) / 2).astype(np.int32)], 1)
for nm in ('c_tta_44_id', 'c_tta_44_mean'):
    p = np.load(RT + nm + '.npy') > 127; print(nm, "share of Ben's closed-block ground called block", round(float(p[blk == 1].mean()), 4))
# open blocks: label-block pixels outside Ben's closed blocks, by connected component touching the paper edge
alh = cv2.resize(np.load(SP + 'cufp/44/png_alpha_s4.npy').astype(np.float32), (w, h)) > 0.5
outb = ((lab == 1) & (blk == 0)).astype(np.uint8); n, cc = cv2.connectedComponents(outb)
edge_band = alh & ~(cv2.erode(alh.astype(np.uint8), np.ones((61, 61), np.uint8)) > 0)   # within 30 px (half size) = 60 px full of the paper edge
touch = np.zeros(n, bool); touch[np.unique(cc[edge_band & (outb > 0)])] = True; touch[0] = False
sizes = np.bincount(cc.ravel(), minlength=n)
print('label-block px outside closed blocks', int(outb.sum()), 'in components touching the paper-edge band', round(float(sizes[touch].sum() / outb.sum()), 3), 'n components', n - 1,
      'n large (>20000 px) not touching edge', int(((sizes > 20000) & ~touch)[1:].sum()))
# in-sample vs held-out area accuracy (a_leak)
for p in ('82A', '80', '43', '45', '44'):
    l = cv2.imread(U + f'{p}_label.png', 0); q = cv2.imread(U + f'{p}_pred_area_ng1.png', 0)
    m = l != 255; g = l[m] == 1; pb = q[m] > 127; conf = (q[m] < 13) | (q[m] > 242)
    print(p, 'area_ng1 acc', round(float((pb == g).mean()), 4), 'confident share', round(float(conf.mean()), 3), 'acc confident', round(float((pb == g)[conf].mean()), 4), 'acc rest', round(float((pb == g)[~conf].mean()), 4))
