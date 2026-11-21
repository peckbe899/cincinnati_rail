import sys, numpy as np, cv2
D = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
n, x0, y0, w, h, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]), sys.argv[6]
full = cv2.imread(D + f'cufp/22-{n}.jpg'); c = full[y0:y0 + h, x0:x0 + w].copy()
for gx in range((x0 // 50 + 1) * 50, x0 + w, 50):
    X = gx - x0; cv2.line(c, (X, 0), (X, h), (255, 0, 255) if gx % 100 == 0 else (255, 190, 255), 1)
    if gx % 100 == 0: cv2.putText(c, str(gx), (X + 2, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (160, 0, 160), 1)
for gy in range((y0 // 50 + 1) * 50, y0 + h, 50):
    Y = gy - y0; cv2.line(c, (0, Y), (w, Y), (255, 0, 255) if gy % 100 == 0 else (255, 190, 255), 1)
    if gy % 100 == 0: cv2.putText(c, str(gy), (2, Y - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (160, 0, 160), 1)
cv2.imwrite(out, c, [cv2.IMWRITE_JPEG_QUALITY, 88])
