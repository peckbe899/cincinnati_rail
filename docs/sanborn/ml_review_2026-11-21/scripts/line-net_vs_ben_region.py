"""Read-only: lines_ng1 (CPU run, region y 0:3328 x 0:6656 of 44) and lines_v2 (saved) against Ben's checked street map."""
import json
import numpy as np, cv2
R = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; D = R + 'unet_data/'; S = 'C:/Users/peckb/AppData/Local/Temp/claude/8945a8e3044b4e4c/2a2bcb12-80e8-4366-9a59-3be15cce3445/scratchpad/ml_review/line-net/'
H, W = 7219, 10768; Y1, X1 = 3328, 6656; TOL = 3
sm = json.load(open(R + 'streetmap/22-44.json', encoding='utf8'))
ben = {k: np.zeros((H, W), np.uint8) for k in ('printed', 'drawn', 'sheet_edge')}
for l in sm['lines']: cv2.line(ben[l['kind']], tuple(np.round(l['a']).astype(int)), tuple(np.round(l['b']).astype(int)), 1, 3)
ben = {k: v[:Y1, :X1] > 0 for k, v in ben.items()}
alpha = (cv2.resize(np.load(R + 'cufp/44/png_alpha_s4.npy').astype(np.float32), (W, H)) > 0.5)[:Y1, :X1]
k = np.ones((2 * TOL + 1, 2 * TOL + 1), np.uint8)
near_ben = cv2.dilate((ben['printed'] | ben['drawn'] | ben['sheet_edge']).astype(np.uint8), k) > 0
out = {}
for name, p in (('lines_ng1', np.load(S + 'ng1_44_area.npy') > 127), ('lines_ng1_area128', np.load(S + 'ng1_44_none.npy') > 127), ('lines_v2', cv2.imread(D + '44_lines_lines_v2.png', 0)[:Y1, :X1] > 127)):
    pa = p & alpha; near_p = cv2.dilate(p.astype(np.uint8), k) > 0
    out[name] = dict(precision_vs_ben=round(float(near_ben[pa].mean()), 4), recall_printed=round(float(near_p[ben['printed'] & alpha].mean()), 4),
                     recall_drawn=round(float(near_p[ben['drawn'] & alpha].mean()), 4), drawn_px=int(pa.sum()))
    print(name, json.dumps(out[name]))
out['ben_px'] = {k_: int((v & alpha).sum()) for k_, v in ben.items()}
print(out['ben_px'])
json.dump(out, open(S + 'vs_ben_region.json', 'w'), indent=1)
