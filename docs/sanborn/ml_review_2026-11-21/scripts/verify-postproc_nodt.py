"""Share of exported green length (outlines.json 'on print', not paper edge) with no line-network support (along(lp) <= 90)."""
import json, sys, os
import numpy as np, cv2
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; U = SP + 'unet_data/'
tot = [0.0, 0.0]
for N in sys.argv[1:]:
    bj = U + f'{N}_blocks_ng.json'
    if not os.path.exists(bj): continue
    pl = cv2.imread(U + f'{N}_lines_lines_ng1.png', 0); H, W = pl.shape; lp = cv2.GaussianBlur(pl, (5, 5), 0).astype(np.float32)
    def along(img, a, b):
        d = b - a; L = np.hypot(*d); t = np.linspace(0.06, 0.94, max(10, int(L))); q = a + np.outer(t, d)
        return img[np.clip(q[:, 1].round().astype(int), 0, H - 1), np.clip(q[:, 0].round().astype(int), 0, W - 1)]
    g = n_ = 0.0; cnt = [0, 0]
    for p in json.load(open(SP + f'picks22_guided/22-{N}/outlines.json', encoding='utf8')):
        for s in p:
            if s['state'] != 'on print' or s.get('paper_edge'): continue
            a, b = np.array(s['a']), np.array(s['b']); L = np.hypot(*(b - a)); g += L; cnt[0] += 1
            if along(lp, a, b).mean() <= 90: n_ += L; cnt[1] += 1
    tot[0] += g; tot[1] += n_
    print(f'{N:4s} green {g:8.0f} px ({cnt[0]} sides), unsupported {n_:7.0f} px ({cnt[1]} sides) = {100 * n_ / max(g, 1):5.1f}%')
print(f'ALL green {tot[0]:.0f}, unsupported {100 * tot[1] / tot[0]:.1f}%')
