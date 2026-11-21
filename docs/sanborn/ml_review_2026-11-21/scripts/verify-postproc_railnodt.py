"""overlap of 'green on railroad ink' (railgreen.py rule) and 'green without line-network support' (pp-2) per plate"""
import json, sys, numpy as np, cv2
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; U = SP + 'unet_data/'
for N in sys.argv[1:]:
    b = cv2.imread(U + f'{N}_bins.png', 0); names = {int(k): v['name'] for k, v in json.load(open(U + f'{N}_bins.json', encoding='utf8'))['bins'].items()}
    pl = cv2.imread(U + f'{N}_lines_lines_ng1.png', 0); H, W = pl.shape; lp = cv2.GaussianBlur(pl, (5, 5), 0).astype(np.float32)
    def along(img, a, c):
        d = c - a; L = np.hypot(*d); t = np.linspace(0.06, 0.94, max(10, int(L))); q = a + np.outer(t, d)
        return img[np.clip(q[:, 1].round().astype(int), 0, H - 1), np.clip(q[:, 0].round().astype(int), 0, W - 1)]
    T = rail = rail_nodt = nodt = 0.0
    for l in json.load(open(U + f'{N}_edges.json', encoding='utf8')):
        if l['state'] != 'green': continue
        a, c = np.array(l['a']), np.array(l['b']); L = np.hypot(*(c - a)); n = max(2, int(L / 3)); d = (c - a) / L; nr = np.array([-d[1], d[0]]); cnt = {}
        for q in a + np.outer(np.linspace(0.06, 0.94, n), c - a):
            for s in (0, -1, 1, -2, 2):
                x, y = (q + nr * s).round().astype(int)
                if 0 <= x < W and 0 <= y < H and b[y, x]: cnt[b[y, x]] = cnt.get(b[y, x], 0) + 1; break
        k = names.get(max(cnt, key=cnt.get), '?') if cnt else 'no ink'
        nd = along(lp, a, c).mean() <= 90; T += L; nodt += L * nd
        if k == 'railroad': rail += L; rail_nodt += L * nd
    print(f'{N:3s} green {T:7.0f}: railroad {100*rail/T:4.1f}% (of which no line-net support {100*rail_nodt/max(rail,1):4.1f}%), unsupported overall {100*nodt/T:4.1f}% -> railroad green left after the pp-2 gate {100*(rail-rail_nodt)/T:4.1f}% of green')
