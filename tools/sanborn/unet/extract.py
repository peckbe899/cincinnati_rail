"""Blocks and streets of a plate from the U-net's prediction (14 November 2026).

    cd data/sanborn
    ../../tools/sanborn/unet/.venv/Scripts/python.exe ../../tools/sanborn/unet/extract.py N NAME

unet_data/N_pred_NAME.png (P(block), half size) -> on the paper: block where P > 0.5 (specks under MIN_M2 dropped,
holes filled), street elsewhere. Writes, in plate pixels:
  picks22_guided/22-N/unet_blocks.json   block outlines (polygons)
  picks22_guided/22-N/unet_obs.json      "edges": points every STEP px along the block outlines;
                                         "centres": points every STEP px along the thinned street area (centre lines)
  unet_data/N_extract_NAME.jpg           the picture for checking
The solver (guided/solve.py) uses the edge points against today's block edges and the centre points against today's
centre lines, each weighted by its fit like every other observation.
"""
import json, os, sys
import numpy as np
import cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, '..'))
import _ws  # noqa: E402
N, NAME = sys.argv[1], sys.argv[2]; SP = _ws.DATA; K, STEP, MIN_PX = 2, 60, 1500
p = cv2.imread(SP + f'unet_data/{N}_pred_{NAME}.png', 0); h, w = p.shape
alpha = cv2.resize(np.load(SP + f'cufp/{N}/png_alpha_s4.npy').astype(np.float32), (w, h)) > 0.5
alpha = cv2.erode(alpha.astype(np.uint8), np.ones((9, 9), np.uint8)) > 0
blk = ((p > 127) & alpha).astype(np.uint8)
blk = cv2.morphologyEx(blk, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
n, lab, st, _ = cv2.connectedComponentsWithStats(blk, connectivity=4)
for i in range(1, n):
    if st[i, cv2.CC_STAT_AREA] < MIN_PX: blk[lab == i] = 0
street = (alpha & (blk == 0)).astype(np.uint8)
n, lab, st, _ = cv2.connectedComponentsWithStats(street, connectivity=4)      # specks of "street" inside a block
for i in range(1, n):
    if st[i, cv2.CC_STAT_AREA] < MIN_PX: street[lab == i] = 0; blk[lab == i] = 1
cs, _ = cv2.findContours(blk, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
blocks, edges = [], []
inner = cv2.erode(alpha.astype(np.uint8), np.ones((25, 25), np.uint8)) > 0         # an outline along the paper's edge is not a block edge
for c in cs:
    c = c[:, 0, :]
    blocks.append((cv2.approxPolyDP(c.reshape(-1, 1, 2), 1.5, True)[:, 0, :] * K).tolist())
    for q in c[::STEP // K]:
        if inner[q[1], q[0]]: edges.append([int(q[0] * K), int(q[1] * K)])
sk = cv2.ximgproc.thinning(street * 255)
ys, xs = np.where((sk > 0) & inner); order = np.lexsort((xs // 30, ys // 30)); keep = {}
for x, y in zip(xs[order], ys[order]): keep.setdefault((x // (STEP // K), y // (STEP // K)), [int(x * K), int(y * K)])
centres = list(keep.values())
D = SP + f'picks22_guided/22-{N}/'
json.dump(blocks, open(D + 'unet_blocks.json', 'w', encoding='utf8', newline='\n'))
json.dump(dict(model=NAME, edges=edges, centres=centres), open(D + 'unet_obs.json', 'w', encoding='utf8', newline='\n'))
img = cv2.imread(SP + f'unet_data/{N}_img.jpg'); vis = (img * 0.7 + 76).astype(np.uint8)
cv2.drawContours(vis, cs, -1, (0, 130, 0), 2); vis[sk > 0] = (220, 40, 0)
for q in edges: cv2.circle(vis, (q[0] // K, q[1] // K), 3, (0, 80, 0), -1)
cv2.imwrite(SP + f'unet_data/{N}_extract_{NAME}.jpg', cv2.resize(vis, None, fx=0.6, fy=0.6, interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 82])
print('blocks', len(blocks), 'edge points', len(edges), 'centre points', len(centres))
