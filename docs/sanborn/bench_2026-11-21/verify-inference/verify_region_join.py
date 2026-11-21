"""verify-inference: on a batch plate, which batch block regions does the atta8 area map join into its largest region,
and where is the joint? (half-size rasters, P(block) > 0.5 inside the paper; 4-connected components)

    python verify_region_join.py N

Writes pics/N_join_crop{i}.jpg (full-size crops around each joint: red tint = block only in batch, cyan = only in
atta8, green = block in both) and prints the regions.
"""
import os, sys
import numpy as np, cv2
V = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-21/verify-inference/'
INF = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-21/inference/'
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
n = sys.argv[1]
full = cv2.imread(SP + f'cufp/22-{n}.jpg'); H, W = full.shape[:2]; h2, w2 = H // 2, W // 2
ground = cv2.resize(np.load(SP + f'cufp/{n}/png_alpha_s4.npy').astype(np.uint8), (w2, h2), interpolation=cv2.INTER_NEAREST) > 0
mask = SP + f'bench_2026-11-21/visual-pdf/maparea_check/{n}_mask8.png'
if os.path.exists(SP + f'cufp/{n}/source.json') and os.path.exists(mask): ground &= cv2.resize(cv2.imread(mask, 0), (w2, h2), interpolation=cv2.INTER_NEAREST) > 127
b = (cv2.imread(SP + f'unet_data/{n}_pred_area_ng1.png', 0) > 127) & ground
t = (cv2.imread(INF + f'maps_plates/atta8/{n}_area.png', 0) > 127) & ground
nb, lb = cv2.connectedComponents(b.astype(np.uint8), connectivity=4); nt, lt = cv2.connectedComponents(t.astype(np.uint8), connectivity=4)
g = ground.sum()
at = np.bincount(lt.ravel(), minlength=nt); at[0] = 0; big = int(np.argmax(at)); ab = np.bincount(lb.ravel(), minlength=nb); ab[0] = 0
print(n, 'largest atta8 region', f'{at[big] / g:.3f} of the ground;', 'largest batch region', f'{ab.max() / g:.3f}')
inside = lb[(lt == big) & b]; c = np.bincount(inside, minlength=nb); c[0] = 0
parts = [(int(k), int(c[k]), round(float(c[k] / g), 3)) for k in np.argsort(-c) if c[k] > 0.005 * g]
print('batch regions inside it (label, px, share of ground):', parts)
# joints: atta8-only block pixels of the big region that touch two or more of those batch regions within 15 px
P = [p[0] for p in parts]
os.makedirs(V + 'pics', exist_ok=True); i = 0
new = (lt == big) & ~b
near = {k: cv2.dilate((lb == k).astype(np.uint8), np.ones((31, 31), np.uint8)) > 0 for k in P}
cnt = sum(near[k].astype(np.uint8) for k in P)
joint = new & (cnt >= 2)
nj, lj, st, cen = cv2.connectedComponentsWithStats(joint.astype(np.uint8))
order = np.argsort(-st[1:, cv2.CC_STAT_AREA]) + 1 if nj > 1 else []
for j in list(order)[:3]:
    cx, cy = cen[j]; X, Y = int(cx * 2), int(cy * 2); x0, y0 = max(0, X - 900), max(0, Y - 600); x1, y1 = min(W, x0 + 1800), min(H, y0 + 1200)
    v = full[y0:y1, x0:x1].astype(np.float32) * 0.8 + 50
    B = cv2.resize(b.astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST)[y0:y1, x0:x1] > 0; T = cv2.resize(t.astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST)[y0:y1, x0:x1] > 0
    for m, col in ((B & ~T, (60, 60, 255)), (T & ~B, (255, 220, 0)), (B & T, (60, 200, 60))):
        v[m] = v[m] * 0.6 + np.array(col, np.float32) * 0.4
    v = cv2.resize(v.clip(0, 255).astype(np.uint8), None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)
    cv2.imwrite(V + f'pics/{n}_join_crop{i}.jpg', v, [cv2.IMWRITE_JPEG_QUALITY, 90]); print('joint', i, 'at full px', (X, Y), 'size', int(st[j, cv2.CC_STAT_AREA]), 'half px'); i += 1
