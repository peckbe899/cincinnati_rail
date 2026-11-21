import json, numpy as np, cv2
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; U = SP + 'unet_data/'
full = cv2.imread(SP + 'cufp/22-44.jpg'); lab = cv2.resize(cv2.imread(U + '44_label.png', 0), (full.shape[1], full.shape[0]), interpolation=cv2.INTER_NEAREST)
SM = json.load(open(SP + 'streetmap/22-44.json', encoding='utf8'))
I = lambda p: tuple(np.round(p).astype(int).tolist())
tiles = []
for (x0, y0, x1, y1) in [(5300, 380, 6450, 640), (1950, 600, 2300, 1100), (2400, 2080, 2700, 2600), (8350, 1750, 8650, 2500)]:
    c = full[y0:y1, x0:x1].copy(); l = lab[y0:y1, x0:x1]
    ov = c.copy(); ov[l == 1] = (0, 0, 220); ov[l == 0] = (220, 120, 0); ov[l == 255] = (128, 128, 128)
    c = (c * 0.65 + ov * 0.35).astype(np.uint8)
    for s in SM['lines']: cv2.line(c, I(np.array(s['a']) - [x0, y0]), I(np.array(s['b']) - [x0, y0]), (0, 170, 0), 3)
    tiles.append(c)
cv2.imwrite('crop44_alley.jpg', cv2.resize(tiles[0], None, fx=0.6, fy=0.6), [cv2.IMWRITE_JPEG_QUALITY, 85])
h = max(t.shape[0] for t in tiles[1:]); row = np.hstack([cv2.copyMakeBorder(t, 0, h - t.shape[0], 0, 10, cv2.BORDER_CONSTANT, value=(255, 255, 255)) for t in tiles[1:]])
cv2.imwrite('crop44_three.jpg', cv2.resize(row, None, fx=0.6, fy=0.6), [cv2.IMWRITE_JPEG_QUALITY, 85])
