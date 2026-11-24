"""Selection agent (23 Nov 2026), 1A only: would blanking the pseudo label near the line net's lines remove the
alley errors? The confident-block pixels on ground Ben left as street (small pieces only, the two big unclosed
pieces dropped as in ben1a.py --split) against a band of R half-size px around lines_ng1 > 0.5 that lies inside a
confident block region. Also the cost: how much correct confident block such a band would blank.
    python -B ben1a_lines.py     -> ben1a_lines.json
"""
import json, os, sys
import numpy as np
import cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ben1a as B  # noqa: E402
OUT = os.path.dirname(os.path.abspath(__file__))
P, L, W, H, saved, im = B.ben_blocks(); gt = B.raster(P, W, H); hh, hw = gt.shape
a4 = np.load(B.SP + 'cufp/1A/png_alpha_s4.npy').astype(np.uint8); paper = cv2.resize(a4, (hw, hh), interpolation=cv2.INTER_NEAREST) > 0
pa = cv2.imread(B.U + '1A_pred_area_ng1.png', 0); benb = gt > 0
bad = ((pa >= 243) & ~benb & paper).astype(np.uint8)
n, lab, st, _ = cv2.connectedComponentsWithStats(bad, connectivity=8)
big = [i for i in range(1, n) if st[i, cv2.CC_STAT_AREA] >= 50000]
small_bad = (bad > 0) & ~np.isin(lab, big)
ln = cv2.imread(B.U + '1A_lines_lines_ng1.png', 0); lnh = cv2.resize(ln, (hw, hh), interpolation=cv2.INTER_AREA) > 90
res = dict(small_error_px=int(small_bad.sum()), conf_block_px=int(((pa >= 243) & paper).sum()))
for R in (4, 8, 12):
    band = cv2.dilate(lnh.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * R + 1, 2 * R + 1))) > 0
    cb = (pa >= 243) & paper
    res[f'R{R}'] = dict(errors_removed=round(float((small_bad & band).sum() / max(1, small_bad.sum())), 3),
                        correct_block_blanked=round(float((cb & benb & band).sum() / max(1, (cb & benb).sum())), 3))
print(json.dumps(res, indent=1)); json.dump(res, open(os.path.join(OUT, 'ben1a_lines.json'), 'w', encoding='utf8', newline='\n'), indent=1)
