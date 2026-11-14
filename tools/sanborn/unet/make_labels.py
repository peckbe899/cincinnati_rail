"""Training pair for the block / street U-net from a placed plate (14 November 2026).

    cd data/sanborn
    ../../tools/sanborn/unet/.venv/Scripts/python.exe ../../tools/sanborn/unet/make_labels.py N [TAG]

The image is the plate scan at half size (about 2.4 px per metre). The label comes free from the placement: today's
parcel blocks (today/blocks_N.geojson, guided/parcels.py) drawn onto the plate through the plate's model (TAG, default
'guided'). Classes: 0 street or other open ground, 1 block, 255 ignore. Ignored: off the paper, and a band IGN px
either side of every label edge, because the placement is good to a few metres only; the network has to find the edge
from the picture, not from a label that is slightly off.
Writes unet_data/N_img.jpg, N_label.png, N_meta.json (not committed: remade from the scan and the parcels).
"""
import json, os, sys
import numpy as np
import cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, '..', 'guided'))
import streets as S  # noqa: E402
from scipy.interpolate import LinearNDInterpolator  # noqa: E402
from shapely.geometry import shape  # noqa: E402
J = S.J
N = sys.argv[1]; TAG = sys.argv[2] if len(sys.argv) > 2 else 'guided'; K, IGN = 2, 7
SP = S.SP; OUT = SP + 'unet_data/'; os.makedirs(OUT, exist_ok=True)
full = cv2.imread(SP + f'cufp/22-{N}.jpg'); H, W = full.shape[:2]
img = cv2.resize(full, (W // K, H // K), interpolation=cv2.INTER_AREA); h, w = img.shape[:2]
gx, gy = np.meshgrid(np.linspace(-300, W + 300, 120), np.linspace(-300, H + 300, 90)); P = np.c_[gx.ravel(), gy.ravel()]
inv = LinearNDInterpolator(J.world_many(f'22-{N}', P, TAG), P)
lab = np.zeros((h, w), np.uint8)
for f in json.load(open(SP + f'today/blocks_{N}.geojson', encoding='utf8'))['features']:
    q = inv(np.asarray(shape(f['geometry']).exterior.segmentize(3).coords)[:, :2]) / K
    q = q[~np.isnan(q[:, 0])]
    if len(q) >= 3: cv2.fillPoly(lab, [q.astype(np.int32)], 1)
edge = cv2.morphologyEx(lab, cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)) > 0
band = cv2.dilate(edge.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * IGN + 1, 2 * IGN + 1))) > 0
alpha = cv2.resize(np.load(SP + f'cufp/{N}/png_alpha_s4.npy').astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR) > 0.5
out = lab.copy(); out[band] = 255; out[~alpha] = 255
cv2.imwrite(OUT + f'{N}_img.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 92]); cv2.imwrite(OUT + f'{N}_label.png', out)
json.dump(dict(plate=N, tag=TAG, scale=K, ignore_px=IGN, size=[w, h], block=float((out == 1).mean()), street=float((out == 0).mean()), ignore=float((out == 255).mean())),
          open(OUT + f'{N}_meta.json', 'w', encoding='utf8', newline='\n'), indent=1)
vis = img.copy(); vis[out == 1] = (vis[out == 1] * 0.6 + np.array([0, 120, 0]) * 0.4).astype(np.uint8); vis[out == 0] = (vis[out == 0] * 0.6 + np.array([200, 60, 0]) * 0.4).astype(np.uint8)
cv2.imwrite(OUT + f'{N}_check.jpg', cv2.resize(vis, None, fx=0.5, fy=0.5), [cv2.IMWRITE_JPEG_QUALITY, 80])
print(json.load(open(OUT + f'{N}_meta.json')))
