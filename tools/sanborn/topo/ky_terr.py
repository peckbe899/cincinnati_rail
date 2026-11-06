"""Kentucky riverworks for map 3: terraces and levees to 70 ft (151.8 m) along the canon outline (no push into the river).
Segments: 1 Bromley-Ludlow riprap levee, 2 Covington 3 tiers, 3 Newport 2 tiers, 4 Bellevue-Dayton 2 tiers (narrow),
5 Licking banks wall + levee to the Threemile Creek line, 6 tiebacks at that line. Works only where land behind the bank is
below 151.8 m (1912 ground) and connected to the river. Writes map3_ky_terraces_{target_dm,mode,delta_dm}.tif."""
import numpy as np, json, rasterio, cv2
from scipy import ndimage as ndi
from affine import Affine
from pyproj import Transformer
WALL, QBAS, MID, SLOPE = 151.8, 142.0, 147.0, 0.035
d = np.load('rw_setup.npz'); x0 = float(d['x0']); y1 = float(d['y1']); H, W = d['L'].shape; C = d['C']; LV = d['LV']
CL = np.load('rw_CL.npy'); KY = np.load('rw_KY.npy'); fl = np.load('ky_flood.npy')
G3 = np.load('map3_window_ground.npy')
g12 = np.load('ky1912_ground.npy'); g12 = np.where(np.isfinite(g12), g12, d['L'])
T = Transformer.from_crs('EPSG:4326', 'EPSG:26916', always_xy=True)
col = lambda lon: int((T.transform(lon, 39.09)[0] - x0) / 2)
eM, nM = T.transform(-84.4941, 39.0506); rM = int((y1 - nM) / 2); cM = int((eM - x0) / 2)
cBW, cLC, cNB, cDE = col(-84.572), col(-84.537), col(-84.481), col(-84.451)
r0, r1 = 1000, rM + 120                        # crop: Kentucky frontage down to the Threemile line
sl = (slice(r0, r1), slice(0, W)); h = r1 - r0
Wt = (C | CL)[sl]; ky = KY[sl] & ~Wt; F = fl[sl]; lv = LV[sl]; b3 = G3[sl].copy(); g = g12[sl]
# real floodwalls and riverside fills (Z_all) within 400 m of the Kentucky bank give way to the 1912 ground, except canon interstates
DM = json.load(open('dem2m.json')); R0 = int((DM['y1'] - y1) / 2); C0 = int((x0 - DM['x0']) / 2)
with rasterio.open('map3_canon_interstates_delta_dm.tif') as ds: dl = ds.read(1, window=rasterio.windows.Window(C0, R0 + r0, W, r1 - r0))
Za = np.load('rw_Zall.npy')[sl] & ky
rem = Za & (ndi.distance_transform_edt(~Wt) * 2 < 400) & (g < b3 - 1.0) & (dl == 0)
rem = ndi.binary_dilation(rem, iterations=2) & Za & (g < b3) & (dl == 0)
print('real riverside works removed: %.3f km2, mean lowering %.1f m' % (rem.sum() * 4e-6, (b3 - g)[rem].mean()))
b3[rem] = g[rem]
# Dayton marina basin (real-only, open water behind the new wall): filled to the ground around it, on a small crop
eD, nD = T.transform(-84.458, 39.117); rD = int((y1 - nD) / 2) - r0; cD = int((eD - x0) / 2)
ms = (slice(max(0, rD - 500), rD + 400), slice(cD - 700, cD + 700))
Lw = d['L'][r0:r1][ms]; kyw = ky[ms]; bw = b3[ms]
gy_m, gx_m = np.gradient(ndi.gaussian_filter(Lw, 1), 2)
wb = (np.hypot(gy_m, gx_m) < 0.01) & (Lw < 141.5) & kyw
lab_m, _ = ndi.label(wb); sz_m = np.bincount(lab_m.ravel()); sz_m[0] = 0
mar_w = ndi.binary_dilation(np.isin(lab_m, np.nonzero(sz_m * 4 > 20000)[0]), iterations=2) & kyw
ring = ndi.binary_dilation(mar_w, iterations=15) & ~ndi.binary_dilation(mar_w, iterations=5) & kyw
from rw_maps_util import pushpull
hole = ndi.binary_dilation(mar_w, iterations=5) & ~ring | ~kyw
fill_w = pushpull(np.where(hole, 0, bw).astype(np.float32), hole)
marina = np.zeros((h, W), bool); marina[ms] = mar_w
fillv = np.zeros((h, W), np.float32); fillv[ms] = fill_w
b3[marina] = fillv[marina]
print('marina filled: %.3f km2 to %.1f m (ground around it, median %.1f m)' % (marina.sum() * 4e-6, fillv[marina].mean(), np.median(bw[ring])))
rem = rem | marina; g = g.copy(); g[marina] = fillv[marina]
cc = np.broadcast_to(np.arange(W), (h, W)); rr = np.broadcast_to(np.arange(r0, r1)[:, None], (h, W))
ext = ky & (cc >= cBW) & (cc < cDE) & ~((rr > rM) & ~ndi.binary_dilation(CL[sl], iterations=400))
ext &= ~(rr > rM)
nearO = ndi.binary_dilation(C[sl], iterations=2); nearL = ndi.binary_dilation(CL[sl], iterations=2)
bank = ext & (nearO | nearL)
dF = ndi.distance_transform_edt(~(F & ky)) * 2
need = bank & (dF < 60)
need = ndi.binary_closing(need, iterations=50) & bank           # bridge gaps up to about 200 m along the bank
lr, lc = np.nonzero(CL); top = lr < lr.min() + 60; cLM = int(lc[top].mean()); print('Licking mouth col', cLM)
seg = np.zeros((h, W), np.uint8)
seg[need & nearO & (cc < cLC)] = 1
seg[need & nearO & (cc >= cLC) & (cc < cLM)] = 2              # west of the Licking mouth
seg[need & nearO & (cc >= cLM) & (cc < cNB)] = 3
seg[need & nearO & (cc >= cNB)] = 4
seg[need & nearL & ~nearO] = 5
# Covington/Newport split at the Licking: Ohio-bank pixels west of the Licking channel belong to Covington
lic_c = np.nonzero(CL[sl][:400 if h > 400 else h].any(0))[0]
dN, (ir, ic) = ndi.distance_transform_edt(seg == 0, return_indices=True); dN = dN * 2
dW = ndi.distance_transform_edt(~Wt) * 2
S = seg[ir, ic]; zone = ext & (dN < 300) & (dN <= dW + 6) & (S > 0)
z = np.full((h, W), np.nan, np.float32); m = np.zeros((h, W), np.uint8)
def put(mask, val, mode):
    z[mask] = val[mask] if np.ndim(val) else val; m[mask] = mode
back = lambda d0: WALL - SLOPE * (dN - d0)
for s, tiers, top, bs in ((2, [(15, QBAS), (30, MID)], 45, SLOPE), (3, [(20, QBAS)], 35, 1 / 3), (4, [(10, QBAS)], 20, 1 / 3)):
    k = zone & (S == s); lo = 0
    for dd, val in tiers:
        put(k & (dN >= lo) & (dN < dd), val, 1); lo = dd
    put(k & (dN >= lo) & (dN < top), WALL, 2); put(k & (dN >= top), WALL - bs * (dN - top), 2)
k = zone & (S == 1); dr = 2 * (WALL - lv)
put(k & (dN < dr), lv + dN / 2, 2); put(k & (dN >= dr) & (dN < dr + 8), WALL, 2); put(k & (dN >= dr + 8), WALL - (dN - dr - 8) / 3, 2)
k = zone & (S == 5)
put(k & (dN < 8), WALL, 2); put(k & (dN >= 8), WALL - (dN - 8) / 3, 2)
# tiebacks on the Threemile line: from each Licking bank outward until 1912 ground reaches 151.8 m
rl = rM - r0; tb = np.zeros((h, W), bool)
row = Wt[rl]; wcols = np.nonzero(CL[sl][rl])[0]
for c0_, step in ((wcols.min() - 1, -1), (wcols.max() + 1, 1)):
    c_ = c0_
    while 0 <= c_ < W and g[rl, c_] < WALL and abs(c_ - c0_) < 600: tb[rl, c_] = True; c_ += step
gy_, gx_ = np.gradient(ndi.gaussian_filter(dW, 8))
for cend, pick in ((cBW, 'first'), (cDE - 1, 'first')):
    rs = np.nonzero(bank[:, cend] & need[:, cend])[0] if (bank[:, cend] & need[:, cend]).any() else np.nonzero(bank[:, cend])[0]
    if not len(rs): continue
    pr_, pc_ = float(rs[0]), float(cend); n_ = 0
    while n_ < 600:
        i_, j_ = int(round(pr_)), int(round(pc_))
        if not (0 <= i_ < h and 0 <= j_ < W) or g[i_, j_] >= WALL or Wt[i_, j_] and n_ > 5: break
        tb[i_, j_] = True; vy, vx = gy_[i_, j_], gx_[i_, j_]; nv = np.hypot(vy, vx) + 1e-9
        pr_ += vy / nv; pc_ += vx / nv; n_ += 1
    print('end tieback at col', cend, 'length m', n_ * 2)
dT = ndi.distance_transform_edt(~tb) * 2
k = ky & (dT < 60) & ~Wt
zt = np.where(dT < 3, WALL, WALL - (dT - 3) / 3)
kk = k & (np.isnan(z) | (zt > np.nan_to_num(z, nan=-1e9))) & (zt > g)
z[kk] = zt[kk]; m[kk] = 2; seg_tb = kk
# keep only where it changes the map 3 ground
# removed real works: force to the 1912 ground, or to the new fill where that is higher
lowr = rem & (m != 1); z[lowr] = np.where(m[lowr] == 2, np.fmax(g[lowr], z[lowr]), g[lowr]); m[lowr] = 1
b3o = G3[sl]
eff = (m == 1) | ((m == 2) & (z > b3 + 0.05))
z[~eff] = np.nan; m[~eff] = 0
newg = np.where(m == 1, z, np.where(m == 2, np.fmax(b3, np.nan_to_num(z, nan=-1e9)), b3))
# mode 2 pixels inside removed works must also force (base there is now the 1912 ground)
f2 = rem & (m == 2); z[f2] = newg[f2]; m[f2] = 1
dz = newg - b3o
names = {1: 'Bromley-Ludlow riprap', 2: 'Covington 3 tiers', 3: 'Newport 2 tiers', 4: 'Bellevue-Dayton 2 tiers', 5: 'Licking banks'}
stats = {}
for s, nm in names.items():
    kk2 = (m > 0) & (S == s) & zone
    blen = (seg == s).sum() * 2 / 2  # bank px on a 2-px-wide band -> approx metres
    stats[nm] = dict(area_km2=round(kk2.sum() * 4e-6, 3),
                     fill_m3=int(np.clip(dz[kk2], 0, None).sum() * 4), cut_m3=int(np.clip(-dz[kk2], 0, None).sum() * 4))
stats['real works removed'] = dict(area_km2=round(rem.sum() * 4e-6, 3))
stats['total changed km2'] = round((m > 0).sum() * 4e-6, 3)
stats['tiebacks'] = dict(area_km2=round(seg_tb.sum() * 4e-6, 3), length_m=int(tb.sum() * 2))
print(json.dumps(stats, indent=1))
Z = np.full((H, W), np.nan, np.float32); M = np.zeros((H, W), np.uint8); D = np.zeros((H, W), np.float32)
Z[sl] = z; M[sl] = m; D[sl] = dz
np.savez_compressed('ky_terr_out.npz', Z=Z, M=M, seg=np.pad(S * zone, ((r0, H - r1), (0, 0))).astype(np.uint8))
prof = dict(driver='GTiff', height=H, width=W, count=1, crs='EPSG:26916', transform=Affine(2, 0, x0, 0, -2, y1), compress='deflate', predictor=2, tiled=True)
with rasterio.open('map3_ky_terraces_target_dm.tif', 'w', dtype='int16', nodata=-32768, **prof) as ds: ds.write(np.where(M > 0, np.round(Z * 10), -32768).astype(np.int16), 1)
with rasterio.open('map3_ky_terraces_mode.tif', 'w', dtype='uint8', nodata=0, **{k: v for k, v in prof.items() if k != 'predictor'}) as ds: ds.write(M, 1)
with rasterio.open('map3_ky_terraces_delta_dm.tif', 'w', dtype='int16', nodata=0, **prof) as ds: ds.write(np.round(D * 10).astype(np.int16), 1)
json.dump(dict(wall_m=WALL, quai_bas_m=QBAS, covington_mid_m=MID, back_slope=SLOPE, segments=names,
               profiles={'Covington': '142.0 m 0-15 m from the water, 147.0 m 15-30, 151.8 m 30-45, then 3.5% down',
                         'Newport': '142.0 m 0-20, 151.8 m 20-35, then 1:3 down', 'Bellevue-Dayton': '142.0 m 0-10, 151.8 m 10-20, then 1:3 down',
                         'Bromley-Ludlow': 'riprap 1:2 from the water to 151.8 m, 8 m crest, 1:3 back', 'Licking': 'wall to 151.8 m, 8 m crest, 1:3 back',
                         'Tiebacks': 'Threemile Creek line (both banks), Bromley west end, Dayton east end: 6 m crest, 1:3 sides, to 1912 ground at 151.8 m'},
               cut_lines_lon=dict(bromley_west=-84.572, ludlow_covington=-84.537, newport_bellevue=-84.481, dayton_east=-84.451),
               threemile_mouth=[-84.4941, 39.0506], stats=stats), open('ky_terr_params.json', 'w'), indent=1)
