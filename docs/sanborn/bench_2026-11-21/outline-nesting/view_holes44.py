"""Picture of plate 44's hole polygons (RETR_TREE run) over the scan, with Ben's lines and the rail bins.

    python view_holes44.py [RUN_TAG]   -> runs/RUN_TAG/holes44_view.jpg (quarter size) and holes44_crop_*.jpg (half size)

Hole sides that step 4 keeps: cyan where on Ben's lines, red where not; Ben's lines thin magenta; decided ground's edge
yellow; rail bins (N_bins.png railroad/streetcar, if readable) tinted orange; hole number in white.
"""
import json, os, sys
import numpy as np
import cv2
HERE = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/') + '/'
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
tag = sys.argv[1] if len(sys.argv) > 1 else 'nest'; run = HERE + f'runs/{tag}/'
info = json.load(open(run + 'holes44.json'))
polys = json.load(open(run + 'outlines.json', encoding='utf8'))
sm = json.load(open(SP + 'streetmap/22-44.json', encoding='utf8'))
S = 0.5
im = cv2.imread(SP + 'cufp/22-44.jpg', cv2.IMREAD_REDUCED_COLOR_2)
im = (im * 0.75 + 50).astype(np.uint8)
bins = cv2.imread(SP + 'unet_data/44_bins.png', cv2.IMREAD_UNCHANGED)
bj = json.load(open(SP + 'unet_data/44_bins.json', encoding='utf8'))
names = {int(k): v['name'] for k, v in bj['bins'].items()}
if bins is not None:
    if bins.ndim == 3: bins = bins[:, :, 0]
    b2 = cv2.resize(bins, (im.shape[1], im.shape[0]), interpolation=cv2.INTER_NEAREST)
    rail = np.isin(b2, [k for k, v in names.items() if v in ('railroad', 'streetcar')])
    im[rail] = (im[rail] * 0.4 + np.array([0, 120, 255]) * 0.6).astype(np.uint8)
dec = cv2.imread(HERE + 'cache/decided_half.png', 0)
dec = cv2.resize(dec, (im.shape[1], im.shape[0]), interpolation=cv2.INTER_NEAREST)
cs, _ = cv2.findContours((dec > 0).astype(np.uint8), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
cv2.drawContours(im, cs, -1, (0, 220, 255), 2)
for l in sm['lines']:
    cv2.line(im, tuple((np.array(l['a']) * S).astype(int)), tuple((np.array(l['b']) * S).astype(int)), (200, 0, 200), 1, cv2.LINE_AA)
for r in info['holes']:
    p = polys[r['poly']]
    ring = (np.array([s['a'] for s in p]) * S).astype(np.int32)
    cv2.polylines(im, [ring], True, (255, 255, 255), 1, cv2.LINE_AA)
    k = 0
    for s in p:
        if s['state'] == 'short' or s.get('paper_edge'): continue
        on = r['per_side'][k]['on_ben'] if 'per_side' in r else 0; k += 1
        cv2.line(im, tuple((np.array(s['a']) * S).astype(int)), tuple((np.array(s['b']) * S).astype(int)), (255, 255, 0) if (on or 0) >= 0.5 else (0, 0, 255), 4, cv2.LINE_AA)
    if 'centre' in r:
        c = (np.array(r['centre']) * S).astype(int); cv2.putText(im, str(r['poly']), tuple(c), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 3)
cv2.imwrite(run + 'holes44_view.jpg', cv2.resize(im, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 85])
for name, (x0, y0, x1, y1) in dict(se=(4000, 3900, 9000, 6400), ne=(7600, 1300, 10000, 3200)).items():
    cv2.imwrite(run + f'holes44_crop_{name}.jpg', im[int(y0 * S):int(y1 * S), int(x0 * S):int(x1 * S)], [cv2.IMWRITE_JPEG_QUALITY, 85])
print('ok', names)
