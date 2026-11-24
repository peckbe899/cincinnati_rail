# picture of a plate folder's labels: label (block green, street blue, untaught grey) and lines (positive red, negative untinted, 255 dark)
import sys, cv2, numpy as np
d = sys.argv[1].rstrip('/') + '/'; out = sys.argv[2]; sc = float(sys.argv[3]) if len(sys.argv) > 3 else 0.25
crop = [int(v) for v in sys.argv[4].split(',')] if len(sys.argv) > 4 else None   # x0,y0,x1,y1 full px
img = cv2.imread(d + 'img.jpg'); lab = cv2.imread(d + 'label.png', 0); t = cv2.imread(d + 'lines.png', 0)
H, W = t.shape
if crop:
    x0, y0, x1, y1 = crop; img = img[y0 // 2:y1 // 2, x0 // 2:x1 // 2]; lab = lab[y0 // 2:y1 // 2, x0 // 2:x1 // 2]; t = t[y0:y1, x0:x1]
s2 = sc * 2; im = cv2.resize(img, None, fx=s2, fy=s2, interpolation=cv2.INTER_AREA); lb = cv2.resize(lab, (im.shape[1], im.shape[0]), interpolation=cv2.INTER_NEAREST)
a = im.astype(np.float32)
a[lb == 1] = a[lb == 1] * 0.6 + np.array([0, 160, 0]) * 0.4; a[lb == 0] = a[lb == 0] * 0.6 + np.array([200, 80, 0]) * 0.4; a[lb == 255] = a[lb == 255] * 0.55 + 60
tt = cv2.resize(t, (im.shape[1], im.shape[0]), interpolation=cv2.INTER_NEAREST)
pos = cv2.resize((t == 1).astype(np.uint8), (im.shape[1], im.shape[0]), interpolation=cv2.INTER_AREA) > 0
pos = cv2.dilate((cv2.resize((t == 1).astype(np.float32), (im.shape[1], im.shape[0]), interpolation=cv2.INTER_AREA) > 0.05).astype(np.uint8), np.ones((2, 2), np.uint8)) > 0
a[pos] = (0, 0, 255)
cv2.imwrite(out, a.clip(0, 255).astype(np.uint8), [cv2.IMWRITE_JPEG_QUALITY, 88])
# lines alone: negative white, positive red, unscored grey
b = np.full(tt.shape + (3,), 120, np.uint8); b[tt == 0] = 255; b[pos] = (0, 0, 255)
cv2.imwrite(out.replace('.jpg', '_lines.jpg'), b, [cv2.IMWRITE_JPEG_QUALITY, 88])
