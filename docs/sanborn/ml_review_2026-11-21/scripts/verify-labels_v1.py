"""Independent re-check of labels-1, labels-3, labels-6 on plate 44 (read-only on the repo)."""
import json, sys
import numpy as np, cv2
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; U = SP + 'unet_data/'
N = '44'
full = cv2.imread(SP + f'cufp/22-{N}.jpg'); H, W = full.shape[:2]; print('size', W, H)
alpha = cv2.resize(np.load(SP + f'cufp/{N}/png_alpha_s4.npy').astype(np.float32), (W, H)) > 0.5
SM = json.load(open(SP + f'streetmap/22-{N}.json', encoding='utf8'))
ver = json.load(open(U + f'{N}_verified.json', encoding='utf8')); print('verified segs', len(ver))
P = lambda p: (int(round(p[0])), int(round(p[1])))
def rast(segs, w=1):
    m = np.zeros((H, W), np.uint8)
    for a, b in segs: cv2.line(m, P(a), P(b), 1, w)
    return m
benPD = rast([(l['a'], l['b']) for l in SM['lines'] if l['kind'] in ('printed', 'drawn')])
benAll = rast([(l['a'], l['b']) for l in SM['lines']])
benDrawn = rast([(l['a'], l['b']) for l in SM['lines'] if l['kind'] == 'drawn'])
benPr = rast([(l['a'], l['b']) for l in SM['lines'] if l['kind'] == 'printed'])
v1 = rast(ver)
dV = cv2.distanceTransform((v1 == 0).astype(np.uint8), cv2.DIST_L2, 5)
dBall = cv2.distanceTransform((benAll == 0).astype(np.uint8), cv2.DIST_L2, 5)
m = (benPD > 0) & alpha
print('Ben printed+drawn on paper px', int(m.sum()), 'within3 of auto', round(float((dV[m] <= 3).mean()), 4))
for nm, mm in (('printed', benPr), ('drawn', benDrawn)):
    k = (mm > 0) & alpha; print(' ', nm, int(k.sum()), 'within3', round(float((dV[k] <= 3).mean()), 4))
mv = (v1 > 0) & alpha
print('auto target px on paper', int(mv.sum()), 'within3 of any Ben line', round(float((dBall[mv] <= 3).mean()), 4))
# edgenet target
LINE, GAP, TOL = 3, 4, 3
lab = cv2.resize(cv2.imread(U + f'{N}_label.png', 0), (W, H), interpolation=cv2.INTER_NEAREST)
def target(segs, use_lab=True):
    line = rast(segs, LINE)
    near = cv2.dilate(line, np.ones((2 * (LINE + GAP) + 1,) * 2, np.uint8)) > 0
    t = np.where(line > 0, 1, 0).astype(np.uint8)
    if use_lab: t[(lab == 255) & ~near] = 255
    t[near & (line == 0)] = 255; t[~alpha] = 255
    return t
t = target(ver)
print('line_share_of_plate (current target)', round(float((t == 1).mean()), 4))
hsv = cv2.cvtColor(full, cv2.COLOR_BGR2HSV); ink = (hsv[:, :, 2] < 120) | ((hsv[:, :, 1] < 90) & (hsv[:, :, 2] < 170))
# Ben printed+drawn drawn LINE=3 px wide (same as the target's own line)
b3 = (rast([(l['a'], l['b']) for l in SM['lines'] if l['kind'] in ('printed', 'drawn')], LINE) > 0) & alpha
tot = b3.sum()
print('Ben lines at 3px:', int(tot), 'pos', round(float((t[b3] == 1).mean()), 4), 'unscored', round(float((t[b3] == 255).mean()), 4),
      'neg', round(float((t[b3] == 0).mean()), 4), 'neg on ink (w4)', round(float(((t[b3] == 0) & ink[b3]).mean()), 4))
far = b3 & (dV > 8)
print('Ben 3px far>8 from auto share', round(float(far.sum() / tot), 4), 'of those neg', round(float((t[far] == 0).mean()), 4), 'neg ink', round(float(((t[far] == 0) & ink[far]).mean()), 4))
# drawn only
d3 = (rast([(l['a'], l['b']) for l in SM['lines'] if l['kind'] == 'drawn'], LINE) > 0) & alpha
print('drawn 3px', int(d3.sum()), 'pos', round(float((t[d3] == 1).mean()), 4), 'neg', round(float((t[d3] == 0).mean()), 4), 'neg ink', round(float(((t[d3] == 0) & ink[d3]).mean()), 4))
# weight share: of all weight-4 ink negatives in the scored target, how many are Ben line pixels
negink = (t == 0) & ink
print('ink negatives total', int(negink.sum()), 'of which on Ben 3px lines', int((negink & b3).sum()), round(float((negink & b3).sum() / negink.sum()), 4))
# rescoring lines_v2 / lines_ng1? only lines_v2 saved for 44
def score(p, t):
    pr = p > 0.5; k = np.ones((2 * TOL + 1,) * 2, np.uint8); line = t == 1; scored = t != 255
    near_line = cv2.dilate(line.astype(np.uint8), k) > 0; near_pr = cv2.dilate(pr.astype(np.uint8), k) > 0
    drawn = pr & (scored | near_line)
    return dict(precision=round(float((drawn & near_line).sum() / max(1, drawn.sum())), 4), recall=round(float((line & near_pr).sum() / max(1, line.sum())), 4), drawn=int(drawn.sum()))
benL = [(l['a'], l['b']) for l in SM['lines'] if l['kind'] in ('printed', 'drawn')]
tB_whole = target(benL, use_lab=False); tB_lab = target(benL, use_lab=True)
for mname in ('lines_v2', 'lines_v1', 'lines_ng1'):
    p = cv2.imread(U + f'{N}_lines_{mname}.png', 0)
    if p is None: print(mname, 'no saved prediction'); continue
    p = p.astype(np.float32) / 255
    print(mname, 'auto:', score(p, t), '| Ben whole paper:', score(p, tB_whole), '| Ben, label-scored ground:', score(p, tB_lab))
