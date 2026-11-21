"""Per plate: how much of the line target (N_verified.json) lies on black/grey ink; and edges Ben marked wrong still in the target."""
import json, os
import numpy as np, cv2
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; U = SP + 'unet_data/'
def _same(a_, b_, p_, q_):
    a_, b_, p_, q_ = (np.asarray(v_, float) for v_ in (a_, b_, p_, q_)); d1, d2 = b_ - a_, q_ - p_; L2 = np.hypot(*d2) or 1.0; m_ = (a_ + b_) / 2
    t_ = np.clip(((m_ - p_) @ d2) / L2 ** 2, 0, 1)
    return np.hypot(*(m_ - (p_ + t_ * d2))) < 8 and abs(d1 @ d2) / ((np.hypot(*d1) or 1.0) * L2) > 0.97
for N in ['43', '44', '45', '80', '82A']:
    full = cv2.imread(SP + f'cufp/22-{N}.jpg'); H, W = full.shape[:2]
    hsv = cv2.cvtColor(full, cv2.COLOR_BGR2HSV); ink = ((hsv[:, :, 2] < 120) | ((hsv[:, :, 1] < 90) & (hsv[:, :, 2] < 170))).astype(np.uint8)
    del hsv
    ink2 = cv2.dilate(ink, np.ones((5, 5), np.uint8)) > 0
    alphaF = cv2.resize(np.load(SP + f'cufp/{N}/png_alpha_s4.npy').astype(np.float32), (W, H)) > 0.5
    ver = json.load(open(U + f'{N}_verified.json', encoding='utf8')); Lt = 0; Llow = 0; nlow = 0; Loff = 0
    for a, b in ver:
        L = np.hypot(b[0] - a[0], b[1] - a[1]); Lt += L; t = np.linspace(0, 1, max(2, int(L))); q = np.array(a) + np.outer(t, np.array(b) - np.array(a))
        x = np.clip(q[:, 0].round().astype(int), 0, W - 1); y = np.clip(q[:, 1].round().astype(int), 0, H - 1)
        on = alphaF[y, x]
        if on.mean() < 0.5: Loff += L; continue
        cov = ink2[y[on], x[on]].mean()
        if cov < 0.5: Llow += L; nlow += 1
    bf = SP + f'picks22_guided/22-{N}/edges_ben.json'; wr = []
    if os.path.exists(bf): wr = [(l['a0'], l['b0']) for l in json.load(open(bf, encoding='utf8'))['lines'] if l.get('verdict') == 'wrong']
    Lw = sum(np.hypot(b[0] - a[0], b[1] - a[1]) for a, b in ver if any(_same(a, b, *o) for o in wr))
    print(N, 'target length', round(Lt), '| segments <50% on ink (within 2 px):', nlow, 'length share', round(Llow / Lt, 4), '| mostly off paper share', round(Loff / Lt, 4), '| Ben-wrong lines in edges_ben:', len(wr), 'target length matching them', round(Lw), round(Lw / Lt, 4))
