"""labels-1: how much do the AREA scores on 44 move when Ben's map is the answer? labels-9: off-map target share."""
import json, collections
import numpy as np, cv2
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; U = SP + 'unet_data/'
N = '44'
lab = cv2.imread(U + f'{N}_label.png', 0); h, w = lab.shape
al = cv2.resize(np.load(SP + f'cufp/{N}/png_alpha_s4.npy').astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR) > 0.5
SM = json.load(open(SP + f'streetmap/22-{N}.json', encoding='utf8'))
P2 = lambda p: (int(round(p[0] / 2)), int(round(p[1] / 2)))
bk = np.zeros((h, w), np.uint8)
for b in SM['blocks']: cv2.fillPoly(bk, [np.round(np.array(b['ring']) / 2).astype(np.int32)], 1)
ln = np.zeros((h, w), np.uint8)
for l in SM['lines']: cv2.line(ln, P2(l['a']), P2(l['b']), 1, 3)
core = al & (cv2.dilate(ln, np.ones((7, 7), np.uint8)) == 0)
free = ((bk == 0) & al & (ln == 0)).astype(np.uint8)
wide = cv2.dilate(cv2.morphologyEx(free, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (91, 91))), np.ones((9, 9), np.uint8)) & free
corr = (free == 1) & (wide == 0)
benlab = np.full((h, w), 255, np.uint8); benlab[bk == 1] = 1; benlab[corr] = 0; benlab[~core] = 255
def ascore(p, L):
    m = L != 255; pr = p[m] > 127; gt = L[m] == 1
    iou = lambda a, b: float((a & b).sum() / max(1, (a | b).sum()))
    return dict(px=int(m.sum()), acc=round(float((pr == gt).mean()), 4), iou_street=round(iou(~pr, ~gt), 4))
both = np.where((lab != 255) & (benlab != 255), benlab, 255).astype(np.uint8)
labboth = np.where(both != 255, lab, 255).astype(np.uint8)
for m in ('edge_v1', 'area_ng1'):
    p = cv2.imread(U + f'{N}_pred_{m}.png', 0)
    print(m, 'vs label', ascore(p, lab), '| vs Ben (blocks+corridors)', ascore(p, benlab), '| on ground both decide: vs label', ascore(p, labboth), 'vs Ben', ascore(p, both))
rb = json.load(open(SP + f'picks22_guided/22-{N}/rail_ben.json', encoding='utf8'))
print('rail_ben tracks', len(rb['tracks']), collections.Counter(t['kind'] for t in rb['tracks']), 'complete', rb.get('complete'))
# labels-9: target (3 px as edgenet draws) far from Ben lines
full_shape = (2 * h + 1, 2 * w)
H, W = 7219, 10768
alF = cv2.resize(np.load(SP + f'cufp/{N}/png_alpha_s4.npy').astype(np.float32), (W, H)) > 0.5
P = lambda p: (int(round(p[0])), int(round(p[1])))
t = np.zeros((H, W), np.uint8)
for a, b in json.load(open(U + f'{N}_verified.json', encoding='utf8')): cv2.line(t, P(a), P(b), 1, 3)
bl = np.zeros((H, W), np.uint8)
for l in SM['lines']: cv2.line(bl, P(l['a']), P(l['b']), 1, 1)
dB = cv2.distanceTransform((bl == 0).astype(np.uint8), cv2.DIST_L2, 5)
tm = (t > 0) & alF
print('target px (3px) on paper', int(tm.sum()), '>6 px from any Ben line', int((tm & (dB > 6)).sum()), round(float((dB[tm] > 6).mean()), 4))
bins = cv2.imread(U + f'{N}_bins.png', 0)
NAMES = {0: 'no ink', 1: 'block line', 2: 'lot line', 3: 'building outline', 4: 'railroad', 5: 'streetcar', 6: 'water pipe', 7: 'sewer', 8: 'text', 9: 'not sorted'}
c = collections.Counter(bins[tm & (dB > 6)].tolist()); tot = sum(c.values())
print('bins under far target px', {NAMES.get(k, k): round(v / tot, 3) for k, v in sorted(c.items())})
