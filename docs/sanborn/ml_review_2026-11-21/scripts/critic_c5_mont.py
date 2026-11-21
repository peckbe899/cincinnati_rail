import sys, numpy as np, cv2
D = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; OUT = sys.argv[1]; pl = sys.argv[3:]; tag = sys.argv[2]
ims = []
for n in pl:
    full = cv2.imread(D + f'cufp/22-{n}.jpg', cv2.IMREAD_REDUCED_COLOR_4)
    s = 1300 / full.shape[1]; t = cv2.resize(full, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    t = cv2.copyMakeBorder(t[:870], 0, max(0, 870 - t.shape[0]), 0, 0, cv2.BORDER_CONSTANT)
    cv2.putText(t, n, (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 2.5, (0, 0, 255), 5); ims.append(t)
while len(ims) % 2: ims.append(np.zeros_like(ims[0]))
rows = [np.hstack(ims[k:k + 2]) for k in range(0, len(ims), 2)]
cv2.imwrite(OUT + f'/mont_{tag}.jpg', np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 85])
