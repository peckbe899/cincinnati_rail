"""How the plate-44 validation numbers change when Ben's map is the answer instead of the automatic target (read-only)."""
import json
import numpy as np, cv2
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; U = SP + 'unet_data/'
N = '44'; LINE, GAP, TOL = 3, 4, 3
full_shape = (7219, 10768); H, W = full_shape
alphaF = cv2.resize(np.load(SP + f'cufp/{N}/png_alpha_s4.npy').astype(np.float32), (W, H)) > 0.5
I = lambda p: tuple(np.round(p).astype(int).tolist())
lab = cv2.resize(cv2.imread(U + f'{N}_label.png', 0), (W, H), interpolation=cv2.INTER_NEAREST)
def target(segs, use_lab=True):
    line = np.zeros((H, W), np.uint8)
    for a, b in segs: cv2.line(line, I(a), I(b), 1, LINE)
    near = cv2.dilate(line, np.ones((2 * (LINE + GAP) + 1,) * 2, np.uint8)) > 0
    t = np.where(line > 0, 1, 0).astype(np.uint8)
    if use_lab: t[(lab == 255) & ~near] = 255
    t[near & (line == 0)] = 255; t[~alphaF] = 255; return t
def score(p, t):   # edgenet.score
    pr = p > 0.5; k = np.ones((2 * TOL + 1,) * 2, np.uint8); line = t == 1; scored = t != 255
    near_line = cv2.dilate(line.astype(np.uint8), k) > 0; near_pr = cv2.dilate(pr.astype(np.uint8), k) > 0
    drawn = pr & (scored | near_line)
    return dict(precision=round(float((drawn & near_line).sum() / max(1, drawn.sum())), 4), recall=round(float((line & near_pr).sum() / max(1, line.sum())), 4))
ver = json.load(open(U + f'{N}_verified.json', encoding='utf8'))
SM = json.load(open(SP + f'streetmap/22-{N}.json', encoding='utf8'))
benL = [(l['a'], l['b']) for l in SM['lines'] if l['kind'] in ('printed', 'drawn')]
tA = target(ver); tB = target(benL, use_lab=False); tB2 = target(benL, use_lab=True)
for m in ['lines_v2', 'lines_v1']:
    p = cv2.imread(U + f'{N}_lines_{m}.png', 0)
    if p is None: continue
    p = p.astype(np.float32) / 255
    print(m, 'vs automatic target (as trained/validated):', score(p, tA), '| vs Ben map, whole paper scored:', score(p, tB), '| vs Ben map, same scored ground:', score(p, tB2))
# area: area_ng1 / edge_v1 prediction on 44 vs label and vs Ben (blocks = 1, his street corridors = 0)
labh = cv2.imread(U + f'{N}_label.png', 0); h, w = labh.shape
alpha = cv2.resize(np.load(SP + f'cufp/{N}/png_alpha_s4.npy').astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR) > 0.5
bk = np.zeros((h, w), np.uint8)
for b in SM['blocks']: cv2.fillPoly(bk, [np.round(np.array(b['ring']) / 2).astype(np.int32)], 1)
ln = np.zeros((h, w), np.uint8)
for l in SM['lines']: cv2.line(ln, I(np.array(l['a']) / 2), I(np.array(l['b']) / 2), 1, 3)
free = ((bk == 0) & alpha & (ln == 0)).astype(np.uint8)
wide = cv2.dilate(cv2.morphologyEx(free, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (91, 91))), np.ones((9, 9), np.uint8)) & free
benlab = np.full((h, w), 255, np.uint8); benlab[(bk == 1)] = 1; benlab[(free == 1) & (wide == 0)] = 0
benlab[cv2.dilate(ln, np.ones((5, 5), np.uint8)) > 0] = 255; benlab[~alpha] = 255
print('Ben-derived area answer: block', int((benlab == 1).sum()), 'corridor', int((benlab == 0).sum()), 'not known', int(((benlab == 255) & alpha).sum()))
def ascore(p, L):
    m = L != 255; pr = p[m] > 0.5; gt = L[m] == 1; iou = lambda a, b: float((a & b).sum() / max(1, (a | b).sum()))
    return dict(px=int(m.sum()), accuracy=round(float((pr == gt).mean()), 4), iou_street=round(iou(~pr, ~gt), 4))
for m in ['area_ng1', 'edge_v1']:
    p = cv2.imread(U + f'{N}_pred_{m}.png', 0)
    if p is None: continue
    p = p.astype(np.float32) / 255
    print(m, 'vs label:', ascore(p, labh), '| vs Ben blocks+corridors:', ascore(p, benlab))
print('label itself vs Ben blocks+corridors:', ascore((labh == 1).astype(np.float32) * (labh != 255) + 0.0, np.where(labh == 255, 255, benlab).astype(np.uint8)))
