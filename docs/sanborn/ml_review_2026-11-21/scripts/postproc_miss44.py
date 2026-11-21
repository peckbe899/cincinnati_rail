"""Plate 44: where Ben's printed lines go missing. Each sample point of his printed lines is put in the first class it fits:
exported side within 6 px / short piece within 6 px / short piece within 40 px / watershed block edge within 40 px / P(block)=0.5 edge within 40 px / nothing."""
import json, numpy as np, cv2
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; U = SP + 'unet_data/'
H, W = 7219, 10768
sm = json.load(open(SP + 'streetmap/22-44.json', encoding='utf8'))
o = json.load(open(SP + 'picks22_guided/22-44/outlines.json', encoding='utf8'))
def raster(segs):
    m = np.full((H, W), 255, np.uint8)
    for a, b in segs: cv2.line(m, tuple(np.round(a).astype(int)), tuple(np.round(b).astype(int)), 0, 1)
    return cv2.distanceTransform(m, cv2.DIST_L2, 3)
ex = raster([(s['a'], s['b']) for p in o for s in p if s['state'] != 'short' and not s.get('paper_edge')])
sh = raster([(s['a'], s['b']) for p in o for s in p if s['state'] == 'short'])
bm = cv2.resize(cv2.imread(U + '44_blockmask.png', 0), (W, H), interpolation=cv2.INTER_NEAREST) > 127
e = (bm ^ cv2.erode(bm.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)); bd = cv2.distanceTransform((~e).astype(np.uint8) * 255, cv2.DIST_L2, 3)
pa = cv2.resize(cv2.imread(U + '44_pred_edge_v1.png', 0), (W, H)) > 127
e2 = pa ^ cv2.erode(pa.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool); pd = cv2.distanceTransform((~e2).astype(np.uint8) * 255, cv2.DIST_L2, 3)
cls = np.zeros(6); names = ['exported side <=6px', 'short piece <=6px', 'short piece <=40px', 'watershed block edge <=40px', 'P(block)=0.5 edge <=40px', 'nothing within 40px']
for l in sm['lines']:
    if l['kind'] != 'printed': continue
    a, b = np.array(l['a']), np.array(l['b']); L = np.hypot(*(b - a)); n = max(2, int(L / 4)); P = a + np.outer(np.linspace(0, 1, n), b - a)
    x = np.clip(P[:, 0].round().astype(int), 0, W - 1); y = np.clip(P[:, 1].round().astype(int), 0, H - 1)
    for i in range(n):
        if ex[y[i], x[i]] <= 6: k = 0
        elif sh[y[i], x[i]] <= 6: k = 1
        elif sh[y[i], x[i]] <= 40: k = 2
        elif bd[y[i], x[i]] <= 40: k = 3
        elif pd[y[i], x[i]] <= 40: k = 4
        else: k = 5
        cls[k] += L / n
for k in range(6): print(f'{names[k]:30s} {100 * cls[k] / cls.sum():5.1f}% of Ben\'s printed length')
