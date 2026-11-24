"""Integrator (23 Nov 2026): compare validation cuts on plate 1A (right-hand image quarter, paper quarter, Elm St).
Reads the label maker's test output (labels/out/1A) and Ben's street map built there; writes ../val_options.json"""
import json, os
import numpy as np, cv2
from shapely.geometry import Polygon
T = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')) + '/'
SP = os.path.normpath(T + '../../') + '/'
d = T + 'labels/out/1A/'
lab = cv2.imread(d + 'label.png', 0); t = cv2.imread(d + 'lines.png', 0); sm = json.load(open(d + 'streetmap.json'))
h, w = lab.shape; W, H = sm['size']
a4 = np.load(SP + 'cufp/1A/png_alpha_s4.npy').astype(np.float32); paper = cv2.resize(a4, (w, h), interpolation=cv2.INTER_LINEAR) > 0.5
blocks = [Polygon(b['ring']) for b in sm['blocks']]
out = {}
for name, xh in (('image_quarter', int(w * 0.75)), ('paper_quarter', 1679), ('elm_st_centre', 1420)):
    xf = 2 * xh
    cen = sum(1 for p in blocks if p.centroid.x >= xf); cut = sum(1 for p in blocks if p.bounds[0] < xf < p.bounds[2])
    out[name] = dict(x_half=xh, x_full=xf, paper_share=round(float(paper[:, xh:].sum() / paper.sum()), 3), blocks_by_centroid=cen, blocks_cut=cut,
                     val_block_px=int((lab[:, xh:] == 1).sum()), val_street_px=int((lab[:, xh:] == 0).sum()), train_block_px=int((lab[:, :xh] == 1).sum()), train_street_px=int((lab[:, :xh] == 0).sum()),
                     val_line_pos=int((t[:, xf:] == 1).sum()), val_line_neg=int((t[:, xf:] == 0).sum()), train_line_pos=int((t[:, :xf] == 1).sum()), train_line_neg=int((t[:, :xf] == 0).sum()))
print(json.dumps(out, indent=1)); json.dump(out, open(T + 'integrate/val_options.json', 'w'), indent=1)
