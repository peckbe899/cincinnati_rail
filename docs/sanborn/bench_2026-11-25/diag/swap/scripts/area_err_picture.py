"""area_err_picture.py (diag/swap, 25 Nov 2026): an area map of plate 44 against Ben's map, at 1/8 size (or a crop at 1/4).
red = his street ground called block (P > 0.5), blue = his block called street, yellow = unsure (0.2 < P < 0.8) and right,
dark = ground he did not decide (with the map's block share there tinted green).
    python -B area_err_picture.py AREA_PNG OUT.jpg [x0 y0 x1 y1 full px]
"""
import sys, glob, json
import numpy as np, cv2
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
D = SP + 'bench_2026-11-25/diag/swap/'
W, H = 10768, 7219
f, out = sys.argv[1], sys.argv[2]; crop = [int(v) for v in sys.argv[3:7]] if len(sys.argv) >= 7 else None
sc = 0.25 if crop else 0.125; w, h = int(W * sc), int(H * sc)
sm = json.load(open(SP + 'streetmap/22-44.json', encoding='utf8'))
gt = np.zeros((h, w), np.uint8)
for b in sm['blocks']: cv2.fillPoly(gt, [(np.array(b['ring']) * sc).round().astype(np.int32)], 1)
dec = cv2.resize(cv2.imread(glob.glob(D + 'runs_baseline44/cache/decided_half_*_260.png')[0], 0), (w, h), interpolation=cv2.INTER_NEAREST) > 0
alpha = cv2.resize(np.load(SP + 'cufp/44/png_alpha_s4.npy').astype(np.float32), (w, h)) > 0.5
P = cv2.resize(cv2.imread(f, 0), (w, h), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
im = cv2.imread(SP + 'cufp/22-44.jpg', cv2.IMREAD_REDUCED_COLOR_4 if crop else cv2.IMREAD_REDUCED_COLOR_8)
im = cv2.resize(im, (w, h)).astype(np.float32); im = im * 0.55 + 100
blk = gt > 0; pb = P > 0.5; uns = (P > 0.2) & (P < 0.8)
def tint(m, c, a=0.6): im[m] = im[m] * (1 - a) + np.array(c, np.float32) * a
tint(dec & ~blk & pb, (0, 0, 230)); tint(dec & blk & ~pb, (230, 80, 0)); tint(dec & uns & (pb == blk), (0, 220, 255), 0.5)
v = alpha & ~dec; im[v] = im[v] * 0.6; tint(v & pb, (0, 160, 0), 0.35)
for b in sm['blocks']: cv2.polylines(im, [(np.array(b['ring']) * sc).round().astype(np.int32)], True, (255, 255, 255), 1)
im = im.clip(0, 255).astype(np.uint8)
if crop: x0, y0, x1, y1 = [int(v * sc) for v in crop]; im = im[y0:y1, x0:x1]
cv2.putText(im, f.replace(SP, '')[-70:], (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
cv2.imwrite(out, im, [cv2.IMWRITE_JPEG_QUALITY, 88]); print(out)
