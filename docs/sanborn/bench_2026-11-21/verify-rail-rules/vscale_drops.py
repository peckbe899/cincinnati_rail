"""verify-rail-rules (21 Nov 2026): the group railroad filter (600 px / 60 px) is in pixels, so on the 400-ft sheets
(46-50, per the ml review's critic-2) the same ground length is half as many px. Draw every railroad track the patched
filter drops on 47, 49 and 50 (on rail-rules' proposed bins, which equal mine on the plates I re-ran), one tile each,
with all kept railroad tracks in green and the dropped one in red. Writes scale/drops_400ft.jpg and .json here.
    cd data/sanborn
    python bench_2026-11-21/verify-rail-rules/vscale_drops.py [47 49 50]"""
import os, sys, json, importlib.util
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); RR = os.path.join(os.path.dirname(HERE), 'rail-rules'); O = os.path.join(HERE, 'scale'); os.makedirs(O, exist_ok=True)
spec = importlib.util.spec_from_file_location('rtp', os.path.join(HERE, 'patched', 'rail_tracks.py')); RP = importlib.util.module_from_spec(spec); spec.loader.exec_module(RP)
plates = sys.argv[1:] or ['47', '49', '50']; tiles = []; info = []; HALF = 260
for N in plates:
    bp = os.path.join(RR, 'batch', f'{N}_bins.png'); B = cv2.imread(bp if os.path.exists(bp) else f'unet_data/{N}_bins.png', 0)
    rr = RP.railroad_tracks((B == 4).astype(np.uint8)); kept = RP.drop_alone(rr, *RP.TRACKS['rr_alone']); ks = {id(p) for p in kept}
    im = cv2.imread(f'cufp/22-{N}.jpg'); H, W = im.shape[:2]; c = im.copy()
    for p in kept: cv2.polylines(c, [np.round(np.asarray(p)).astype(np.int32)], False, (0, 170, 0), 3)
    for p in rr:
        if id(p) in ks: continue
        q = np.asarray(p); cx, cy = q.mean(0).round().astype(int)
        t = c.copy(); cv2.polylines(t, [np.round(q).astype(np.int32)], False, (0, 0, 255), 3)
        x0, y0 = max(0, cx - HALF), max(0, cy - HALF); crop = np.full((2 * HALF, 2 * HALF, 3), 255, np.uint8); s = t[y0:cy + HALF, x0:cx + HALF]; crop[:s.shape[0], :s.shape[1]] = s
        L = RP.plen(p); cv2.putText(crop, f'{len(tiles)} {N} ({cx},{cy}) {L:.0f}', (6, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
        tiles.append(crop); info.append(dict(tile=len(tiles) - 1, plate=N, at=[int(cx), int(cy)], len=round(L)))
cols = 6; rows = (len(tiles) + cols - 1) // cols
M = np.full((rows * 2 * HALF, cols * 2 * HALF, 3), 255, np.uint8)
for i, t in enumerate(tiles): r, k = divmod(i, cols); M[r * 2 * HALF:(r + 1) * 2 * HALF, k * 2 * HALF:(k + 1) * 2 * HALF] = t
cv2.imwrite(os.path.join(O, 'drops_400ft.jpg'), cv2.resize(M, None, fx=0.6, fy=0.6, interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 85])
json.dump(info, open(os.path.join(O, 'drops_400ft.json'), 'w'), indent=1); print(len(tiles), 'tiles')
