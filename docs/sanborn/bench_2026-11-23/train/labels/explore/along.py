# explore: line-net and area-net values along Ben's lines on a plate, by kind (nothing written)
import json, sys
import numpy as np, cv2
sys.path.insert(0, '../../tools/sanborn/unet'); sys.path.insert(0, '../../tools/sanborn')
import street_map as SM
N = sys.argv[1]
B = json.load(open(f'picks22_guided/22-{N}/edges_ben.json', encoding='utf8'))
im = cv2.imread(f'cufp/22-{N}.jpg'); H, W = im.shape[:2]
L, SH = SM.editor_lines(N, W, H, json.load(open(f'unet_data/{N}_edges.json', encoding='utf8')), B)
pl = cv2.imread(f'unet_data/{N}_lines_lines_ng1.png', 0); pa = cv2.imread(f'unet_data/{N}_pred_area_ng1.png', 0)
plm = cv2.dilate(pl, np.ones((7, 7), np.uint8))   # max within 3 px
for kind in ('printed', 'drawn', 'sheet_edge'):
    v = []; lens = []
    for l in L:
        if l['kind'] != kind: continue
        a, b = np.array(l['a']), np.array(l['b']); n = max(2, int(np.hypot(*(b - a)))); q = a + np.outer(np.linspace(0, 1, n), b - a)
        x = np.clip(q[:, 0].round().astype(int), 0, W - 1); y = np.clip(q[:, 1].round().astype(int), 0, H - 1)
        v.append(plm[y, x]); lens.append(n)
    if not v: continue
    v = np.concatenate(v)
    print(kind, 'lines', len(lens), 'len', sum(lens), 'line-net max within 3px: share >127', round(float((v > 127).mean()), 3), '>50', round(float((v > 50).mean()), 3), '>25', round(float((v > 25).mean()), 3), '>10', round(float((v > 10).mean()), 3), '>3', round(float((v > 3).mean()), 3))
