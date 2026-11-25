"""Size, stroke width and slant of the marks today's rule calls text (ink_bins bin 8), per plate.
Measured on unet_data/<plate>_bins.png. A component = 8-connected piece of bin-8 pixels.
Writes out/text_sizes_<plate>.json. Usage: python -B text_sizes.py 44 5"""
import os, sys, json, cv2, numpy as np
R = r'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D'
O = os.path.join(R, 'data/sanborn/bench_2026-11-25/text/research/out')
for plate in sys.argv[1:]:
    code = cv2.imread(os.path.join(R, f'data/sanborn/unet_data/{plate}_bins.png'), cv2.IMREAD_UNCHANGED)
    t = (code == 8).astype(np.uint8)
    n, lab, st, cen = cv2.connectedComponentsWithStats(t, connectivity=8)
    st = st[1:]
    h, w, area = st[:, 3], st[:, 2], st[:, 4]
    keep = (area >= 20)
    dt = cv2.distanceTransform(t, cv2.DIST_L2, 3)
    # stroke width = 2 x median of the ridge (local max) of the distance transform, sampled over all text
    ridge = (dt >= cv2.dilate(dt, np.ones((3, 3), np.uint8))) & (t > 0)
    sw = 2 * dt[ridge]
    res = {'plate': plate, 'components': int(n - 1), 'components_area_ge_20': int(keep.sum()),
           'text_px': int(t.sum()),
           'height_px_percentiles_5_25_50_75_95': np.percentile(h[keep], [5, 25, 50, 75, 95]).round(1).tolist(),
           'width_px_percentiles_5_25_50_75_95': np.percentile(w[keep], [5, 25, 50, 75, 95]).round(1).tolist(),
           'stroke_width_px_percentiles_10_50_90': np.percentile(sw, [10, 50, 90]).round(2).tolist()}
    hist, edges = np.histogram(h[keep], bins=[0, 10, 15, 20, 25, 30, 35, 40, 50, 60, 80, 100, 131, 10000])
    res['height_histogram'] = {f'{int(edges[i])}-{int(edges[i+1])}': int(hist[i]) for i in range(len(hist))}
    print(json.dumps(res, indent=1))
    json.dump(res, open(os.path.join(O, f'text_sizes_{plate}.json'), 'w'), indent=1)
