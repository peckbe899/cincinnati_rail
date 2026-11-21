"""share of the green sides (N_edges.json) whose ink lies mostly in ink_bins.py's railroad / streetcar bins (the rail bins are the
ones that mean something on an unplaced plate)"""
import json, sys, numpy as np, cv2
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; U = SP + 'unet_data/'
tot = {}
for N in sys.argv[1:]:
    b = cv2.imread(U + f'{N}_bins.png', 0); names = {int(k): v['name'] for k, v in json.load(open(U + f'{N}_bins.json', encoding='utf8'))['bins'].items()}
    H, W = b.shape; e = json.load(open(U + f'{N}_edges.json', encoding='utf8')); res = {}
    for l in e:
        if l['state'] != 'green': continue
        a, c = np.array(l['a']), np.array(l['b']); L = np.hypot(*(c - a)); n = max(2, int(L / 3)); d = (c - a) / L; nr = np.array([-d[1], d[0]]); cnt = {}
        for q in a + np.outer(np.linspace(0.06, 0.94, n), c - a):
            for s in (0, -1, 1, -2, 2):
                x, y = (q + nr * s).round().astype(int)
                if 0 <= x < W and 0 <= y < H and b[y, x]: cnt[b[y, x]] = cnt.get(b[y, x], 0) + 1; break
        k = names.get(max(cnt, key=cnt.get), '?') if cnt else 'no ink'
        res[k] = res.get(k, 0) + L
    T = sum(res.values()); rail = res.get('railroad', 0) + res.get('streetcar', 0)
    print(f'plate {N}: green length {T:.0f}; mostly on railroad {100 * res.get("railroad", 0) / T:.1f}%, streetcar {100 * res.get("streetcar", 0) / T:.1f}%; bins: ' + ', '.join(f'{k} {100 * v / T:.0f}%' for k, v in sorted(res.items(), key=lambda x: -x[1])))
    for k, v in res.items(): tot[k] = tot.get(k, 0) + v
T = sum(tot.values()); print(f'ALL: green {T:.0f} px; railroad {100 * tot.get("railroad", 0) / T:.1f}%, streetcar {100 * tot.get("streetcar", 0) / T:.1f}%')
