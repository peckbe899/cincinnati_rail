"""Verified (line-target) segments with the area label calling BOTH sides street (offsets 6..20 half px), away from the paper edge."""
import json, sys
import numpy as np, cv2
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; U = SP + 'unet_data/'
for N in ['43', '44', '45', '80', '82A']:
    lab = cv2.imread(U + f'{N}_label.png', 0); h, w = lab.shape
    alpha = cv2.resize(np.load(SP + f'cufp/{N}/png_alpha_s4.npy').astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR) > 0.5
    nearpaper = cv2.dilate((~alpha).astype(np.uint8), np.ones((41, 41), np.uint8)) > 0
    ver = json.load(open(U + f'{N}_verified.json', encoding='utf8')); Lt = Lb = Lb1 = 0; bad = []
    for a, b in ver:
        a = np.array(a) / 2; b = np.array(b) / 2; L = np.hypot(*(b - a)); Lt += 2 * L
        if L < 5: continue
        d = (b - a) / L; n = np.array([-d[1], d[0]]); t = np.linspace(0.15, 0.85, 12); P = a + np.outer(t, b - a)
        if nearpaper[np.clip(P[:, 1].astype(int), 0, h - 1), np.clip(P[:, 0].astype(int), 0, w - 1)].mean() > 0.3: continue
        side = []
        for s in (1, -1):
            v = []
            for o in range(6, 21, 2):
                Q = P + s * o * n; x = np.clip(Q[:, 0].round().astype(int), 0, w - 1); y = np.clip(Q[:, 1].round().astype(int), 0, h - 1); v.append(lab[y, x])
            v = np.array(v); side.append(((v == 0).sum() / max(1, (v != 255).sum()), (v == 1).sum() / max(1, (v != 255).sum())))
        if side[0][0] > 0.8 and side[1][0] > 0.8: Lb += 2 * L; bad.append((round(2 * L), (a * 2).round().tolist(), (b * 2).round().tolist()))
        if side[0][1] > 0.8 and side[1][1] > 0.8: Lb1 += 2 * L
    bad.sort(reverse=True)
    print(N, 'target length', round(Lt), '| street on both sides (away from paper edge):', round(Lb), round(Lb / Lt, 4), '| block on both sides:', round(Lb1), round(Lb1 / Lt, 4), '| longest:', bad[:4])
