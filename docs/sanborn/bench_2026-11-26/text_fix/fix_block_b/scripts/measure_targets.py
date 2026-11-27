"""Measure the dev block-number targets: size, stroke width, angle, and what finder3 called their text px.
    python -B .../scripts/measure_targets.py OUT.json"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'code'))
import numpy as np, cv2
import bfcommon as C

crops = C.dev_crops(); out = {}; cache = {}
for tid, c in sorted(crops.items()):
    N = c['plate']; x0, y0, x1, y1 = c['win']
    T = cv2.imread(os.path.join(C.DEVB, 'truth', f'{tid}_mask.png'), 0)
    W = json.load(open(os.path.join(C.DEVB, 'truth', f'{tid}_words.json'), encoding='utf8'))['words']
    w = [q for q in W if q.get('target')][0]
    pm = np.zeros(T.shape, np.uint8); cv2.fillPoly(pm, [np.round(np.array(w['poly']) - [x0, y0]).astype(np.int32)], 1)
    t2 = (T == 2) & (pm > 0); t3 = (T == 3) & (pm > 0)
    if N not in cache:
        cache.clear(); cache[N] = cv2.imread(C.f3_path(N), 0)
    code = cache[N][y0:y1, x0:x1]
    dt = cv2.distanceTransform(((t2 | t3)).astype(np.uint8), cv2.DIST_L2, 5)
    sk = (dt >= cv2.dilate(dt, np.ones((3, 3), np.uint8))) & (dt > 0)
    sw = 2 * dt[sk]
    ys, xs = np.nonzero(t2)
    miss = t2 & ~np.isin(code, (2, 3))
    out[tid] = dict(plate=N, scale=c['scale_ft_per_inch'], reading=w['reading'], angle=w['angle'], height=w['height'], length=w['length'],
                    text_px=int(t2.sum()), care_px=int(t3.sum()), sw_med=round(float(np.median(sw)), 2) if len(sw) else None,
                    sw_p25=round(float(np.percentile(sw, 25)), 2) if len(sw) else None, sw_p75=round(float(np.percentile(sw, 75)), 2) if len(sw) else None,
                    ink_h=int(ys.max() - ys.min() + 1), ink_w=int(xs.max() - xs.min() + 1),
                    missed=int(miss.sum()), missed_by_code={str(v): int((miss & (code == v)).sum()) for v in range(6)})
    print(tid, out[tid])
json.dump(out, open(sys.argv[1], 'w'), indent=1)
