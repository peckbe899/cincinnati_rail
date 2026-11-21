"""Read-only: lines_v2's saved 44 map (whole plate) and lines_ng1 (scratch inner box) against Ben's street map by kind."""
import json
import numpy as np, cv2
R = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; D = R + 'unet_data/'
S = 'C:/Users/peckb/AppData/Local/Temp/claude/8945a8e3044b4e4c/2a2bcb12-80e8-4366-9a59-3be15cce3445/scratchpad/ml_review/verify-line-net/'
sm = json.load(open(R + 'streetmap/22-44.json', encoding='utf8')); W, H = sm['size']
alpha = cv2.resize(np.load(R + 'cufp/44/png_alpha_s4.npy').astype(np.float32), (W, H)) > 0.5
K = {}
for kind in ('printed', 'drawn', 'sheet_edge'):
    m = np.zeros((H, W), np.uint8)
    for l in sm['lines']:
        if l['kind'] == kind: cv2.line(m, tuple(np.round(l['a']).astype(int)), tuple(np.round(l['b']).astype(int)), 1, 3)
    K[kind] = m > 0
allb = K['printed'] | K['drawn'] | K['sheet_edge']; k7 = np.ones((7, 7), np.uint8)
near_ben = cv2.dilate(allb.astype(np.uint8), k7) > 0
def vs_ben(p, box=None):
    pr = p > 0.5; npr = cv2.dilate(pr.astype(np.uint8), k7) > 0
    a = alpha if box is None else alpha[box]; nb = near_ben if box is None else near_ben[box]
    out = dict(precision_vs_ben_whole_paper=round(float((pr & nb & a).sum() / max(1, (pr & a).sum())), 4))
    for kind in ('printed', 'drawn'):
        kk = K[kind] if box is None else K[kind][box]; kk = kk & a
        out[f'recall_{kind}'] = round(float(npr[kk].mean()), 4) if kk.any() else None
        out[f'{kind}_px'] = int(kk.sum())
    return out
res = {}
pv = cv2.imread(D + '44_lines_lines_v2.png', 0).astype(np.float32) / 255
res['lines_v2_whole'] = vs_ben(pv)
box = (slice(850, 2150), slice(2050, 4250))
res['lines_v2_inner_box'] = vs_ben(pv[box], box)
pn = np.load(S + 'v2_area_inner.npy').astype(np.float32) / 255
res['lines_ng1_inner_box'] = vs_ben(pn, box)
print(json.dumps(res, indent=1)); json.dump(res, open(S + 'v3_ben.json', 'w'), indent=1)
