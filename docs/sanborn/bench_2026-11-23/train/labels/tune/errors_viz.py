# 1A only: where the pseudo area label disagrees with Ben's map (red: pseudo block on his street; blue: pseudo street on his block)
import sys, json, numpy as np, cv2
sys.path.insert(0, 'bench_2026-11-23/train/staged/tools/sanborn/unet')
import make_labels_v2 as M
th = dict(M.PSEUDO, **json.loads(sys.argv[1])); I = M.pseudo_inputs('1A'); al, _ = M.alley_strips(I, 100)
lab, t, e, c = M.pseudo_labels(I, th, 100, al); ml = cv2.imread('bench_2026-11-23/train/labels/out/1A/label.png', 0)
img = cv2.imread('bench_2026-11-23/train/labels/out/1A/img.jpg').astype(np.float32) * 0.5 + 100
fb = (lab == 1) & (ml == 0); fs = (lab == 0) & (ml == 1)
img[fb] = (0, 0, 255); img[fs] = (255, 0, 0)
print('false block px', int(fb.sum()), 'false street px', int(fs.sum()))
n, cc, st, _ = cv2.connectedComponentsWithStats(fs.astype(np.uint8)); big = np.argsort(-st[1:, 4])[:8] + 1
print('largest false-street pieces (x, y, w, h, px, half size):', [st[k].tolist() for k in big])
n, cc, st, _ = cv2.connectedComponentsWithStats(fb.astype(np.uint8)); big = np.argsort(-st[1:, 4])[:8] + 1
print('largest false-block pieces:', [st[k].tolist() for k in big])
cv2.imwrite('bench_2026-11-23/train/labels/tune/1A_area_errors.jpg', cv2.resize(img.astype(np.uint8), None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA))
