# Ben's printed/drawn lines coloured by the pseudo line target under them: green taught positive, red wrongly negative, orange left 255
import sys, json, cv2, numpy as np
N, pdir, mdir, out = sys.argv[1:5]; sc = 0.25
pt = cv2.imread(f'{pdir}/{N}/lines.png', 0); sm = json.load(open(f'{mdir}/{N}/streetmap.json', encoding='utf8')); W, H = sm['size']
img = cv2.imread(f'{pdir}/{N}/img.jpg'); lab = cv2.imread(f'{pdir}/{N}/label.png', 0)
im = cv2.resize(img, None, fx=sc * 2, fy=sc * 2, interpolation=cv2.INTER_AREA).astype(np.float32); lb = cv2.resize(lab, (im.shape[1], im.shape[0]), interpolation=cv2.INTER_NEAREST)
im[lb == 1] = im[lb == 1] * 0.6 + np.array([0, 160, 0]) * 0.4; im[lb == 0] = im[lb == 0] * 0.6 + np.array([200, 80, 0]) * 0.4; im[lb == 255] = im[lb == 255] * 0.6 + 50
im = im.clip(0, 255).astype(np.uint8)
gp = cv2.resize((pt == 1).astype(np.float32), (im.shape[1], im.shape[0]), interpolation=cv2.INTER_AREA) > 0.05; im[gp] = (255, 0, 255)
for l in sm['lines']:
    if l['kind'] not in ('printed', 'drawn'): continue
    a, b = np.array(l['a'], float), np.array(l['b'], float); n = max(2, int(np.hypot(*(b - a))) + 1); q = a + np.outer(np.linspace(0, 1, n), b - a)
    x = np.clip(q[:, 0].round().astype(int), 0, W - 1); y = np.clip(q[:, 1].round().astype(int), 0, H - 1); v = pt[y, x]
    for i in range(0, n - 4, 4):
        c = (0, 200, 0) if v[i] == 1 else ((0, 0, 255) if v[i] == 0 else (0, 165, 255))
        cv2.line(im, tuple((q[i] * sc).astype(int)), tuple((q[min(i + 4, n - 1)] * sc).astype(int)), c, 2)
cv2.imwrite(out, im, [cv2.IMWRITE_JPEG_QUALITY, 88])
