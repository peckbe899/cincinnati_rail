"""labels-9: verified length whose two sides (6-20 half px out) the area label calls the same class."""
import json
import numpy as np, cv2
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; U = SP + 'unet_data/'
for N in ('43', '44', '45', '80', '82A'):
    lab = cv2.imread(U + f'{N}_label.png', 0); h, w = lab.shape
    al = cv2.resize(np.load(SP + f'cufp/{N}/png_alpha_s4.npy').astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR) > 0.5
    dIn = cv2.distanceTransform(al.astype(np.uint8), cv2.DIST_L2, 5)
    tot = ss = bb = 0.0
    for a, b in json.load(open(U + f'{N}_verified.json', encoding='utf8')):
        a = np.array(a) / 2; b = np.array(b) / 2; L = np.hypot(*(b - a))
        if L < 2: continue
        d = (b - a) / L; n = np.array([-d[1], d[0]])
        for s in np.arange(0.5, L, 1.0):
            p = a + d * s
            if dIn[int(np.clip(round(p[1]), 0, h - 1)), int(np.clip(round(p[0]), 0, w - 1))] < 25: continue   # away from the paper edge
            side = []
            for sg in (1, -1):
                q = p[None, :] + sg * np.arange(6, 21)[:, None] * n[None, :]
                x = np.clip(q[:, 0].round().astype(int), 0, w - 1); y = np.clip(q[:, 1].round().astype(int), 0, h - 1)
                v = lab[y, x]; v = v[v != 255]
                side.append(None if len(v) < 5 else bool((v == 1).mean() > 0.5))
            tot += 1
            if side[0] is False and side[1] is False: ss += 1
            if side[0] is True and side[1] is True: bb += 1
    print(N, 'verified half-px length away from edge', int(tot), f'street both sides {ss / tot:.4f}', f'block both sides {bb / tot:.4f}')
