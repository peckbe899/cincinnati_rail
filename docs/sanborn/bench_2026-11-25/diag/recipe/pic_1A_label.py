"""A picture of 1A's training label (train_v2/1A/label.png) over the scan: block green, street red, untaught grey,
Ben's lines by kind (printed dark green, drawn magenta, sheet edge blue), the validation region hatched. Also the same
for plate 43's 21 Nov label for comparison. Writes pics/ beside this file. Reads only."""
import json, os, numpy as np, cv2
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; OUT = SP + 'bench_2026-11-25/diag/recipe/pics/'; os.makedirs(OUT, exist_ok=True)
def paint(img, lab, alpha=0.45):
    c = img.copy(); col = np.zeros_like(img); col[lab == 1] = (60, 170, 60); col[lab == 0] = (60, 60, 220); col[lab == 255] = (150, 150, 150)
    return (c * (1 - alpha) + col * alpha).astype(np.uint8)
img = cv2.imread(SP + 'train_v2/1A/img.jpg'); lab = cv2.imread(SP + 'train_v2/1A/label.png', 0); vm = cv2.imread(SP + 'train_v2/1A/valmask.png', 0) > 0
c = paint(img, lab)
c[vm & ((np.indices(vm.shape).sum(0) // 6) % 6 == 0)] = (0, 200, 255)
T = json.load(open(SP + 'train_v2/1A/streetmap.json', encoding='utf8')); COL = dict(printed=(0, 90, 0), drawn=(200, 0, 200), sheet_edge=(255, 80, 0), no_printed_line=(0, 140, 255))
for l in T['lines']: cv2.line(c, tuple((np.array(l['a']) / 2).round().astype(int)), tuple((np.array(l['b']) / 2).round().astype(int)), COL[l['kind']], 3)
cv2.imwrite(OUT + '1A_label_lines.jpg', cv2.resize(c, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 88])
cv2.imwrite(OUT + '1A_label_lines_full.jpg', c, [cv2.IMWRITE_JPEG_QUALITY, 85])
for p in ['43', '82A']:
    img = cv2.imread(SP + f'train_v2/{p}/img.jpg'); lab = cv2.imread(SP + f'train_v2/{p}/label.png', 0)
    cv2.imwrite(OUT + f'{p}_label.jpg', cv2.resize(paint(img, lab), None, fx=0.3, fy=0.3, interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 85])
print('ok')
