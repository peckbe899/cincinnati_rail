# read-only: plate 44 automatic labels (make_labels: N_label.png, N_verified.json) vs Ben's checked street map (streetmap/22-44.json)
import cv2, numpy as np, json
SP = r'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; U = SP + 'unet_data/'
sm = json.load(open(SP + 'streetmap/22-44.json', encoding='utf8')); full = cv2.imread(SP + 'cufp/22-44.jpg', cv2.IMREAD_REDUCED_GRAYSCALE_2)
h, w = full.shape[:2]; H, W = 2 * h, 2 * w
# lines at full size
ben = np.zeros((H, W), np.uint8); benp = np.zeros((H, W), np.uint8)
for l in sm['lines']:
    a, b = tuple(np.round(l['a']).astype(int)), tuple(np.round(l['b']).astype(int))
    if l['kind'] != 'sheet_edge': cv2.line(ben, a, b, 1, 1)
ver = np.zeros((H, W), np.uint8)
for a, b in json.load(open(U + '44_verified.json', encoding='utf8')): cv2.line(ver, tuple(np.round(a).astype(int)), tuple(np.round(b).astype(int)), 1, 1)
k = np.ones((7, 7), np.uint8)   # 3 px tolerance, as edgenet.TOL
near_v = cv2.dilate(ver, k) > 0; near_b = cv2.dilate(ben, k) > 0
print(f"Ben's street lines (not sheet edge): {int(ben.sum())} px; verified.json lines: {int(ver.sum())} px")
print(f"share of Ben's line length within 3 px of a verified edge (target recall vs GT): {near_v[ben > 0].mean():.3f}")
print(f"share of verified-edge length within 3 px of a Ben line (target precision vs GT): {near_b[ver > 0].mean():.3f}")
# blocks at half size vs the label
blk = np.zeros((h, w), np.uint8)
for b in sm['blocks']: cv2.fillPoly(blk, [np.round(np.array(b['ring']) / 2).astype(np.int32)], 1)
lab = cv2.imread(U + '44_label.png', 0); ok = lab != 255
print(f"label: block share of labelled {float((lab[ok] == 1).mean()):.3f}; Ben's closed blocks cover {float(blk.mean()):.3f} of the plate")
inb = (blk == 1) & ok
print(f"inside Ben's closed blocks, label says block: {float((lab[inb] == 1).mean()):.4f} ({int(inb.sum())} px)")
st = ok & (lab == 0); print(f"label street pixels that fall inside a Ben block: {float((blk[st] == 1).mean()):.4f}")
p = cv2.imread(U + '44_pred_area_ng1.png', 0) > 127
print(f"area_ng1 inside Ben's closed blocks says block: {float(p[blk == 1].mean()):.4f}")
