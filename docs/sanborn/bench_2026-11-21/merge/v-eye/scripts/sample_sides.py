"""merge/v-eye: random samples of merged sides for the eye check, as montages of crops (21 Nov 2026).

    python -B sample_sides.py rail  [K] [SEED]   sides dropped 'on rail' that step 4 would otherwise show (was not 'not on a line')
    python -B sample_sides.py holes [K] [SEED]   exported hole sides
    python -B sample_sides.py bridges [K] [SEED] exported bridging sides
    python -B sample_sides.py edge [K] [SEED]    exported sides within 40 px inside the map ground's edge on the PDF sheets (merged)
-> merge/v-eye/samples/KIND_k.jpg (6 per image, each 600 x 600 px of the scan at full size, the sampled side magenta and
   numbered, the other merged exported lines thin green / orange / cyan) and samples/KIND.json (the list, for verdicts).
Plates: common.PLATES less 44 (44 has truth: scored against Ben's map in lost.py / sides_stats.py). Sampled uniform by
length (a long side is more likely), without replacement.
"""
import json, os, sys
import numpy as np
import cv2
import common as C
import views as V
from lost import L

KIND = sys.argv[1]; K = int(sys.argv[2]) if len(sys.argv) > 2 else 36; SEED = int(sys.argv[3]) if len(sys.argv) > 3 else 0
PL = [n for n in C.PLATES if n != '44'] if KIND != 'edge' else ['90', '30', '23', '21', '47']
pop = []
for n in PL:
    polys = json.load(open(V.src(n, 'merged'), encoding='utf8'))
    if KIND == 'edge':
        mf = C.ME + f'runs/merged/{n}/{n}_mapground.png'; m8 = cv2.imread(mf, 0) > 127
        d8 = cv2.distanceTransform(m8.astype(np.uint8), cv2.DIST_L2, 5) * 8
    for p in polys:
        for s in p:
            if s.get('paper_edge') or s['state'] == 'short': continue
            ok = False
            if KIND == 'rail': ok = s['state'] == 'on rail' and s.get('was') != 'not on a line'
            elif KIND == 'holes': ok = bool(s.get('hole')) and V.keep('merged', s)
            elif KIND == 'bridges': ok = 'bridge' in s and V.keep('merged', s)
            elif KIND == 'edge':
                if V.keep('merged', s):
                    mx, my = (s['a'][0] + s['b'][0]) / 2, (s['b'][1] + s['a'][1]) / 2
                    ok = d8[min(d8.shape[0] - 1, int(my / 8)), min(d8.shape[1] - 1, int(mx / 8))] <= 40
            if ok: pop.append((n, s))
w = np.array([L(s) for _, s in pop]); rng = np.random.default_rng(SEED)
idx = rng.choice(len(pop), size=min(K, len(pop)), replace=False, p=w / w.sum())
print(KIND, 'population', len(pop), 'sides', round(w.sum()), 'px; sample', len(idx))
os.makedirs(C.ME + 'samples', exist_ok=True); S = 600; tiles = []; rec = []
cache = {}
for j, i in enumerate(idx):
    n, s = pop[i]
    if n not in cache: cache.clear(); cache[n] = (V.scan(n), json.load(open(V.src(n, 'merged'), encoding='utf8')))
    full, polys = cache[n]; H, W = full.shape[:2]
    cx, cy = (s['a'][0] + s['b'][0]) / 2, (s['a'][1] + s['b'][1]) / 2; x0 = int(max(0, min(W - S, cx - S / 2))); y0 = int(max(0, min(H - S, cy - S / 2)))
    im = full[y0:y0 + S, x0:x0 + S].copy()
    P = lambda q: (int(round(q[0] - x0)), int(round(q[1] - y0)))
    for t, h in V.exported('merged', polys):
        if t is s: continue
        cv2.line(im, P(t['a']), P(t['b']), (255, 255, 0) if h else ((0, 170, 0) if t['state'] == 'on print' else (0, 140, 255)), 1, cv2.LINE_AA)
    cv2.line(im, P(s['a']), P(s['b']), (255, 0, 255), 2, cv2.LINE_AA)
    for q in (s['a'], s['b']): cv2.circle(im, P(q), 4, (255, 0, 255), -1)
    V.header(im, f"#{j} plate {n} {round(L(s))} px {s['state']}" + (f" was {s.get('was')}" if s.get('was') else '') + (f" bridge {s['bridge']}" if 'bridge' in s else ''), 24, 0.5)
    tiles.append(im); rec.append(dict(i=j, plate=n, a=s['a'], b=s['b'], len=round(L(s)), state=s['state'], was=s.get('was'), bridge=s.get('bridge'), hole=bool(s.get('hole')), crop_xy=[x0, y0]))
for k in range(0, len(tiles), 6):
    ts = tiles[k:k + 6] + [np.full((S, S, 3), 255, np.uint8)] * (6 - len(tiles[k:k + 6]))
    sv = np.full((S, 6, 3), 255, np.uint8); row = lambda a: np.hstack([a[0], sv, a[1], sv, a[2]])
    cv2.imwrite(C.must_be_mine(C.ME + f'samples/{KIND}_{k // 6}.jpg'), np.vstack([row(ts[:3]), np.full((6, 3 * S + 12, 3), 255, np.uint8), row(ts[3:])]), [cv2.IMWRITE_JPEG_QUALITY, 88])
json.dump(dict(kind=KIND, population_sides=len(pop), population_px=round(w.sum()), seed=SEED, sample=rec), open(C.must_be_mine(C.ME + f'samples/{KIND}.json'), 'w'), indent=1)
