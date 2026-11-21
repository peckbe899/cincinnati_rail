import json, numpy as np, cv2
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; U = SP + 'unet_data/'
full = cv2.imread(SP + 'cufp/22-44.jpg'); lab = cv2.resize(cv2.imread(U + '44_label.png', 0), (full.shape[1], full.shape[0]), interpolation=cv2.INTER_NEAREST)
SM = json.load(open(SP + 'streetmap/22-44.json', encoding='utf8')); ver = json.load(open(U + '44_verified.json'))
I = lambda p: tuple(np.round(p).astype(int).tolist())
for nm, (x0, y0, x1, y1) in dict(c0=(2000, 5900, 3300, 7219), c2=(2550, 3900, 3300, 4600), c1=(6500, 4850, 7700, 5550)).items():
    c = full[y0:y1, x0:x1].copy(); l = lab[y0:y1, x0:x1]
    ov = c.copy(); ov[l == 1] = (0, 0, 220); ov[l == 0] = (220, 120, 0); ov[l == 255] = (128, 128, 128)
    c = (c * 0.65 + ov * 0.35).astype(np.uint8)
    for s in SM['lines']: cv2.line(c, I(np.array(s['a']) - [x0, y0]), I(np.array(s['b']) - [x0, y0]), (0, 170, 0), 3)
    for a, b in ver: cv2.line(c, I(np.array(a) - [x0, y0]), I(np.array(b) - [x0, y0]), (255, 0, 255), 1)
    cv2.imwrite(f'crop44_{nm}.jpg', cv2.resize(c, None, fx=0.6, fy=0.6, interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 85])
