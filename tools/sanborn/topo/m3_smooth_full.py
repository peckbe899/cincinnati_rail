"""Map 3 base over the whole LiDAR extent (same method as m3_smooth.py): LiDAR + real-only rebuild, building and street
imprint removed, computed at 4 m (its smallest relief is about 15-20 m across) and resampled to 2 m.
Tiles of 2000 px (2 m) with 300 px overlap, two workers (argv: worker index, count).
Output m3/full_base_dm.npy (int16 dm, 17500 x 20000)."""
import numpy as np, json, rasterio, os, sys, cv2
from scipy import ndimage as ndi
from skimage.morphology import area_opening, area_closing, disk
DM = json.load(open('dem2m.json')); H, W = DM['h'], DM['w']
D = np.load('dem2m.npy', mmap_mode='r'); RO = rasterio.open('map3_realonly_delta_dm.tif')
out = np.load('m3/full_base_dm.npy', mmap_mode='r+')
WK, NW = int(sys.argv[1]), int(sys.argv[2])
done = set(open(f'm3/full_done_{WK}.txt').read().split()) if os.path.exists(f'm3/full_done_{WK}.txt') else set()
T, O = 2000, 300
def proc(G2):
    h, w = G2.shape
    G = cv2.resize(G2.astype(np.float32), ((w + 1) // 2, (h + 1) // 2), interpolation=cv2.INTER_AREA).astype(np.float64)   # 4 m
    Tr = ndi.gaussian_filter(G, 20); Rs = G - Tr
    gy, gx = np.gradient(ndi.gaussian_filter(G, 4), 4); sl = np.hypot(gx, gy)
    wf = np.clip((0.12 - sl) / 0.06, 0, 1)
    Rs = wf * ndi.grey_closing(Rs, footprint=disk(3)) + (1 - wf) * Rs
    zi = np.round(Rs * 100).astype(np.int32)
    D1 = Tr + area_closing(area_opening(zi, 3000), 3000) / 100.0
    R = ndi.gaussian_filter(ndi.median_filter(D1, size=5), 0.75)
    w2 = np.clip((0.06 - sl) / 0.03, 0, 1)
    R = w2 * ndi.gaussian_filter(R, 2) + (1 - w2) * R
    return cv2.resize(R.astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR).astype(np.float64)
for i in range(0, H, T):
    for j in range(0, W, T):
        key = f'{i}_{j}'
        if key in done or ((i // T) * 10 + j // T) % NW != WK: continue
        a0, a1, b0, b1 = max(0, i - O), min(H, i + T + O), max(0, j - O), min(W, j + T + O)
        raw = np.asarray(D[a0:a1, b0:b1]); nod = raw < -30000
        G = raw.astype(np.float64) / 10 + RO.read(1, window=rasterio.windows.Window(b0, a0, b1 - b0, a1 - a0)).astype(np.float64) / 10
        if nod.all(): out[i:min(H, i + T), j:min(W, j + T)] = -32768; continue
        if nod.any(): G[nod] = np.median(G[~nod])
        R = proc(G); R = np.where(nod, -3276.8, R)
        out[i:min(H, i + T), j:min(W, j + T)] = np.round(R[i - a0:i - a0 + min(T, H - i), j - b0:j - b0 + min(T, W - j)] * 10).astype(np.int16)
        out.flush(); open(f'm3/full_done_{WK}.txt', 'a').write(key + '\n'); print(key, flush=True)
print('ALL DONE', flush=True)
