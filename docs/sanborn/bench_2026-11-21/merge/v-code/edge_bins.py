"""v-code: where plate 90's block-line ink (bin 1) of the staged fallback lies: near the paper's edge, off the map ground (read only)."""
import json, sys
import numpy as np, cv2
ME = 'bench_2026-11-21/merge/v-code/runs/'
b = cv2.imread(ME + 'i90/90_bins.png', 0); H, W = b.shape
al = cv2.resize(np.load('cufp/90/png_alpha_s4.npy'), (W, H), interpolation=cv2.INTER_NEAREST) > 0
d = cv2.distanceTransform(np.pad(al.astype(np.uint8), 1), cv2.DIST_L2, 5)[1:-1, 1:-1]
mg = cv2.resize(cv2.imread(ME + 'b90/90_mapground.png', 0), (W, H), interpolation=cv2.INTER_NEAREST) > 0
bl = b == 1
out = dict(block_line_px=int(bl.sum()), within_7px_of_paper_edge=int((bl & (d <= 7)).sum()), within_40px=int((bl & (d <= 40)).sum()),
           off_map_ground=int((bl & ~mg).sum()), off_map_ground_not_near_edge=int((bl & ~mg & (d > 40)).sum()),
           all_ink_within_7px_of_edge=int(((b > 0) & (d <= 7)).sum()))
print(json.dumps(out))
