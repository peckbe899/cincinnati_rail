try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# plate N build check: plate warped (light), earlier streets (grey; set names), new plate streets (blue), blocks (green outline), area (red)
import sys, json, numpy as np, cv2
from shapely.geometry import shape
SP = _ws.DATA
N = sys.argv[1]; res = float(sys.argv[2]) if len(sys.argv) > 2 else 1.6; box = [float(v) for v in sys.argv[3:7]] if len(sys.argv) > 6 else None
A = shape(json.load(open(SP + f'cufp/{N}/area.json'))); E0, N0, E1, N1 = box or [v + d for v, d in zip(A.bounds, (-120, -120, 120, 120))]
W, H = int((E1 - E0) / res), int((N1 - N0) / res)
g = dict(np.load(SP + f'cufp/{N}/model.npz')); im = cv2.imread(SP + f'cufp/{N}/png_s8.jpg')
ee, nn = np.meshgrid(E0 + (np.arange(W) + .5) * res, N1 - (np.arange(H) + .5) * res)
fx = ((ee - g['E0']) / g['step']).astype(np.float32); fy = ((g['N1'] - nn) / g['step']).astype(np.float32)
px = cv2.remap(g['px'], fx, fy, cv2.INTER_LINEAR, borderValue=-1e6) / 8; py = cv2.remap(g['py'], fx, fy, cv2.INTER_LINEAR, borderValue=-1e6) / 8
out = cv2.remap(im, px.astype(np.float32), py.astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255))
out = (out * 0.45 + 255 * 0.55).astype(np.uint8)
P = lambda c: np.array([(int((x - E0) / res), int((N1 - y) / res)) for x, y in c], np.int32)
B = json.load(open(SP + 'deckpage/basin.json'))
for f in B['features']:
    if f['properties']['layer'] == 'street' and f['properties'].get('set') != 'c' + N:
        cv2.polylines(out, [P(f['geometry']['coordinates'])], False, (90, 90, 90), 2, cv2.LINE_AA)
X = json.load(open(SP + f'cufp/{N}/ext.json'))
for f in X['features']:
    if f['properties']['layer'] == 'block': cv2.polylines(out, [P(f['geometry']['coordinates'][0])], True, (0, 150, 0), 1, cv2.LINE_AA)
for f in X['features']:
    if f['properties']['layer'] == 'street': cv2.polylines(out, [P(f['geometry']['coordinates'])], False, (220, 90, 0), 2, cv2.LINE_AA)
cv2.polylines(out, [P(q.exterior.coords) for q in getattr(A, 'geoms', [A])], True, (0, 0, 230), 1, cv2.LINE_AA)
cv2.imwrite(SP + f'cufp/{N}/build.jpg', out, [cv2.IMWRITE_JPEG_QUALITY, 82]); print(out.shape)
