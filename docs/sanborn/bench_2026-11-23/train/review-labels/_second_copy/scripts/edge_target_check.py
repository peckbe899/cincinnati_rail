"""review-labels, 24 Nov 2026: the area net's third output (edge target, unet.edge_maps) on Ben's printed and drawn lines.
    python -B edge_target_check.py LABEL_DIR N STREETMAP.json      prints the shares of Ben's line length (sampled at half size) where
    the edge target is 1 (an edge), 0 (taught 'no edge') or 255 (not taught)."""
import json, sys
import numpy as np
import cv2
d, N, smf = sys.argv[1:4]
lab = cv2.imread(f'{d}/{N}/label.png', 0); e = cv2.imread(f'{d}/{N}/edge.png', 0); sm = json.load(open(smf, encoding='utf8'))
tgt = (cv2.dilate(e, np.ones((3, 3), np.uint8)) > 0).astype(np.uint8); tgt[(lab == 255) & (tgt == 0)] = 255       # unet.edge_maps
h, w = lab.shape; c = dict(edge=0, no_edge=0, untaught=0)
for l in sm['lines']:
    if l['kind'] not in ('printed', 'drawn'): continue
    a, b = np.array(l['a'], float) / 2, np.array(l['b'], float) / 2; n = max(2, int(np.hypot(*(b - a))) + 1); q = a + np.outer(np.linspace(0, 1, n), b - a)
    v = tgt[np.clip(q[:, 1].round().astype(int), 0, h - 1), np.clip(q[:, 0].round().astype(int), 0, w - 1)]
    c['edge'] += int((v == 1).sum()); c['no_edge'] += int((v == 0).sum()); c['untaught'] += int((v == 255).sum())
t = sum(c.values()); print(N, d, {k: round(v / t, 4) for k, v in c.items()}, 'samples', t)
