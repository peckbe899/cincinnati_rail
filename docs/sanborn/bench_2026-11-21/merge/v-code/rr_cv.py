"""v-code: ink_bins.railroad on plate N with the block ground of an outline run, saved as a PNG in v-code/runs/ (run under
each interpreter; compares cv2 builds). Read only on the repo."""
import json, sys
import numpy as np, cv2
sys.path.insert(0, 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-21/merge/staged/tools/sanborn/unet'); import ink_bins as IB  # noqa
N, D, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
full = cv2.imread(f'cufp/22-{N}.jpg'); H, W = full.shape[:2]
al = cv2.resize(np.load(f'cufp/{N}/png_alpha_s4.npy'), (W, H), interpolation=cv2.INTER_NEAREST) > 0
ink = (cv2.cvtColor(full, cv2.COLOR_BGR2LAB)[..., 0] < IB.INK_L) & al
G = IB.block_ground(json.load(open(D + '/outlines.json', encoding='utf8')), H, W)
rr, info = IB.railroad(ink, G, al)
cv2.imwrite(OUT, rr.astype(np.uint8) * 255); print(cv2.__version__, int(rr.sum()), info['clear'], info['faint'], info['chained'])
