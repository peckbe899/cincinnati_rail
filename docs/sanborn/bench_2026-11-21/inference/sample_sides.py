"""Random exported sides, uniform by length, as crops to judge by eye (is it a street side?). No truth exists on these plates.

    python sample_sides.py SETTING N[,N...] [--k 24] [--seed 1] [--only-new OTHER_SETTING]

Sides come from qa/SETTING/N/N_edges.json (what the line editor would get). A point is drawn uniformly along the total
exported length, and the side it falls on is shown: a 600 x 600 full-px window around that point at 0.5 size, the side in
magenta (thin, so the print under it stays visible), the sampled point as a cyan dot. --only-new OTHER: sample only
length that is NOT within 8 px (and 20 degrees) of a side exported under OTHER (what the setting adds);
--only-shared OTHER: only length that IS within 8 px of a side exported under OTHER.
Writes samples/SETTING[_only_vs_OTHER | _shared_with_OTHER]_K_sSEED.jpg (6 per row, numbered) and .json (plate, side, point).
"""
import json, os, sys
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/') + '/'
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
a = sys.argv[1:]
def opt(k, d): return a[a.index(k) + 1] if k in a else d
setting, plates = a[0], a[1].split(','); K = int(opt('--k', 24)); rng = np.random.default_rng(int(opt('--seed', 1))); other = opt('--only-new', None) or opt('--only-shared', None); SHARED = '--only-shared' in a
R, SC = 300, 0.5


def edges(s, n): return json.load(open(HERE + f'qa/{s}/{n}/{n}_edges.json', encoding='utf8'))


def covered(pt, d, oth):
    for e in oth:
        p0, p1 = np.array(e['a'], float), np.array(e['b'], float); v = p1 - p0; L = np.hypot(*v)
        if L < 1: continue
        t = np.clip((pt - p0) @ v / L ** 2, 0, 1)
        if np.hypot(*(pt - (p0 + t * v))) <= 8 and abs(d @ (v / L)) >= np.cos(np.radians(20)): return True
    return False


pool = []                                        # (plate, edge, length)
for n in plates:
    for e in edges(setting, n):
        L = float(np.hypot(e['b'][0] - e['a'][0], e['b'][1] - e['a'][1]))
        if L > 0: pool.append((n, e, L))
lens = np.array([p[2] for p in pool]); cum = np.cumsum(lens); picks = []; tries = 0
oth = {n: edges(other, n) for n in plates} if other else None
while len(picks) < K and tries < 20000:
    tries += 1; u = rng.uniform(0, cum[-1]); i = int(np.searchsorted(cum, u)); n, e, L = pool[i]
    t = (u - (cum[i] - L)) / L; p0, p1 = np.array(e['a'], float), np.array(e['b'], float); pt = p0 + t * (p1 - p0); d = (p1 - p0) / L
    if oth is not None and covered(pt, d, oth[n]) != SHARED: continue
    picks.append((n, e, pt))
tiles, rec = [], []
cache = {}
for k, (n, e, pt) in enumerate(picks):
    if n not in cache: cache[n] = cv2.imread(SP + f'cufp/22-{n}.jpg')
    im = cache[n]; H, W = im.shape[:2]; cx, cy = int(pt[0]), int(pt[1])
    x0, y0 = max(0, cx - R), max(0, cy - R); c = cv2.copyMakeBorder(im[y0:cy + R, x0:cx + R], max(0, R - cy), max(0, cy + R - H), max(0, R - cx), max(0, cx + R - W), cv2.BORDER_CONSTANT, value=(255, 255, 255))
    ox, oy = cx - R, cy - R; c = cv2.resize(c, None, fx=SC, fy=SC, interpolation=cv2.INTER_AREA)
    P = lambda q: (int(round((q[0] - ox) * SC)), int(round((q[1] - oy) * SC)))
    cv2.line(c, P(e['a']), P(e['b']), (255, 0, 255), 1, cv2.LINE_AA); cv2.circle(c, P(pt), 4, (255, 255, 0), -1)
    cv2.rectangle(c, (0, 0), (120, 18), (255, 255, 255), -1); cv2.putText(c, f'{k + 1} p{n} {e["state"][0]}', (3, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1, cv2.LINE_AA)
    tiles.append(cv2.copyMakeBorder(c, 2, 2, 2, 2, cv2.BORDER_CONSTANT, value=(0, 0, 0))); rec.append(dict(k=k + 1, plate=n, a=e['a'], b=e['b'], state=e['state'], point=[round(float(v), 1) for v in pt]))
while len(tiles) % 6: tiles.append(np.full_like(tiles[0], 255))
mont = np.vstack([np.hstack(tiles[i:i + 6]) for i in range(0, len(tiles), 6)])
os.makedirs(HERE + 'samples', exist_ok=True); tag = f"{setting}{(('_shared_with_' if SHARED else '_only_vs_') + other) if other else ''}_{K}_s{opt('--seed', 1)}"
cv2.imwrite(HERE + f'samples/{tag}.jpg', mont, [cv2.IMWRITE_JPEG_QUALITY, 90]); json.dump(dict(setting=setting, other=other, plates=plates, picks=rec, total_len=float(cum[-1])), open(HERE + f'samples/{tag}.json', 'w'), indent=1)
print(HERE + f'samples/{tag}.jpg', 'total exported length', round(float(cum[-1])))
