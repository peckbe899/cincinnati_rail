# where a pseudo folder's area label disagrees with a map folder's (red: pseudo block on Ben's street; blue: pseudo street on his block),
# and Ben's lines the pseudo line target teaches negative (magenta)
import sys, json, numpy as np, cv2
N, P, Mp, out = sys.argv[1:5]
pl = cv2.imread(f'{P}/{N}/label.png', 0); ml = cv2.imread(f'{Mp}/{N}/label.png', 0); pt = cv2.imread(f'{P}/{N}/lines.png', 0); sm = json.load(open(f'{Mp}/{N}/streetmap.json', encoding='utf8'))
img = cv2.imread(f'{P}/{N}/img.jpg').astype(np.float32) * 0.5 + 100
fb = (pl == 1) & (ml == 0); fs = (pl == 0) & (ml == 1); img[fb] = (0, 0, 255); img[fs] = (255, 0, 0)
W, H = sm['size']; nneg = 0
for l in sm['lines']:
    if l['kind'] not in ('printed', 'drawn'): continue
    a, b = np.array(l['a'], float), np.array(l['b'], float); n = max(2, int(np.hypot(*(b - a))) + 1); q = a + np.outer(np.linspace(0, 1, n), b - a)
    x = np.clip(q[:, 0].round().astype(int), 0, W - 1); y = np.clip(q[:, 1].round().astype(int), 0, H - 1); v = pt[y, x] == 0; nneg += int(v.sum())
    for i in np.where(v)[0]: cv2.circle(img, (int(q[i, 0] / 2), int(q[i, 1] / 2)), 3, (255, 0, 255), -1)
print(N, 'false block px', int(fb.sum()), 'false street px', int(fs.sum()), 'Ben line px taught negative', nneg)
n, cc, st, _ = cv2.connectedComponentsWithStats(fb.astype(np.uint8)); big = np.argsort(-st[1:, 4])[:6] + 1
print('largest false-block pieces (x, y, w, h, px; half size):', [st[k].tolist() for k in big])
cv2.imwrite(out, cv2.resize(img.astype(np.uint8), None, fx=0.25, fy=0.25, interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 88])
