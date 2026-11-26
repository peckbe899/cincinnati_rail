"""view.py X0 Y0 X1 Y1 scale out.jpg [grid]: a plate-90 window with a full-plate coordinate grid (by eye only)"""
import sys, cv2
X0, Y0, X1, Y1 = map(int, sys.argv[1:5]); f = float(sys.argv[5]); out = sys.argv[6]
g = int(sys.argv[7]) if len(sys.argv) > 7 else 100
plate = sys.argv[8] if len(sys.argv) > 8 else '90'
im = cv2.imread(f'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/cufp/22-{plate}.jpg')
c = im[Y0:Y1, X0:X1]
s = cv2.resize(c, None, fx=f, fy=f, interpolation=cv2.INTER_AREA if f < 1 else cv2.INTER_CUBIC)
for x in range((X0 // g + 1) * g, X1, g):
    xx = int((x - X0) * f); cv2.line(s, (xx, 0), (xx, s.shape[0]), (255, 120, 0), 1)
    cv2.putText(s, str(x), (xx + 2, 11), 0, 0.38, (255, 0, 0), 1)
for y in range((Y0 // g + 1) * g, Y1, g):
    yy = int((y - Y0) * f); cv2.line(s, (0, yy), (s.shape[1], yy), (255, 120, 0), 1)
    cv2.putText(s, str(y), (2, yy - 2), 0, 0.38, (255, 0, 0), 1)
cv2.imwrite(out, s, [cv2.IMWRITE_JPEG_QUALITY, 92]); print(s.shape)
