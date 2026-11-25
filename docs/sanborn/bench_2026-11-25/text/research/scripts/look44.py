"""Overview and a few full-size crops of plate 44, to look at the lettering by eye.
Writes pics/44_overview.jpg and pics/44_crop_<name>.jpg. Reads only data/sanborn/cufp/22-44.jpg."""
import os, sys, cv2
R = r'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D'
O = os.path.join(R, 'data/sanborn/bench_2026-11-25/text/research/pics')
plate = sys.argv[1] if len(sys.argv) > 1 else '44'
im = cv2.imread(os.path.join(R, f'data/sanborn/cufp/22-{plate}.jpg'))
h, w = im.shape[:2]
print(plate, w, h)
s = 1600 / w
ov = cv2.resize(im, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
for x in range(0, w, 1000):
    cv2.line(ov, (int(x * s), 0), (int(x * s), ov.shape[0]), (0, 0, 255), 1)
    cv2.putText(ov, str(x // 1000), (int(x * s) + 2, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
for y in range(0, h, 1000):
    cv2.line(ov, (0, int(y * s)), (ov.shape[1], int(y * s)), (0, 0, 255), 1)
    cv2.putText(ov, str(y // 1000), (2, int(y * s) + 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
cv2.imwrite(os.path.join(O, f'{plate}_overview.jpg'), ov, [cv2.IMWRITE_JPEG_QUALITY, 85])
# crops given as name:x0,y0,x1,y1 on the command line
for a in sys.argv[2:]:
    n, b = a.split(':')
    x0, y0, x1, y1 = map(int, b.split(','))
    cv2.imwrite(os.path.join(O, f'{plate}_crop_{n}.jpg'), im[y0:y1, x0:x1], [cv2.IMWRITE_JPEG_QUALITY, 90])
