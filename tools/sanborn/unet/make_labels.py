"""Training pair for the block / street U-net from a placed plate (14 November 2026).

    cd data/sanborn
    ../../tools/sanborn/unet/.venv/Scripts/python.exe ../../tools/sanborn/unet/make_labels.py N [TAG]

The image is the plate scan at half size (about 2.4 px per metre). The label comes free from the placement: today's
parcel blocks (today/blocks_N.geojson, guided/parcels.py) drawn onto the plate through the plate's model (TAG, default
'guided'). Classes: 0 street or other open ground, 1 block, 255 ignore. Each block side is first slid onto the printed block
line beside it (snap), so the label's edges are straight and lie on the ruled lines. A side is verified when the scan is
clearly darker along it than beside it; a side that is not (no printed line there, or the snap missed) is blanked
out in a band, so only verified edges are taught. Ignored: off the paper, those bands, and one pixel either side of
every label edge. The guide keeps the unsnapped (rough) blocks.
Also writes the guide (N_guide.png): today's blocks and centre lines through the same model, the U-net's extra input
(unet.py shifts and erases it at random in training, so the network must find the real edge in the picture).
Writes unet_data/N_img.jpg, N_label.png, N_guide.png, N_meta.json (not committed: remade from the scan and the parcels).
"""
import json, os, sys
import numpy as np
import cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, '..', 'guided'))
import streets as S  # noqa: E402
from scipy.interpolate import LinearNDInterpolator  # noqa: E402
from shapely.geometry import shape  # noqa: E402
J = S.J
N = sys.argv[1]; TAG = sys.argv[2] if len(sys.argv) > 2 else 'guided'; K, IGN, SNAP, TURN, MINSIDE, UNSURE = 2, 1, 18, 8, 28, 8
SP = S.SP; OUT = SP + 'unet_data/'; os.makedirs(OUT, exist_ok=True)
full = cv2.imread(SP + f'cufp/22-{N}.jpg'); H, W = full.shape[:2]
img = cv2.resize(full, (W // K, H // K), interpolation=cv2.INTER_AREA); h, w = img.shape[:2]
gx, gy = np.meshgrid(np.linspace(-300, W + 300, 120), np.linspace(-300, H + 300, 90)); P = np.c_[gx.ravel(), gy.ravel()]
inv = LinearNDInterpolator(J.world_many(f'22-{N}', P, TAG), P)
lab = np.zeros((h, w), np.uint8); cl = np.zeros((h, w), np.uint8); rough = np.zeros((h, w), np.uint8)
grayF = cv2.GaussianBlur(cv2.cvtColor(full, cv2.COLOR_BGR2GRAY), (3, 3), 0).astype(np.float32)      # the snap works on the full-size scan
def dark(a, b):
    d = b - a; L = np.hypot(*d); t = np.linspace(0.06, 0.94, max(10, int(L)))
    q = a + np.outer(t, d); x = q[:, 0].round().astype(int); y = q[:, 1].round().astype(int)
    ok = (x >= 0) & (x < W) & (y >= 0) & (y < H)
    return float(grayF[y[ok], x[ok]].mean()) if ok.sum() > 8 else 255.0
def snap(poly):
    """Ben, 14 November 2026: teach it how a street looks. A block side is a straight ruled line. Each side of today's
    block (full-size px) is first slid sideways (up to SNAP px, about 3.5 m) to the darkest line beside it, then its two
    ends are moved separately (TURN px each) so the side can turn onto the printed line: the placed parcels are slightly
    rotated against the print, and a slide alone leaves the side crossing the line. Corners are rebuilt where
    neighbouring sides meet. Returns the polygon and how many sides were snapped."""
    v = cv2.approxPolyDP(poly.astype(np.float32).reshape(-1, 1, 2), 3.0, True)[:, 0, :].astype(float); n = len(v); moved = 0
    if n < 3: return poly, 0
    sides = []
    for k in range(n):
        a, b = v[k], v[(k + 1) % n]; L = np.hypot(*(b - a)); nrm = np.array([-(b - a)[1], (b - a)[0]]) / (L or 1); a2, b2 = a, b
        if L >= MINSIDE:
            ds = {o: dark(a + nrm * o, b + nrm * o) + 0.3 * abs(o) for o in range(-SNAP, SNAP + 1, 2)}; o1 = min(ds, key=ds.get)
            if ds[o1] < np.median(list(ds.values())) - 10:
                best = min(((dark(a + nrm * (o1 + i), b + nrm * (o1 + j)), i, j) for i in range(-TURN, TURN + 1) for j in range(-TURN, TURN + 1)))
                a2, b2 = a + nrm * (o1 + best[1]), b + nrm * (o1 + best[2]); moved += 1
        sides.append((a2, b2))
    out = []
    for k in range(n):
        (a1, b1), (a2, b2) = sides[k - 1], sides[k]; d1, d2 = b1 - a1, b2 - a2; den = d1[0] * d2[1] - d1[1] * d2[0]; x = None
        if abs(den) > 0.15 * np.hypot(*d1) * np.hypot(*d2):
            x = a1 + ((a2[0] - a1[0]) * d2[1] - (a2[1] - a1[1]) * d2[0]) / den * d1
            if np.hypot(*(x - a2)) > 2.5 * SNAP: x = None
        out.append(x if x is not None else (b1 + a2) / 2)
    return np.array(out), moved
def on_line(a, b):
    """is the side on a printed line: at least 25 grey darker than the paper 3 to 6 px either side of it"""
    d = b - a; L = np.hypot(*d)
    if L < MINSIDE: return False
    nrm = np.array([-d[1], d[0]]) / L
    return np.mean([dark(a + nrm * o, b + nrm * o) for o in (-6, -3, 3, 6)]) - dark(a, b) > 25
snapped = []; unsure = np.zeros((h, w), np.uint8); nver = 0
nside = nmoved = 0
for f in json.load(open(SP + f'today/blocks_{N}.geojson', encoding='utf8'))['features']:
    q = inv(np.asarray(shape(f['geometry']).exterior.segmentize(3).coords)[:, :2])
    q = q[~np.isnan(q[:, 0])]
    if len(q) < 3: continue
    cv2.fillPoly(rough, [(q / K).astype(np.int32)], 1)
    q2, m = snap(q); nmoved += m; nside += len(q2); cv2.fillPoly(lab, [(q2 / K).round().astype(np.int32)], 1); snapped.append(q2.round(1).tolist())
    for k in range(len(q2)):                    # a side with no printed line under it is not taught as an edge: blank a band along it
        a_, b_ = q2[k], q2[(k + 1) % len(q2)]
        if on_line(a_, b_): nver += 1
        else: cv2.line(unsure, tuple((a_ / K).round().astype(int)), tuple((b_ / K).round().astype(int)), 1, 2 * UNSURE + 1)
for s_ in S.Plate(N).streets():                    # today's centre lines, for the guide input
    for l in getattr(s_['geom'], 'geoms', [s_['geom']]):
        q = inv(np.asarray(l.segmentize(3).coords)[:, :2]) / K; q = q[~np.isnan(q[:, 0])]
        if len(q) >= 2: cv2.polylines(cl, [q.astype(np.int32)], False, 255, 3)
json.dump(snapped, open(OUT + f'{N}_snapped.json', 'w', encoding='utf8', newline=chr(10)))      # block polygons on the printed lines, full-size px
cv2.imwrite(OUT + f'{N}_guide.png', np.dstack([rough * 255, cl, np.zeros_like(cl)]))   # channel 0: today's blocks, 1: today's centre lines
edge = cv2.morphologyEx(lab, cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)) > 0
band = cv2.dilate(edge.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * IGN + 1, 2 * IGN + 1))) > 0
alpha = cv2.resize(np.load(SP + f'cufp/{N}/png_alpha_s4.npy').astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR) > 0.5
out = lab.copy(); out[band] = 255; out[unsure > 0] = 255; out[~alpha] = 255
cv2.imwrite(OUT + f'{N}_img.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 92]); cv2.imwrite(OUT + f'{N}_label.png', out)
json.dump(dict(plate=N, tag=TAG, scale=K, ignore_px=IGN, sides=nside, sides_snapped=nmoved, sides_on_printed_line=nver, size=[w, h], block=float((out == 1).mean()), street=float((out == 0).mean()), ignore=float((out == 255).mean())),
          open(OUT + f'{N}_meta.json', 'w', encoding='utf8', newline='\n'), indent=1)
full_vis = full.copy()                       # full-size check: snapped block sides (green) on the scan
for q in snapped:
    q = np.array(q)
    for k in range(len(q)): cv2.line(full_vis, tuple(q[k].round().astype(int)), tuple(q[(k + 1) % len(q)].round().astype(int)), (0, 170, 0) if on_line(q[k], q[(k + 1) % len(q)]) else (0, 0, 230), 1, cv2.LINE_AA)   # green: on a printed line; red: not verified
cv2.imwrite(OUT + f'{N}_snapcheck.jpg', full_vis, [cv2.IMWRITE_JPEG_QUALITY, 88])
vis = img.copy(); vis[out == 1] = (vis[out == 1] * 0.6 + np.array([0, 120, 0]) * 0.4).astype(np.uint8); vis[out == 0] = (vis[out == 0] * 0.6 + np.array([200, 60, 0]) * 0.4).astype(np.uint8)
cv2.imwrite(OUT + f'{N}_check.jpg', cv2.resize(vis, None, fx=0.5, fy=0.5), [cv2.IMWRITE_JPEG_QUALITY, 80])
print(json.load(open(OUT + f'{N}_meta.json')))
