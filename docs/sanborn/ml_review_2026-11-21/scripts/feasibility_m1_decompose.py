# read-only: decompose the "10 point overstatement" of lines_ng1 precision on plate 44 into region vs target effects
import cv2, numpy as np, json
SP = r'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; U = SP + 'unet_data/'
RT = r'C:/Users/peckb/AppData/Local/Temp/claude/8945a8e3044b4e4c/2a2bcb12-80e8-4366-9a59-3be15cce3445/scratchpad/ml_review/research-training/'
LINE, GAP, TOL = 3, 4, 3
sm = json.load(open(SP + 'streetmap/22-44.json', encoding='utf8'))
full = cv2.imread(SP + 'cufp/22-44.jpg', cv2.IMREAD_GRAYSCALE); H, W = full.shape; del full
lab = cv2.resize(cv2.imread(U + '44_label.png', 0), (W, H), interpolation=cv2.INTER_NEAREST)
line = np.zeros((H, W), np.uint8)
for a, b in json.load(open(U + '44_verified.json', encoding='utf8')):
    cv2.line(line, tuple(np.round(a).astype(int)), tuple(np.round(b).astype(int)), 1, LINE)
alpha = cv2.resize(np.load(SP + 'cufp/44/png_alpha_s4.npy').astype(np.float32), (W, H)) > 0.5
near = cv2.dilate(line, np.ones((2 * (LINE + GAP) + 1,) * 2, np.uint8)) > 0
t = np.where(line > 0, 1, 0).astype(np.uint8); t[(lab == 255) & ~near] = 255; t[near & (line == 0)] = 255; t[~alpha] = 255
k = np.ones((2 * TOL + 1, 2 * TOL + 1), np.uint8)
inner = cv2.erode(alpha.astype(np.uint8), np.ones((121, 121), np.uint8)) > 0
def ben_mask(kinds):
    m = np.zeros((H, W), np.uint8)
    for l in sm['lines']:
        if l['kind'] in kinds: cv2.line(m, tuple(np.round(l['a']).astype(int)), tuple(np.round(l['b']).astype(int)), 1, 1)
    return m > 0
benA = ben_mask(('printed', 'drawn')); benP = ben_mask(('printed',))
nearA = cv2.dilate(benA.astype(np.uint8), k) > 0; nearP = cv2.dilate(benP.astype(np.uint8), k) > 0
vline = t == 1; near_v = cv2.dilate(vline.astype(np.uint8), k) > 0; scored = t != 255
edgenet_region = scored | near_v
res = {}
for name, pr in (('lines_ng1', np.load(RT + 'd_lines_ng1_44.npy') > 127), ('lines_v2', cv2.imread(U + '44_lines_lines_v2.png', 0) > 127)):
    npr = cv2.dilate(pr.astype(np.uint8), k) > 0; r = {}
    for rname, reg in (('edgenet_region', edgenet_region), ('inner', inner), ('edgenet_region&inner', edgenet_region & inner)):
        d = pr & reg
        r[rname] = dict(drawn_px=int(d.sum()), P_vs_verified=round(float(near_v[d].mean()), 4), P_vs_ben_all=round(float(nearA[d].mean()), 4), P_vs_ben_printed=round(float(nearP[d].mean()), 4),
                        R_ben_all=round(float(npr[benA & reg].mean()), 4), R_ben_printed=round(float(npr[benP & reg].mean()), 4), R_verified=round(float(npr[vline & reg].mean()), 4))
    # share of drawn pixels (inside paper interior) that lie on ground edgenet.score ignores
    d = pr & inner; r['share_of_drawn_in_inner_outside_edgenet_region'] = round(float((~edgenet_region[d]).mean()), 4)
    r['P_vs_ben_all_on_ignored_ground'] = round(float(nearA[d & ~edgenet_region].mean()), 4)
    res[name] = r
# target vs Ben
d = vline & inner; res['verified_vs_ben'] = dict(P_all=round(float(nearA[d].mean()), 4), P_printed=round(float(nearP[d].mean()), 4),
     R_all=round(float((cv2.dilate(line, k) > 0)[benA & inner].mean()), 4), R_printed=round(float((cv2.dilate(line, k) > 0)[benP & inner].mean()), 4))
res['ben_drawn_share_of_ben_px_inner'] = round(float((benA & ~benP & inner).sum() / max(1, (benA & inner).sum())), 4)
# area: label block outside Ben's closed blocks (half size)
labh = cv2.imread(U + '44_label.png', 0); h, w = labh.shape; blk = np.zeros((h, w), np.uint8)
for b in sm['blocks']: cv2.fillPoly(blk, [np.round(np.array(b['ring']) / 2).astype(np.int32)], 1)
alh = cv2.resize(np.load(SP + 'cufp/44/png_alpha_s4.npy').astype(np.float32), (w, h)) > 0.5
res['area'] = dict(label_block_px=int((labh == 1).sum()), label_block_outside_ben_blocks=round(float((blk[labh == 1] == 0).mean()), 4),
    paper_share_in_ben_blocks=round(float(blk[alh].mean()), 4), paper_share_label_block=round(float((labh[alh] == 1).mean()), 4), paper_share_label_ignore=round(float((labh[alh] == 255).mean()), 4),
    ben_blocks=len(sm['blocks']), open_ends=len(sm['open_ends']))
print(json.dumps(res, indent=1))
