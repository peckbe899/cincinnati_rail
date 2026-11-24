"""Selection agent (23 Nov 2026): plate 1A's validation area. The right-hand quarter of the image against a strip
cut where the paper (not the image) reaches 75%, from the left. Counts Ben's blocks (centroid) and paper in each.
    python -B val1a.py   -> val1a.json
"""
import json, os, sys
import numpy as np
import cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ben1a as B  # noqa: E402
P, L, W, H, saved, im = B.ben_blocks(); gt = B.raster(P, W, H); hh, hw = gt.shape
a4 = np.load(B.SP + 'cufp/1A/png_alpha_s4.npy').astype(np.uint8); paper = cv2.resize(a4, (hw, hh), interpolation=cv2.INTER_NEAREST) > 0
col = paper.sum(0).cumsum() / paper.sum(); xp = int(np.searchsorted(col, 0.75))
cx = [float(p.centroid.x) / 2 for p in P]; area = [p.area / 4 for p in P]
out = {}
for name, x0 in (('image_quarter', int(hw * 0.75)), ('paper_quarter', xp)):
    inside = [i for i, c in enumerate(cx) if c >= x0]
    part = sum(float((gt[:, x0:] == i + 1).sum()) for i in range(len(P)))
    out[name] = dict(x_half=x0, x_full=2 * x0, x_share_of_width=round(x0 / hw, 3), paper_share=round(float(paper[:, x0:].sum() / paper.sum()), 3),
                     ben_blocks_by_centroid=len(inside), ben_block_px_right_of_cut=int(part), ben_blocks_cut_by_line=sum(1 for i in range(len(P)) if (gt[:, :x0] == i + 1).any() and (gt[:, x0:] == i + 1).any()))
print(json.dumps(out, indent=1)); json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'val1a.json'), 'w', encoding='utf8', newline='\n'), indent=1)
