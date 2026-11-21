"""labels-3 (where the mis-taught Ben pixels lie), labels-4 (label vs Ben blocks), labels-5 (rail on label 1)."""
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
print('Ben closed block share of paper', round(float(bk[al].mean()), 4), 'n blocks', len(SM['blocks']))
ln = np.zeros((h, w), np.uint8)
for l in SM['lines']: cv2.line(ln, P2(l['a']), P2(l['b']), 1, 3)
core = al & (cv2.dilate(ln, np.ones((7, 7), np.uint8)) == 0)
# corridors: free ground removed by an opening of 91 half px (about 1.4 street widths?)
free = ((bk == 0) & al & (ln == 0)).astype(np.uint8)
for OP in (61, 91, 121):
    wide = cv2.dilate(cv2.morphologyEx(free, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (OP, OP))), np.ones((9, 9), np.uint8)) & free
    corr = (free == 1) & (wide == 0)
    m = corr & core
    print(f'open {OP}: corridor share of paper {float(corr[al].mean()):.4f} wide-unclosed {float(wide[al].mean()):.4f} | label on corridor', {k: round(float((lab[m] == k).mean()), 4) for k in (0, 1, 255)})
    benlab = np.full((h, w), 255, np.uint8); benlab[bk == 1] = 1; benlab[corr] = 0; benlab[~core] = 255
    dec = benlab != 255; tg = dec & (lab != 255)
    agree = float(((lab == 1) == (benlab == 1))[tg].mean())
    ls_, bs_ = lab[tg] == 0, benlab[tg] == 0
    print(f'   label vs Ben where both decide: agree {agree:.4f} street IoU {float((ls_ & bs_).sum() / (ls_ | bs_).sum()):.4f}; Ben-decided share of paper {float(dec[al].mean()):.4f}; label blank there {float((lab[dec] == 255).mean()):.4f}')
# street width estimate from marked streets (make_labels SHEET_D)
mr = json.load(open(U + f'{N}_marked_refined.json', encoding='utf8'))
wd = [float(np.hypot(*(np.array(m_['left'][0]) - np.array(m_['right'][0])))) for m_ in mr]
print('median marked street width full px', round(float(np.median(wd)), 1), '-> half px', round(float(np.median(wd)) / 2, 1))
# rail
for kind in ('railroad', 'streetcar'):
    m = np.zeros((h, w), np.uint8)
    for t in json.load(open(SP + f'picks22_guided/22-{N}/rail_ben.json', encoding='utf8'))['tracks']:
        if t['kind'] == kind: cv2.polylines(m, [np.round(np.array(t['pts']) / 2).astype(np.int32)], False, 1, 1)
    m = (m > 0) & al; c = collections.Counter(lab[m].tolist()); tot = sum(c.values())
    print(kind, 'track px half', tot, {k: round(v / tot, 3) for k, v in sorted(c.items())}, 'inside Ben block', round(float(bk[m].mean()), 3))
# labels-3: where are Ben line pixels that the edgenet target makes negative, relative to label boundaries?
H, W = 2 * h, 2 * w
full = cv2.imread(SP + f'cufp/22-{N}.jpg'); H, W = full.shape[:2]
alF = cv2.resize(np.load(SP + f'cufp/{N}/png_alpha_s4.npy').astype(np.float32), (W, H)) > 0.5
labF = cv2.resize(lab, (W, H), interpolation=cv2.INTER_NEAREST)
ver = json.load(open(U + f'{N}_verified.json', encoding='utf8'))
P = lambda p: (int(round(p[0])), int(round(p[1])))
line = np.zeros((H, W), np.uint8)
for a, b in ver: cv2.line(line, P(a), P(b), 1, 3)
near = cv2.dilate(line, np.ones((15, 15), np.uint8)) > 0
t = np.where(line > 0, 1, 0).astype(np.uint8); t[(labF == 255) & ~near] = 255; t[near & (line == 0)] = 255; t[~alF] = 255
hsv = cv2.cvtColor(full, cv2.COLOR_BGR2HSV); ink = (hsv[:, :, 2] < 120) | ((hsv[:, :, 1] < 90) & (hsv[:, :, 2] < 170)); del hsv
b3 = np.zeros((H, W), np.uint8)
for l in SM['lines']:
    if l['kind'] in ('printed', 'drawn'): cv2.line(b3, P(l['a']), P(l['b']), 1, 3)
b3 = (b3 > 0) & alF
neg = b3 & (t == 0)
# distance from label boundary: boundary = any transition between 0/1/255 classes, at full size
bnd = (cv2.morphologyEx(labF, cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)) > 0).astype(np.uint8)
dBd = cv2.distanceTransform((bnd == 0).astype(np.uint8), cv2.DIST_L2, 5)
print('Ben 3px px', int(b3.sum()), 'taught neg', int(neg.sum()), round(float(neg.sum() / b3.sum()), 4))
for d in (10, 25, 50):
    print(f'  of the negatives, share > {d} full px from any label boundary: {float((dBd[neg] > d).mean()):.4f}')
print('  label class under the negatives', {k: round(float((labF[neg] == k).mean()), 4) for k in (0, 1)})
bins = cv2.imread(U + f'{N}_bins.png', 0)
NAMES = {0: 'no ink', 1: 'block line', 2: 'lot line', 3: 'building outline', 4: 'railroad', 5: 'streetcar', 6: 'water pipe', 7: 'sewer', 8: 'text', 9: 'not sorted'}
if bins is not None and bins.shape == (H, W):
    c = collections.Counter(bins[neg & ink].tolist()); tot = sum(c.values())
    print('  ink bins under weight-4 Ben negatives', {NAMES.get(k, k): round(v / tot, 3) for k, v in sorted(c.items())})
else: print('bins shape', None if bins is None else bins.shape)
