"""review-leak: what the line target says on the pixels where the 7th input (area_in, resized as edgenet.pack does)
crosses 0.5: share positive (1), negative (0), not scored (255), and the share negative within 3 px. Reads only.
cd data/sanborn; python -B bench_2026-11-23/train/review-leak/scripts/channel7_boundary.py"""
import json
import numpy as np, cv2
D = 'train_v2/'; man = json.load(open(D + 'manifest.json', encoding='utf8'))['plates']; res = {}
for N, e in man.items():
    t = cv2.imread(D + N + '/lines.png', 0); H, W = t.shape
    a = cv2.resize(cv2.imread(D + N + '/area_in.png', 0), (W, H), interpolation=cv2.INTER_LINEAR)
    b = cv2.morphologyEx((a > 127).astype(np.uint8), cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)) > 0; del a
    if N == '1A': b &= ~(cv2.resize(cv2.imread(D + '1A/valmask.png', 0), (W, H), interpolation=cv2.INTER_NEAREST) > 0)
    neg3 = cv2.dilate((t == 0).astype(np.uint8), np.ones((7, 7), np.uint8)) > 0
    n = int(b.sum()); tb = t[b]
    res[N] = dict(source=e['source'], boundary_px=n, pos=round(float((tb == 1).mean()), 4), neg=round(float((tb == 0).mean()), 4), unscored=round(float((tb == 255).mean()), 4), neg_within_3px=round(float(neg3[b].mean()), 4))
    print(N, json.dumps(res[N]), flush=True)
json.dump(res, open('bench_2026-11-23/train/review-leak/channel7_boundary.json', 'w'), indent=1)
