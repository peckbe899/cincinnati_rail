import sys, json, numpy as np
sys.path.insert(0, '.')
from common import load_layers, Tiles
from shapely.geometry import box
from shapely.ops import unary_union
from shapely.strtree import STRtree
from PIL import Image, ImageDraw, ImageFont
blocks, _, _ = load_layers(); T = Tiles()
bb = [b['g'] for b in blocks if b['src'] == 'basin']; tree = STRtree(bb)
U = unary_union(bb); x0, y0, x1, y1 = U.bounds; C, M, RES = 150.0, 20.0, 0.25
fnt = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 12)
man = []; k = 0
for gx in np.arange(np.floor(x0 / C) * C, x1, C):
    for gy in np.arange(np.floor(y0 / C) * C, y1, C):
        cell = box(gx, gy, gx + C, gy + C)
        if sum(bb[i].intersection(cell).area for i in tree.query(cell)) < 300: continue
        X0, Y1 = gx - M, gy + C + M; W = int((C + 2 * M) / RES)
        xs = X0 + (np.arange(W) + 0.5) * RES; ys = Y1 - (np.arange(W) + 0.5) * RES; XX, YY = np.meshgrid(xs, ys)
        lum = T.sample(XX.ravel(), YY.ravel())
        if np.isnan(lum).mean() > 0.85: continue
        # colour crop: sample RGB by reading tiles directly would be nicer; luminance is enough to read the lettering
        im = Image.fromarray(np.nan_to_num(lum.reshape(W, W), nan=255).astype(np.uint8)).convert('RGB'); d = ImageDraw.Draw(im)
        for m in range(0, int(C + 2 * M) + 1, 25):
            p = m / RES; d.line([(p, 0), (p, W)], fill=(255, 150, 150), width=1); d.line([(0, p), (W, p)], fill=(255, 150, 150), width=1)
            d.text((p + 2, 2), str(m), fill=(200, 0, 0), font=fnt); d.text((2, p + 2), str(m), fill=(200, 0, 0), font=fnt)
        a, b2 = M / RES, (C + M) / RES; d.rectangle([a, a, b2, b2], outline=(0, 90, 255), width=2)
        cid = 'c%04d' % k; im.save('crops/%s.png' % cid); man.append(dict(id=cid, X0=X0, Y1=Y1, res=RES, core=[M, C + M])); k += 1
json.dump(man, open('crops/manifest.json', 'w')); print('crops', len(man))
