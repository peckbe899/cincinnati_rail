"""Draw candidate NEGATIVE marks (tick-like marks that are not ditto marks), seeded, scan only (dev_ditto, 26 Nov 2026).

    cd data/sanborn
    python -B bench_2026-11-26/text_fix/dev_ditto/scripts/neg_sample.py

Five samplers, each seeded with random.Random('neg-' + SAMPLER + '-' + plate), every draw kept in order with its
reason; the candidates are then looked at by eye (negatives/choose/sheet_*.png) and each is kept as a negative or
dropped (text, ditto, nothing tick-like) in that order, never chosen by how a finder treats it:
  rail      plates 44 and 5: Ben's railroad tracks (picks22_guided/22-N/rail_ben.json, read only). Along each track,
            every 1 px, the ink extent across the track within +-16 px; runs where it is 11 px or more (the line is
            4-7 px) are crossings: rail ticks. A random crossing is drawn (track chosen with weight by length).
  streetcar plates 44 and 5: Ben's streetcar tracks; a random point along a track, snapped to the nearest separate
            small ink piece (6-200 px) within 12 px: a dash or tick of the streetcar symbol.
  isolated  12 plates: a random separate ink piece of 6-80 px, 5-18 px long, elongated (length / width 2 or more from
            second moments): a free tick, dash, hook, prime, figure 1, speck ...
  dash      12 plates: as isolated, 8-40 px long, with a second piece of about its length (0.5-2x) within 45 px along
            its own axis (to 15 deg): a dash of a dashed line.
  lineend   12 plates: a random end point of the skeleton of a large ink piece (1000 px or more): a line end or stub.
Never within 60 px of a ditto truth word, inside H1-H4, or on a sealed plate. Writes negatives/choose/candidates.json.
"""
import json, math, os, random, sys
sys.dont_write_bytecode = True
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common import plate_img, paper
def skeletonize(m):
    """Zhang-Suen thinning in numpy (skimage does not import here: no lazy_loader; this cv2 has no ximgproc.thinning)"""
    I = np.pad(m.astype(np.uint8), 1)
    while True:
        ch = False
        for it in (0, 1):
            P = [np.roll(np.roll(I, -dy, 0), -dx, 1) for dy, dx in ((-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1))]
            B = sum(P); A = sum(((P[i] == 0) & (P[(i + 1) % 8] == 1)).astype(np.uint8) for i in range(8))
            c = (P[0] * P[2] * P[4] == 0) & (P[2] * P[4] * P[6] == 0) if it == 0 else (P[0] * P[2] * P[6] == 0) & (P[0] * P[4] * P[6] == 0)
            d = (I == 1) & (B >= 2) & (B <= 6) & (A == 1) & c
            if d.any(): I[d] = 0; ch = True
        if not ch: break
    return I[1:-1, 1:-1] > 0

DD = os.path.normpath(os.path.join(HERE, '..')); OUT = os.path.join(DD, 'negatives', 'choose'); os.makedirs(OUT, exist_ok=True)
SEALED = set('6 9 52 56 58 63 35 38 41 66 71 76 84 88 46 92'.split())
HELD = {'90': [[5640, 3950, 7140, 4950], [880, 2100, 2380, 3100]], '47': [[7040, 4560, 8540, 5560]], '54A': [[7190, 3950, 8690, 4950]]}
PLATES = ['30', '90', '60B', '19', '64A', '86', '3', '12', '57', '47', '48', '93A']   # 6 at 200 ft, 3 at 100 ft, 3 at 400 ft
N = dict(rail=16, streetcar=6, isolated=4, dash=2, lineend=2)   # plate 5 has no railroad track in rail_ben.json: all 16 rail ticks come from 44


def ditto_boxes():
    T = os.path.join(DD, 'truth'); C = json.load(open(os.path.join(T, 'crops.json'))); out = {}
    for k, c in C.items():
        f = os.path.join(T, f'{k}_words.json')
        if os.path.exists(f):
            for w in json.load(open(f))['words']:
                if w['kind'] == 'ditto': out.setdefault(c['plate'], []).append(w['aabb'])
    return out


DB = ditto_boxes()


def ok_place(p, x, y):
    if p in SEALED: return False
    for h in HELD.get(p, []):
        if h[0] - 60 <= x <= h[2] + 60 and h[1] - 60 <= y <= h[3] + 60: return False
    for b in DB.get(p, []):
        if b[0] - 60 <= x <= b[2] + 60 and b[1] - 60 <= y <= b[3] + 60: return False
    return True


_ink = {}
def ink(p):
    if p not in _ink:
        L = cv2.cvtColor(plate_img(p), cv2.COLOR_BGR2LAB)[..., 0]; _ink[p] = ((L < 140) & paper(p)).astype(np.uint8)
    return _ink[p]


_cc = {}
def comps(p):
    if p not in _cc:
        n, lb, st, cen = cv2.connectedComponentsWithStats(ink(p), connectivity=8); _cc[p] = (n, lb, st, cen)
    return _cc[p]


def shape(lb, st, k):
    x, y, w, h, A = st[k]; m = lb[y:y + h, x:x + w] == k; ys, xs = np.nonzero(m)
    if len(xs) < 3: return 0, 1, 0
    c = np.cov(np.vstack([xs, ys])); ev, evec = np.linalg.eigh(c); ev = np.maximum(ev, 1e-6)
    L = 4 * math.sqrt(ev[1]); W = 4 * math.sqrt(ev[0]); ang = math.degrees(math.atan2(evec[1, 1], evec[0, 1]))
    return L, L / max(W, 1e-3), ang


def rail_draws(p, kind):
    R = json.load(open(f'picks22_guided/22-{p}/rail_ben.json'))['tracks']; trk = [np.array(t['pts'], float) for t in R if t['kind'] == kind]
    if not trk: return [dict(sampler=kind, plate=p, verdict=f'no {kind} track in rail_ben.json')]
    lens = [float(np.sum(np.hypot(*np.diff(t, axis=0).T))) for t in trk]
    rng = random.Random(f'neg-{kind}-{p}'); I = ink(p); H, W = I.shape; out = []
    n, lb, st, cen = comps(p)
    for k in range(400):
        if sum(d_['verdict'] == 'candidate' for d_ in out) >= N['rail' if kind == 'railroad' else 'streetcar']: break
        t = rng.choices(range(len(trk)), weights=lens)[0]; P = trk[t]
        seg = np.hypot(*np.diff(P, axis=0).T); s = rng.uniform(0, seg.sum()); i = int(np.searchsorted(np.cumsum(seg), s)); i = min(i, len(seg) - 1)
        f = (s - (np.cumsum(seg)[i] - seg[i])) / max(seg[i], 1e-6); x, y = P[i] + f * (P[i + 1] - P[i])
        u = (P[i + 1] - P[i]) / max(seg[i], 1e-6); v = np.array([-u[1], u[0]])
        d = dict(sampler='rail' if kind == 'railroad' else 'streetcar', plate=p, draw=k, at=[round(float(x), 1), round(float(y), 1)])
        snapped = None
        if kind == 'streetcar':   # a separate small piece (a dash of the symbol) within 12 px, else the nearest crossing as for rail
            x0, y0 = int(x) - 12, int(y) - 12; sub = lb[max(0, y0):y0 + 25, max(0, x0):x0 + 25]; ks = [k_ for k_ in np.unique(sub) if k_ and 6 <= st[k_, 4] <= 200]
            if ks: k_ = min(ks, key=lambda k_: math.hypot(cen[k_][0] - x, cen[k_][1] - y)); snapped = cen[k_]; d['how'] = 'separate piece'
        if snapped is not None: cx, cy = snapped
        else:   # walk along the track from the drawn point to the nearest crossing (extent >= 11 px)
            best = None
            for step in range(0, 120):
                for sgn in (1, -1):
                    q = np.array([x, y]) + sgn * step * u
                    cols = [I[int(round(q[1] + o * v[1])), int(round(q[0] + o * v[0]))] if 0 <= int(round(q[0] + o * v[0])) < W and 0 <= int(round(q[1] + o * v[1])) < H else 0 for o in range(-16, 17)]
                    if sum(cols) >= 11: best = q; break
                if best is not None: break
            if best is None: d['verdict'] = 'no crossing within 120 px'; out.append(d); continue
            cx, cy = best; d['how'] = 'crossing'
        if not ok_place(p, cx, cy): d['verdict'] = 'too near a ditto word or H1-H4'; out.append(d); continue
        d.update(centre=[int(round(cx)), int(round(cy))], verdict='candidate'); out.append(d)
    return out


def piece_draws(p, sampler):
    n, lb, st, cen = comps(p); rng = random.Random(f'neg-{sampler}-{p}'); out = []
    A = st[:, 4]; side = np.maximum(st[:, 2], st[:, 3])
    if sampler == 'lineend': pool = np.nonzero(A >= 1000)[0]; pool = pool[pool > 0]
    else: pool = np.nonzero((A >= 6) & (A <= 80) & (side >= 5) & (side <= (18 if sampler == 'isolated' else 40)))[0]; pool = pool[pool > 0]
    if sampler == 'dash': pool = np.nonzero((A >= 8) & (A <= 200) & (side >= 8) & (side <= 40))[0]; pool = pool[pool > 0]
    tries = 0
    while len([d for d in out if d['verdict'] == 'candidate']) < N[sampler] and tries < 3000:
        tries += 1; k = int(rng.choice(pool)); d = dict(sampler=sampler, plate=p, draw=tries, piece_box=[int(st[k, 0]), int(st[k, 1]), int(st[k, 0] + st[k, 2] - 1), int(st[k, 1] + st[k, 3] - 1)])
        if sampler == 'lineend':
            # a random pixel of the piece, then the skeleton of the piece in a 120 px window round it (whole pieces are too big)
            ys_, xs_ = np.nonzero(lb[st[k, 1]:st[k, 1] + st[k, 3], st[k, 0]:st[k, 0] + st[k, 2]] == k); j = rng.randrange(len(xs_))
            px_, py_ = st[k, 0] + xs_[j], st[k, 1] + ys_[j]; x, y = max(0, px_ - 60), max(0, py_ - 60)
            m = (lb[y:y + 121, x:x + 121] == k); sk = skeletonize(m).astype(np.uint8); sk[:3, :] = 0; sk[-3:, :] = 0; sk[:, :3] = 0; sk[:, -3:] = 0
            nb = cv2.filter2D(sk, -1, np.ones((3, 3), np.float32), borderType=cv2.BORDER_CONSTANT)
            ends = np.argwhere((sk > 0) & (nb == 2))
            if not len(ends): d['verdict'] = 'no skeleton end'; out.append(d); continue
            ey, ex = ends[rng.randrange(len(ends))]; cx, cy = x + ex, y + ey
        else:
            L, el, ang = shape(lb, st, k)
            if el < 2.0: d['verdict'] = f'not elongated ({el:.1f})'; out.append(d); continue
            cx, cy = cen[k]
            if sampler == 'dash':
                a = math.radians(ang); u = np.array([math.cos(a), math.sin(a)]); found = False
                x0, y0 = int(cx) - 50, int(cy) - 50; sub = lb[max(0, y0):y0 + 101, max(0, x0):x0 + 101]
                for k2 in np.unique(sub):
                    if k2 in (0, k) or not (8 <= st[k2, 4] <= 200): continue
                    dv = cen[k2] - cen[k]; dist = float(np.hypot(*dv))
                    if dist > 45 + L or dist < 3: continue
                    L2, el2, ang2 = shape(lb, st, k2)
                    if el2 < 2.0 or not (0.5 <= L2 / max(L, 1) <= 2): continue
                    da = abs((ang2 - ang + 90) % 180 - 90); along = abs((math.degrees(math.atan2(dv[1], dv[0])) - ang + 90) % 180 - 90)
                    if da <= 15 and along <= 15 and dist - (L + L2) / 2 <= 45: found = True; break
                if not found: d['verdict'] = 'no collinear partner'; out.append(d); continue
        if not ok_place(p, cx, cy): d['verdict'] = 'too near a ditto word or H1-H4'; out.append(d); continue
        d.update(centre=[int(round(cx)), int(round(cy))], verdict='candidate'); out.append(d)
    return out


def main():
    allc = []
    for p in ('44', '5'):
        allc += rail_draws(p, 'railroad'); allc += rail_draws(p, 'streetcar')
    for p in PLATES:
        for s in ('isolated', 'dash', 'lineend'): allc += piece_draws(p, s)
        _ink.pop(p, None); _cc.pop(p, None)
    cand = [d for d in allc if d['verdict'] == 'candidate']
    for i, d in enumerate(cand): d['cid'] = f'C{i + 1:03d}'
    json.dump(dict(note=__doc__, draws=allc), open(os.path.join(OUT, 'candidates.json'), 'w'), indent=1)
    print(len(allc), 'draws,', len(cand), 'candidates')
    import collections; print(collections.Counter(d['sampler'] for d in cand))


if __name__ == '__main__':
    main()
