"""Map 3: take the building and street imprint out of the LiDAR so developed ground reads as terrain.
1) split the ground into an 80 m trend and the residual;
2) area opening + closing (4.8 ha) on the residual: pads, blocks and hillside terraces smaller than a city block
   flatten onto the trend, whatever their shape, while landforms and long ravines (large connected areas) stay;
   On gentle ground a 24 m closing fills the street network first (it is one connected low, so step 2 alone keeps it).
3) 18 m median, then 3 m Gaussian; 8 m more on flat ground. Tiled with overlap. Input: LiDAR + real-only rebuild over the riverworks
   window, computed with a 1.2 km margin and feathered into the real LiDAR over the window's outer 300 m.
   Output: m3/map3_smooth_base.npy."""
import numpy as np, json, rasterio
from scipy import ndimage as ndi
from skimage.morphology import area_opening, area_closing, disk
d = np.load('rw_setup.npz'); L = d['L']; x0 = float(d['x0']); y1 = float(d['y1']); H, W = L.shape
DM = json.load(open('dem2m.json')); r0 = int((DM['y1'] - y1) / 2); c0 = int((x0 - DM['x0']) / 2)
# work on the window plus a 1.2 km margin of real LiDAR, so nothing at the window edge is an edge effect
MG = 600; D = np.load('dem2m.npy', mmap_mode='r')
ra, ca = max(0, r0 - MG), max(0, c0 - MG); rb, cb = min(DM['h'], r0 + H + MG), min(DM['w'], c0 + W + MG)
with rasterio.open('map3_realonly_delta_dm.tif') as ds:
    G0 = np.asarray(D[ra:rb, ca:cb]).astype(np.float32) / 10 + ds.read(1, window=rasterio.windows.Window(ca, ra, cb - ca, rb - ra)).astype(np.float32) / 10
G0[G0 < -1000] = np.median(G0[G0 > -1000])
H0, W0 = H, W; H, W = G0.shape
OUT = np.zeros_like(G0); T, O = 1600, 300
for i in range(0, H, T):
    for j in range(0, W, T):
        a0, a1, b0, b1 = max(0, i - O), min(H, i + T + O), max(0, j - O), min(W, j + T + O)
        G = G0[a0:a1, b0:b1].astype(np.float64)
        Tr = ndi.gaussian_filter(G, 40); Rs = G - Tr
        gy, gx = np.gradient(ndi.gaussian_filter(G, 8), 2); sl = np.hypot(gx, gy)
        wf = np.clip((0.12 - sl) / 0.06, 0, 1)                       # gentle ground: streets are filled first
        Rs = wf * ndi.grey_closing(Rs, footprint=disk(6)) + (1 - wf) * Rs
        zi = np.round(Rs * 100).astype(np.int32)
        D1 = Tr + area_closing(area_opening(zi, 12000), 12000) / 100.0
        R = ndi.gaussian_filter(ndi.median_filter(D1, size=9), 1.5)
        w2 = np.clip((0.06 - sl) / 0.03, 0, 1)                       # flat basin: soften leftover sub-metre steps
        R = w2 * ndi.gaussian_filter(R, 4) + (1 - w2) * R
        OUT[i:min(H, i + T), j:min(W, j + T)] = R[i - a0:i - a0 + min(T, H - i), j - b0:j - b0 + min(T, W - j)]
        print(i, j, flush=True)
# cut back to the window and feather into the real LiDAR over the outer 300 m, so the edge matches it exactly
oy, ox = r0 - ra, c0 - ca
S = OUT[oy:oy + H0, ox:ox + W0]; G = G0[oy:oy + H0, ox:ox + W0]
yy = np.minimum(np.arange(H0), np.arange(H0)[::-1])[:, None]; xx = np.minimum(np.arange(W0), np.arange(W0)[::-1])[None, :]
w = np.clip(np.minimum(yy, xx) / 150.0, 0, 1); w = w * w * (3 - 2 * w)
B = w * S + (1 - w) * G
np.save('m3/map3_smooth_base.npy', B.astype(np.float32))
dz = B - G; print('change p1/p50/p99 %.1f/%.1f/%.1f m' % tuple(np.percentile(dz, [1, 50, 99])))
e = np.zeros((H0, W0), bool); e[:2] = e[-2:] = True; e[:, :2] = e[:, -2:] = True
print('edge |change| max %.3f m' % np.abs(dz[e]).max())
