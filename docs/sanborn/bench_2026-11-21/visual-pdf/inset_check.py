"""Insets at another scale: does the area network see streets inside a 200-ft inset of a 400-ft sheet (and inside 78's
400-ft inset of a 200-ft sheet) as it does in the main map?

    python inset_check.py    -> inset_check.json, printed table

Regions are map_area.py's islands (maparea_check/N_mask8.png split by its frames, ids as in N_map_area.json);
street = area net P(block) <= 0.5 (unet_data/N_pred_area_ng1.png, half size); line = line net P > 0.5.
"""
import json, os
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__))
D = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; U = D + 'unet_data/'
SHEETS = {'46': {1: 200, 0: 400}, '48': {0: 400, 1: 200, 2: 200}, '92': {0: 400, 1: 400, 2: 200}, '94': {0: 400, 1: 200}, '78': {0: 200, 1: 400}}
res = {}
for n, scales in SHEETS.items():
    pa = cv2.imread(U + f'{n}_pred_area_ng1.png', 0); h, w = pa.shape
    pl = cv2.resize(cv2.imread(U + f'{n}_lines_lines_ng1.png', cv2.IMREAD_REDUCED_GRAYSCALE_2), (w, h), interpolation=cv2.INTER_AREA)
    m8 = cv2.imread(os.path.join(HERE, 'maparea_check', f'{n}_mask8.png'), 0) > 127
    ncc, cc = cv2.connectedComponents(m8.astype(np.uint8), connectivity=4)
    info = json.load(open(os.path.join(HERE, 'maparea_check', f'{n}_map_area.json')))
    rows = []
    for g in info['regions']:
        cx, cy = g['centroid']; lab = cc[min(m8.shape[0] - 1, cy // 8), min(m8.shape[1] - 1, cx // 8)]
        if lab == 0:                                     # centroid off the island: take the biggest label in its bbox
            x0, y0, x1, y1 = [v // 8 for v in g['bbox']]; sub = cc[y0:y1, x0:x1]; v = np.bincount(sub[sub > 0].ravel()); lab = int(np.argmax(v)) if v.size else 0
        reg = cv2.resize((cc == lab).astype(np.uint8), (w, h), interpolation=cv2.INTER_NEAREST) > 0
        rows.append(dict(region=g['id'], share_of_map=g['share_of_map'], ft_per_inch=scales.get(g['id']),
                         street_share=round(float((pa[reg] <= 127).mean()), 3), line_share=round(float((pl[reg] > 127).mean()), 4)))
    res[n] = rows; print(n, rows, flush=True)
json.dump(res, open(os.path.join(HERE, 'inset_check.json'), 'w'), indent=1)
