"""merge/impl: pictures of the sides the merged outline step calls 'on rail' (21 Nov 2026), to judge them by eye.

    python -B rail_crops.py N [N ...] [--k 3]     -> merge/impl/rail_crops/N_overview.jpg and N_cropK.jpg

From merge/impl/plates/N/outlines.json and the batch's unet_data/N_bins.png (the bins the step used). Crops are full
resolution windows of 1800 x 1200 px round the K densest clusters of 'on rail' side length. Drawn: railroad ink red,
streetcar ink orange (tinted), 'on rail' sides magenta (thick), the sides step 4 keeps green (on print) or blue
(orange in the editor), sides step 4 drops for no line grey. The numbers by each magenta side are its index in
rail_crops/N_sides.json (with the state it would have had).
"""
import json, os, sys
import numpy as np
import cv2
import common as C
O = C.IMPL + 'rail_crops/'; os.makedirs(O, exist_ok=True)
K = int(sys.argv[sys.argv.index('--k') + 1]) if '--k' in sys.argv else 3
for n in [a for i, a in enumerate(sys.argv[1:], 1) if not a.startswith('--') and sys.argv[i - 1] != '--k']:
    polys = json.load(open(C.IMPL + f'plates/{n}/outlines.json', encoding='utf8')); im = cv2.imread(C.DATA + f'cufp/22-{n}.jpg'); H, W = im.shape[:2]
    B = cv2.imread(C.U + f"{n}_bins.png", 0) if "--batch-bins" in sys.argv else (lambda r: r)(cv2.imread(C.U + f"{n}_bins.png", 0) * 0)
    S = [s for p in polys for s in p if not s.get('paper_edge')]; R = [s for s in S if s['state'] == 'on rail']
    v = im.copy(); v[B == 4] = (v[B == 4] * 0.3 + np.array([0, 0, 255]) * 0.7).astype(np.uint8); v[B == 5] = (v[B == 5] * 0.3 + np.array([0, 140, 255]) * 0.7).astype(np.uint8)
    for s in S:
        if s['state'] == 'on rail': continue
        col = (0, 150, 0) if s['state'] == 'on print' else ((150, 150, 150) if s['state'] == 'not on a line' else (255, 120, 0))
        cv2.line(v, tuple(np.round(s['a']).astype(int)), tuple(np.round(s['b']).astype(int)), col, 3, cv2.LINE_AA)
    for i, s in enumerate(R):
        a, b = np.round(s['a']).astype(int), np.round(s['b']).astype(int); cv2.line(v, tuple(a), tuple(b), (200, 0, 200), 6, cv2.LINE_AA)
        m = (a + b) // 2; cv2.putText(v, str(i), (int(m[0]) + 8, int(m[1]) - 8), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (120, 0, 120), 3, cv2.LINE_AA)
    json.dump([dict(i=i, a=s['a'], b=s['b'], was=s.get('was'), rail=s.get('rail'), len=round(float(np.hypot(*(np.array(s['b']) - np.array(s['a'])))))) for i, s in enumerate(R)], open(O + f'{n}_sides.json', 'w'), indent=0)
    cv2.imwrite(O + f'{n}_overview.jpg', cv2.resize(v, None, fx=0.2, fy=0.2, interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 85])
    # densest windows of on-rail length
    dens = np.zeros((H // 200 + 1, W // 200 + 1))
    for s in R:
        m = (np.array(s['a']) + np.array(s['b'])) / 2; dens[int(m[1] // 200), int(m[0] // 200)] += np.hypot(*(np.array(s['b']) - np.array(s['a'])))
    dens = cv2.boxFilter(dens, -1, (9, 6), normalize=False, borderType=cv2.BORDER_CONSTANT)
    for k in range(K):
        if dens.max() <= 0: break
        y, x = np.unravel_index(np.argmax(dens), dens.shape); cx, cy = int(x * 200 + 100), int(y * 200 + 100)
        x0, y0 = max(0, min(W - 1800, cx - 900)), max(0, min(H - 1200, cy - 600))
        cv2.imwrite(O + f'{n}_crop{k}.jpg', v[y0:y0 + 1200, x0:x0 + 1800], [cv2.IMWRITE_JPEG_QUALITY, 88]); print(n, 'crop', k, x0, y0, flush=True)
        dens[max(0, y - 6):y + 7, max(0, x - 9):x + 10] = 0
    print(n, len(R), 'on rail sides', round(sum(np.hypot(*(np.array(s['b']) - np.array(s['a']))) for s in R)), 'px', flush=True)
