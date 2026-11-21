"""Open line ends by kind, to check auto_audit.py's classes by eye (visual-cut, 21 Nov 2026). Reads only.

    python ends_view.py N X0 Y0 W H [SCALE]      -> views/ends_N_X0_Y0.jpg

Rings at open ends (audit/N_audit.json): blue = broken side (a collinear piece within 400 px), yellow = open corner
(another side meets within 200 px), red = dangling (nothing to meet within 200 px). Lines as in view.py.
"""
import json, os, sys
import cv2
from vlib import load, draw, HERE
n = sys.argv[1]; x0, y0, w, h = map(int, sys.argv[2:6]); s = float(sys.argv[6]) if len(sys.argv) > 6 else min(1.0, 1900 / w)
D = load(n); im = draw(D, x0, y0, w, h, s, grid=500)
col = dict(broken=(255, 80, 0), corner=(0, 200, 255), dangling=(0, 0, 255))
for e in json.load(open(os.path.join(HERE, 'audit', f'{n}_audit.json')))['ends']:
    x, y = e['at']
    if x0 <= x < x0 + w and y0 <= y < y0 + h:
        cv2.circle(im, (int((x - x0) * s), int((y - y0) * s)), 12, col[e['kind']], 3, cv2.LINE_AA)
f = os.path.join(HERE, 'views', f'ends_{n}_{x0}_{y0}.jpg'); cv2.imwrite(f, im, [cv2.IMWRITE_JPEG_QUALITY, 88]); print(f, im.shape)
