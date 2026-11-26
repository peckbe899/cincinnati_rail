"""cz.py H1 X0 Y0 X1 Y1 f out.jpg: the built mask over a region (full-plate px) at scale f, beside the scan.
text red, don't care yellow, other ink grey; word boxes magenta with annotation line numbers; 25 px grid."""
import sys, os, json, cv2, numpy as np
HO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
cid = sys.argv[1]; X0, Y0, X1, Y1 = map(int, sys.argv[2:6]); f = float(sys.argv[6]); out = sys.argv[7]
c = json.load(open(os.path.join(HO, 'crops.json')))[cid]; wx0, wy0, wx1, wy1 = c['win']
im = cv2.imread(f"C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/cufp/22-{c['plate']}.jpg")[Y0:Y1, X0:X1]
M = np.zeros(im.shape[:2], np.uint8) + 9
Mf = cv2.imread(os.path.join(os.path.dirname(HO), 'heldout', f'{cid}_mask.png'), 0)
a0, b0, a1, b1 = max(X0, wx0), max(Y0, wy0), min(X1, wx1), min(Y1, wy1)
M[b0 - Y0:b1 - Y0, a0 - X0:a1 - X0] = Mf[b0 - wy0:b1 - wy0, a0 - wx0:a1 - wx0]
v = (im * 0.35 + 255 * 0.65).astype(np.uint8)
v[M == 1] = (120, 120, 120); v[M == 2] = (0, 0, 230); v[M == 3] = (0, 200, 255)
s1 = cv2.resize(im, None, fx=f, fy=f, interpolation=cv2.INTER_CUBIC)
s2 = cv2.resize(v, None, fx=f, fy=f, interpolation=cv2.INTER_NEAREST)
W = json.load(open(os.path.join(os.path.dirname(HO), 'heldout', f'{cid}_words.json'), encoding='utf8'))['words']
for w in W:
    q = (np.array(w['poly']) - [X0, Y0]) * f
    if q[:, 0].max() < 0 or q[:, 1].max() < 0 or q[:, 0].min() > s2.shape[1] or q[:, 1].min() > s2.shape[0]: continue
    cv2.polylines(s2, [np.round(q).astype(np.int32)], True, (255, 0, 170), 1)
    k = q[np.argmin(q[:, 1])]; cv2.putText(s2, str(w['annot_line']), (int(k[0]) + 2, int(k[1]) - 2), 0, 0.4, (160, 0, 120), 1)
for s in (s1, s2):
    for x in range((X0 // 25 + 1) * 25, X1, 25):
        xx = int((x - X0) * f); s[:6, xx] = (255, 0, 0)
        if x % 50 == 0: cv2.putText(s, str(x), (xx + 1, 14), 0, 0.35, (255, 0, 0), 1)
    for y in range((Y0 // 25 + 1) * 25, Y1, 25):
        yy = int((y - Y0) * f); s[yy, :6] = (255, 0, 0)
        if y % 50 == 0: cv2.putText(s, str(y), (1, yy - 2), 0, 0.35, (255, 0, 0), 1)
sep = np.full((s1.shape[0], 8, 3), 255, np.uint8)
cv2.imwrite(out, np.hstack([s1, sep, s2]) if s1.shape[1] < 700 else np.vstack([s1, np.full((8, s1.shape[1], 3), 255, np.uint8), s2]), [cv2.IMWRITE_JPEG_QUALITY, 92])
