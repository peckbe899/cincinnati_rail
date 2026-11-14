"""Blocks and streets of a plate from the U-net's prediction (14 November 2026).

    cd data/sanborn
    ../../tools/sanborn/unet/.venv/Scripts/python.exe ../../tools/sanborn/unet/extract.py N NAME

unet_data/N_pred_NAME.png (P(block), half size) -> on the paper: block where P > 0.5 (specks dropped), street elsewhere.
Ben, 14 November 2026: a street is never wavy. The mask outline is only a first guess. Each block outline is cut into
sides; a straight line is fitted to every side, then moved sideways (up to SNAP px) onto the darkest ruled line of the
scan next to it, the printed block line. Corners are where neighbouring sides' lines meet. A side is kept as a curve
only where a straight line misses the outline by more than CURVE px, and then it is smoothed.
Writes, in plate pixels:
  picks22_guided/22-N/unet_blocks.json   block polygons (straight sides)
  picks22_guided/22-N/unet_obs.json      "edges": points every STEP px along the straight sides;
                                         "centres": points every STEP px along the middle of the street area
  unet_data/N_extract_NAME.jpg           the picture for checking
"""
import json, os, sys
import numpy as np
import cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, '..'))
import _ws  # noqa: E402
N, NAME = sys.argv[1], sys.argv[2]; SP = _ws.DATA
K, STEP, MIN_PX, TOL, MINLEN, CURVE, SNAP = 2, 60, 1500, 6.0, 45.0, 4.0, 10
p = cv2.imread(SP + f'unet_data/{N}_pred_{NAME}.png', 0); h, w = p.shape
img = cv2.imread(SP + f'unet_data/{N}_img.jpg'); gray = cv2.GaussianBlur(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), (3, 3), 0).astype(np.float32)
alpha = cv2.resize(np.load(SP + f'cufp/{N}/png_alpha_s4.npy').astype(np.float32), (w, h)) > 0.5
alpha = cv2.erode(alpha.astype(np.uint8), np.ones((9, 9), np.uint8)) > 0
blk = ((p > 127) & alpha).astype(np.uint8)
blk = cv2.morphologyEx(blk, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
n, lab, st, _ = cv2.connectedComponentsWithStats(blk, connectivity=4)
for i in range(1, n):
    if st[i, cv2.CC_STAT_AREA] < MIN_PX: blk[lab == i] = 0
n, lab, st, _ = cv2.connectedComponentsWithStats((alpha & (blk == 0)).astype(np.uint8), connectivity=4)      # specks of "street" inside a block
for i in range(1, n):
    if st[i, cv2.CC_STAT_AREA] < MIN_PX: blk[lab == i] = 1
inner = cv2.erode(alpha.astype(np.uint8), np.ones((25, 25), np.uint8)) > 0         # an outline along the paper's edge is not a block edge

def darkness(a, b, off):
    """mean grey along the segment a-b moved sideways by off px (lower = darker)"""
    d = b - a; L = np.hypot(*d); nrm = np.array([-d[1], d[0]]) / L; t = np.linspace(0.1, 0.9, max(8, int(L * 0.8)))
    q = a + np.outer(t, d) + nrm * off; x = np.clip(q[:, 0].round().astype(int), 0, w - 1); y = np.clip(q[:, 1].round().astype(int), 0, h - 1)
    return float(gray[y, x].mean())

def straighten(c):
    """closed outline (n x 2, half-size px) -> (vertices, sides): sides = [(a, b, straight?)]"""
    c = c.astype(np.float32); ap = cv2.approxPolyDP(c.reshape(-1, 1, 2), TOL, True)[:, 0, :]
    if len(ap) < 3: return None, []
    idx = [int(np.argmin(np.hypot(*(c - v).T))) for v in ap]; lines = []
    for k in range(len(idx)):
        i, j = idx[k], idx[(k + 1) % len(idx)]; seg = c[i:j + 1] if j > i else np.r_[c[i:], c[:j + 1]]
        a, b = seg[0], seg[-1]; L = float(np.hypot(*(b - a)))
        if L < MINLEN or len(seg) < 5: lines.append(dict(kind='short', a=a, b=b, seg=seg)); continue
        vx, vy, x0, y0 = cv2.fitLine(seg, cv2.DIST_L2, 0, 0.01, 0.01)[:, 0]; dv = np.array([vx, vy]); p0 = np.array([x0, y0])
        dev = np.abs((seg - p0) @ np.array([-vy, vx]))
        if dev.max() > CURVE and L > 60: lines.append(dict(kind='curve', a=a, b=b, seg=seg)); continue
        a2, b2 = p0 + dv * ((a - p0) @ dv), p0 + dv * ((b - p0) @ dv)
        if inner[int(np.clip((a2[1] + b2[1]) / 2, 0, h - 1)), int(np.clip((a2[0] + b2[0]) / 2, 0, w - 1))]:      # snap to the printed line
            ds = {o: darkness(a2, b2, o) for o in range(-SNAP, SNAP + 1)}; o = min(ds, key=ds.get)
            if ds[o] < np.median(list(ds.values())) - 8:
                nrm = np.array([-(b2 - a2)[1], (b2 - a2)[0]]) / np.hypot(*(b2 - a2)); a2, b2 = a2 + nrm * o, b2 + nrm * o
        lines.append(dict(kind='line', a=a2, b=b2, seg=seg))
    # a short side between two straight sides is the mask's rounded corner: drop it, the two lines meet at the corner
    if sum(l['kind'] == 'line' for l in lines) >= 3: lines = [l for l in lines if l['kind'] != 'short']
    verts = []
    for k, l in enumerate(lines):                   # corner = where this side's line meets the previous side's line
        pr = lines[k - 1]
        if l['kind'] == 'line' and pr['kind'] == 'line':
            d1, d2 = pr['b'] - pr['a'], l['b'] - l['a']; den = d1[0] * d2[1] - d1[1] * d2[0]
            if abs(den) > 0.2 * np.hypot(*d1) * np.hypot(*d2):
                t = ((l['a'][0] - pr['a'][0]) * d2[1] - (l['a'][1] - pr['a'][1]) * d2[0]) / den; x = pr['a'] + t * d1
                if np.hypot(*(x - l['a'])) < 60: pr['b'] = x; l['a'] = x
    for l in lines:
        if l['kind'] == 'curve':
            s = cv2.GaussianBlur(l['seg'].reshape(-1, 1, 2), (1, 31), 0)[:, 0, :] if len(l['seg']) > 31 else l['seg']
            verts += s[::8].tolist()
        else: verts.append(l['a'].tolist())
    return verts, [(l['a'], l['b']) for l in lines if l['kind'] == 'line']

cs, _ = cv2.findContours(blk, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
blocks, edges, clean, nline = [], [], np.zeros((h, w), np.uint8), 0
for c in cs:
    verts, sides = straighten(c[:, 0, :])
    if not verts or len(verts) < 3: continue
    v = np.array(verts); blocks.append((v * K).round(1).tolist()); cv2.fillPoly(clean, [v.round().astype(np.int32)], 1); nline += len(sides)
    for a, b in sides:
        L = np.hypot(*(b - a))
        for t in np.arange(STEP / K / 2, L, STEP / K):
            q = a + (b - a) * t / L
            if 0 <= q[0] < w and 0 <= q[1] < h and inner[int(q[1]), int(q[0])]: edges.append([round(float(q[0] * K), 1), round(float(q[1] * K), 1)])
sk = cv2.ximgproc.thinning((alpha & (clean == 0)).astype(np.uint8) * 255)
ys, xs = np.where((sk > 0) & inner); keep = {}
for x, y in zip(xs, ys): keep.setdefault((x // (STEP // K), y // (STEP // K)), [int(x * K), int(y * K)])
centres = list(keep.values())
D = SP + f'picks22_guided/22-{N}/'
json.dump(blocks, open(D + 'unet_blocks.json', 'w', encoding='utf8', newline='\n'))
json.dump(dict(model=NAME, edges=edges, centres=centres), open(D + 'unet_obs.json', 'w', encoding='utf8', newline='\n'))
vis = (img * 0.7 + 76).astype(np.uint8)
for b in blocks: cv2.polylines(vis, [(np.array(b) / K).round().astype(np.int32)], True, (0, 120, 0), 2, cv2.LINE_AA)
vis[sk > 0] = (220, 40, 0)
cv2.imwrite(SP + f'unet_data/{N}_extract_{NAME}.jpg', cv2.resize(vis, None, fx=0.6, fy=0.6, interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 82])
print('blocks', len(blocks), 'straight sides', nline, 'edge points', len(edges), 'centre points', len(centres))
