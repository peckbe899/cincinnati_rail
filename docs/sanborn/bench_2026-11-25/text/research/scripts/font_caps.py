"""Picture only: plate 44's printed street-name capitals and italic labels beside the same words set in fonts
already on this machine (C:/Windows/Fonts) and OpenCV's built-in Hershey stroke fonts. Writes pics/font_caps.png.
No numbers come from this script; it is for judging by eye."""
import os, cv2, numpy as np
from PIL import Image, ImageDraw, ImageFont
R = r'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D'
B = os.path.join(R, 'data/sanborn/bench_2026-11-25/text/research')
scan = cv2.imread(os.path.join(R, 'data/sanborn/cufp/22-44.jpg'), cv2.IMREAD_GRAYSCALE)
H = 64
W = 760


def row_img(img, label):
    r = np.full((H + 8, W + 190), 255, np.uint8)
    cv2.putText(r, label[:22], (2, H // 2 + 6), cv2.FONT_HERSHEY_SIMPLEX, 0.45, 0, 1)
    s = min(H / img.shape[0], W / img.shape[1])
    im = cv2.resize(img, (int(img.shape[1] * s), int(img.shape[0] * s)), interpolation=cv2.INTER_AREA)
    r[4:4 + im.shape[0], 190:190 + im.shape[1]] = im
    return r


def ttf(path, text, italic_shear=0.0):
    f = ImageFont.truetype(path, 80)
    im = Image.new('L', (80 * len(text), 160), 255)
    ImageDraw.Draw(im).text((20, 20), text, fill=0, font=f)
    a = np.array(im)
    if italic_shear:
        h, w = a.shape
        A = np.float32([[1, -italic_shear, italic_shear * h / 2], [0, 1, 0]])
        a = cv2.warpAffine(a, A, (w, h), borderValue=255)
    ys, xs = np.nonzero(a < 128)
    return a[ys.min() - 4:ys.max() + 5, xs.min() - 4:xs.max() + 5]


def hershey(face, text):
    a = np.full((140, 90 * len(text)), 255, np.uint8)
    cv2.putText(a, text, (10, 100), face, 3.0, 0, 6, cv2.LINE_AA)
    ys, xs = np.nonzero(a < 128)
    return a[ys.min() - 4:ys.max() + 5, xs.min() - 4:xs.max() + 5]


rows = [row_img(scan[1925:2035, 5720:6150], 'REAL 44: KNOWLTON')]
F = 'C:/Windows/Fonts/'
for n in ['framd.ttf', 'FRAMDCN.TTF', 'FRADM.TTF', 'GOTHIC.TTF', 'arial.ttf', 'ARIALN.TTF', 'bahnschrift.ttf',
          'TCM_____.TTF', 'TCCM____.TTF', 'COPRGTL.TTF', 'LiberationSansNarrow-Regular.ttf', 'DejaVuSansCondensed.ttf']:
    rows.append(row_img(ttf(F + n, 'KNOWLTON'), n))
rows.append(row_img(hershey(cv2.FONT_HERSHEY_SIMPLEX, 'KNOWLTON'), 'hershey simplex'))
rows.append(row_img(hershey(cv2.FONT_HERSHEY_DUPLEX, 'KNOWLTON'), 'hershey duplex'))
rows.append(np.full((10, W + 190), 128, np.uint8))
rows.append(row_img(scan[1960:2000, 5480:5640], 'REAL 44: 6" W. PIPE'))
for n in ['ariali.ttf', 'ARIALNI.TTF', 'TCMI____.TTF', 'framdit.ttf']:
    rows.append(row_img(ttf(F + n, '6" W. PIPE'), n))
rows.append(row_img(ttf(F + 'TCCM____.TTF', '6" W. PIPE', 0.25), 'TCCM + slant'))
rows.append(row_img(hershey(cv2.FONT_HERSHEY_SIMPLEX | cv2.FONT_ITALIC, '6" W. PIPE'), 'hershey simplex italic'))
cv2.imwrite(os.path.join(B, 'pics/font_caps.png'), np.vstack(rows))
