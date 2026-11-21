# read-only: plate 44 area label and line networks vs Ben's checked street map
import cv2, numpy as np, json
SP = r'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; U = SP + 'unet_data/'
OUT = r'C:/Users/peckb/AppData/Local/Temp/claude/8945a8e3044b4e4c/2a2bcb12-80e8-4366-9a59-3be15cce3445/scratchpad/ml_review/research-training/'
sm = json.load(open(SP + 'streetmap/22-44.json', encoding='utf8')); lab = cv2.imread(U + '44_label.png', 0); h, w = lab.shape
blk = np.zeros((h, w), np.uint8)
for b in sm['blocks']: cv2.fillPoly(blk, [np.round(np.array(b['ring']) / 2).astype(np.int32)], 1)
ok = lab != 255; inb = (blk == 1) & ok
print(f"inside Ben's closed blocks, label says block: {float((lab[inb] == 1).mean()):.4f} ({int(inb.sum())} px); label street px inside a Ben block: {float((blk[ok & (lab == 0)] == 1).mean()):.4f}")
p = cv2.imread(U + '44_pred_area_ng1.png', 0) > 127; print(f"area_ng1 inside Ben's closed blocks says block: {float(p[blk == 1].mean()):.4f}")
# lines vs Ben, full size, inside the paper less the sheet-edge band
full = cv2.imread(SP + 'cufp/22-44.jpg', cv2.IMREAD_GRAYSCALE); H, W = full.shape
alpha = cv2.resize(np.load(SP + 'cufp/44/png_alpha_s4.npy').astype(np.float32), (W, H)) > 0.5
inner = cv2.erode(alpha.astype(np.uint8), np.ones((121, 121), np.uint8)) > 0
ben = np.zeros((H, W), np.uint8)
for l in sm['lines']:
    if l['kind'] != 'sheet_edge': cv2.line(ben, tuple(np.round(l['a']).astype(int)), tuple(np.round(l['b']).astype(int)), 1, 1)
k = np.ones((7, 7), np.uint8); near_b = cv2.dilate(ben, k) > 0; bl = (ben > 0) & inner
for name, pr in (('lines_ng1 (blank guide)', np.load(OUT + 'd_lines_ng1_44.npy') > 127), ('lines_v2 (guided)', cv2.imread(U + '44_lines_lines_v2.png', 0) > 127)):
    d = pr & inner; near_p = cv2.dilate(pr.astype(np.uint8), k) > 0
    print(f"{name}: precision vs Ben {float(near_b[d].mean()):.3f}, recall of Ben's lines {float(near_p[bl].mean()):.3f}")
ver = np.zeros((H, W), np.uint8)
for a, b in json.load(open(U + '44_verified.json', encoding='utf8')): cv2.line(ver, tuple(np.round(a).astype(int)), tuple(np.round(b).astype(int)), 1, 3)
v = (ver > 0) & inner; near_v = cv2.dilate(ver, k) > 0
print(f"the training target itself (verified.json, 3 px): precision vs Ben {float(near_b[v].mean()):.3f}, recall of Ben's lines {float(near_v[bl].mean()):.3f}")
