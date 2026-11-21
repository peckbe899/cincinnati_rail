"""Crop a region of a full-size scan for reading (scale notes, inset frames).

    python crop.py OUT.jpg SCALE N:x0,y0,x1,y1 [N:x0,y0,x1,y1 ...]     coordinates in full-size px; crops stacked vertically
"""
import sys
import numpy as np, cv2
D = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
out, s = sys.argv[1], float(sys.argv[2]); ims = []
for spec in sys.argv[3:]:
    n, box = spec.split(':'); x0, y0, x1, y1 = map(int, box.split(','))
    im = cv2.imread(D + f'cufp/22-{n}.jpg')
    c = cv2.resize(im[y0:y1, x0:x1], None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    cv2.putText(c, n, (5, 30), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2); ims.append(c)
w = max(c.shape[1] for c in ims)
ims = [cv2.copyMakeBorder(c, 0, 4, 0, w - c.shape[1], cv2.BORDER_CONSTANT, value=(255, 255, 255)) for c in ims]
cv2.imwrite(out, np.vstack(ims), [cv2.IMWRITE_JPEG_QUALITY, 85])
