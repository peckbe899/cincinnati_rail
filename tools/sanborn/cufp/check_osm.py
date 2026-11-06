try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# quick look: plate N warped to world at 1 m (from its png_s8 overview via the inverse grid) with OSM streets in red and controls
import sys, json, numpy as np, cv2
SP = _ws.DATA
N = sys.argv[1]; box = [float(v) for v in sys.argv[2:6]] if len(sys.argv) > 5 else None; res = float(sys.argv[6]) if len(sys.argv) > 6 else 1.0
g = dict(np.load(SP + f'cufp/{N}/model.npz')); im = cv2.imread(SP + f'cufp/{N}/png_s8.jpg')
if box is None:
    h, w = g['px'].shape; box = [g['E0'], g['N1'] - h * g['step'], g['E0'] + w * g['step'], g['N1']]
E0, N0, E1, N1 = box; W, H = int((E1 - E0) / res), int((N1 - N0) / res)
ee, nn = np.meshgrid(E0 + (np.arange(W) + .5) * res, N1 - (np.arange(H) + .5) * res)
fx = ((ee - g['E0']) / g['step']).astype(np.float32); fy = ((g['N1'] - nn) / g['step']).astype(np.float32)
px = cv2.remap(g['px'], fx, fy, cv2.INTER_LINEAR, borderValue=-1e6) / 8; py = cv2.remap(g['py'], fx, fy, cv2.INTER_LINEAR, borderValue=-1e6) / 8
out = cv2.remap(im, px.astype(np.float32), py.astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255))
out = (out * 0.75 + 255 * 0.25).astype(np.uint8)
def P(c): return [(int((x - E0) / res), int((N1 - y) / res)) for x, y in c]
for fn in ('lph/osm_east.geojson', 'lph/osm_north.geojson'):
    for f in json.load(open(SP + fn))['features']:
        if f['geometry']['type'] == 'LineString' and f['properties'].get('name'):
            cv2.polylines(out, [np.array(P(f['geometry']['coordinates']), np.int32)], False, (0, 0, 230), 1, cv2.LINE_AA)
for m in json.load(open(SP + f'cufp/{N}/matches.json')):
    if m.get('osm'):
        x, y = P([m['osm']])[0]; cv2.circle(out, (x, y), 5, (0, 160, 0) if m['used'] else (255, 0, 255), 2)
cv2.imwrite(SP + f'cufp/{N}/check.jpg', out, [cv2.IMWRITE_JPEG_QUALITY, 82]); print(out.shape)
