"""The rules' rail finds of a plate as tracks for the line editor (19 November 2026).

    cd data/sanborn
    python ../../tools/sanborn/unet/rail_tracks.py N [N ...]      or  --all  (every plate that has unet_data/N_bins.png)

Ben, 19 November 2026: the rules run on every plate (run_plates.py), "and then you put them into the line editor program
for me to check". The ink the rules call railroad (bin 4) and streetcar (bin 5) is turned into lines he can delete, move
or keep, so a plate is checked instead of drawn from nothing:
  railroad   the bin is closed (7 px), thinned to its centre line, the ticks (side branches under 24 px) cut off, and
             the centre line followed from end to end; at a switch the two pieces that run straight on are one track;
  streetcar  every heavy dash is a short straight piece; dashes that follow one another along a line (an end within
             TRACKS['car_reach'] px of the next dash's end, within 25 degrees) are joined into one track.
Writes unet_data/N_rail_rule.json: {plate, made, note, tracks: [{kind, pts, src: 'rule'}]} in full-size px.

21 November 2026, after the batch of 109 plates (data/sanborn/bench_2026-11-21/rail-rules: scored against Ben's 28
tracks on plate 44, run as a plate never placed, chosen on one half of it and read on the other; against his 10 checked
streetcar tracks on 1A; and by eye on random samples of what each change removes or adds on the other 107 plates):
  - railroad tracks lying within TRACKS['rr_alone'][1] px of one another form a group, and a group shorter than
    TRACKS['rr_alone'][0] px in all is dropped: on plates that were never placed these are lot lines with hook marks,
    and rows of lot or house numbers. Plate 44: precision 97.9% to 99.5% at 10 px, recall unchanged (98.4%)
  - streetcar dashes are joined across a longer gap (TRACKS['car_reach'], was 150 px): the dashes stop under street
    names and labels printed over the line. Plate 44: recall 83.4% to 88.6% at 30 px, 13 pieces to 9; all the
    length it adds off Ben's tracks lies under street names, where his own tracks stop
These are the rules' guess and nothing more. A track is Ben's only once he has kept it in the editor
(picks22_guided/22-N/rail_ben.json), and this script never writes there.
"""
import json, os, re, sys, time
import numpy as np
import cv2
from scipy.spatial import cKDTree

N8 = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
TRACKS = dict(rr_alone=(600, 60), car_reach=350)   # see the note above (21 November 2026)


def thin(m):
    """the mask worn down to a centre line one pixel wide (Zhang and Suen's thinning, on the mask's own pixels only:
    a plate is 70 million pixels and its rail a few hundred thousand), then the corners of its stair steps taken off"""
    a = np.pad(m > 0, 1); OFF = [(-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1)]   # P2..P9, clockwise from north
    ys, xs = np.nonzero(a)
    while True:
        gone = 0
        for step in (0, 1):
            P = [a[ys + dy, xs + dx] for dy, dx in OFF]; B = np.sum(P, axis=0); A = sum((~P[k]) & P[(k + 1) % 8] for k in range(8))
            c = ~(P[0] & P[2] & P[4]) & ~(P[2] & P[4] & P[6]) if step == 0 else ~(P[0] & P[2] & P[6]) & ~(P[0] & P[4] & P[6])
            d = (B >= 2) & (B <= 6) & (A == 1) & c; a[ys[d], xs[d]] = False; ys, xs = ys[~d], xs[~d]; gone += int(d.sum())
        if not gone: break
    for r in range(4):   # a pixel in the corner of a stair step: its two neighbours touch each other without it
        P = [a[ys + dy, xs + dx] for dy, dx in OFF]; i = 2 * r
        d = P[i] & P[(i + 2) % 8] & ~P[(i + 4) % 8] & ~P[(i + 5) % 8] & ~P[(i + 6) % 8]; a[ys[d], xs[d]] = False; ys, xs = ys[~d], xs[~d]
    return a[1:-1, 1:-1]


def graph(sk):
    """the centre line as pieces between ends and forks: [(path of (x, y), end kind at start, end kind at finish)], kind 1 = a free end"""
    ys, xs = np.nonzero(sk); S = set(zip(ys.tolist(), xs.tolist()))
    nb = {p: [(p[0] + dy, p[1] + dx) for dy, dx in N8 if (p[0] + dy, p[1] + dx) in S] for p in S}
    node = {p for p in S if len(nb[p]) != 2}; out = []; seen = set()
    for p in node:
        for q in nb[p]:
            if (p, q) in seen: continue
            path = [p, q]; seen.add((p, q))
            while path[-1] not in node:
                a = path[-1]; nxt = [r for r in nb[a] if r != path[-2]]
                if not nxt: break
                path.append(nxt[0])
            if path[-1] in node: seen.add((path[-1], path[-2]))
            out.append(([(x, y) for y, x in path], len(nb[p]), len(nb[path[-1]]) if path[-1] in node else 1))
    return out


def plen(p):
    p = np.asarray(p, float); return float(np.hypot(*np.diff(p, axis=0).T).sum())


def railroad_tracks(m, spur=24, short=60):
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)))
    sk = thin(m)
    for _ in range(3):   # cut the ticks off: a side branch under `spur` px that ends free
        cut = 0
        for path, k0, k1 in graph(sk):
            if (k0 == 1) != (k1 == 1) and len(path) < spur:
                for x, y in (path[:-1] if k0 == 1 else path[1:]): sk[y, x] = False
                cut += 1
        if not cut: break
        sk = thin(sk)
    P = [np.array(p, float) for p, _, _ in graph(sk) if len(p) >= 4]
    while True:   # at a switch the two pieces that run straight on are one track
        E = np.array([q for p in P for q in (p[0], p[-1])]).reshape(-1, 2); best = None
        if len(E) < 4: break
        def out_dir(k):
            p = P[k // 2]; n = min(len(p) - 1, 14); d = (p[0] - p[n]) if k % 2 == 0 else (p[-1] - p[-1 - n]); return d / max(1e-6, np.hypot(*d))
        for a, b in cKDTree(E).query_pairs(4.5):
            if a // 2 == b // 2: continue
            c = float(out_dir(a) @ out_dir(b))
            if c < -0.85 and (best is None or c < best[0]): best = (c, a, b)
        if best is None: break
        _, a, b = best; pa = P[a // 2] if a % 2 else P[a // 2][::-1]; pb = P[b // 2][::-1] if b % 2 else P[b // 2]   # pa ends at the switch, pb starts there
        P = [p for k, p in enumerate(P) if k not in (a // 2, b // 2)] + [np.vstack([pa, pb])]
    out = []
    for p in P:
        if plen(p) < short: continue
        out.append(cv2.approxPolyDP(p.astype(np.float32)[:, None, :], 3.0, False)[:, 0, :].astype(float))
    return out


def streetcar_tracks(m, reach=None, ang=25, short=150):
    reach = TRACKS['car_reach'] if reach is None else reach
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)); n, lb, st, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
    D = []   # dashes: (end, end, direction)
    for i in range(1, n):
        if st[i, 4] < 150: continue
        x, y, w, h = st[i, :4]; ys, xs = np.nonzero(lb[y:y + h, x:x + w] == i); q = np.c_[xs + x, ys + y].astype(float); c = q.mean(0)
        d = np.linalg.svd(q - c, full_matrices=False)[2][0]; t = (q - c) @ d; D.append((c + t.min() * d, c + t.max() * d, d))
    if len(D) < 2: return []
    E = np.array([e for a, b, _ in D for e in (a, b)]); O = np.array([o for _, _, d in D for o in (-d, d)]); cosa = np.cos(np.radians(ang)); best = {}
    for k, js in enumerate(cKDTree(E).query_ball_point(E, reach)):
        for j in js:
            if j // 2 == k // 2: continue
            v = E[j] - E[k]; L = np.hypot(*v)
            if np.hypot(*(E[j ^ 1] - E[k])) < L: continue                  # the far end of that dash
            if abs(O[k] @ O[j]) < cosa: continue                           # the two dashes do not run the same way
            if L > 10 and ((v @ O[k]) / L < cosa or abs(v[0] * O[k][1] - v[1] * O[k][0]) > 18): continue   # not straight on from this end
            if k not in best or L < best[k][0]: best[k] = (L, j)
    link = {k: j for k, (L, j) in best.items() if best.get(j, (0, -1))[1] == k}; used = set(); out = []
    for s in range(len(E)):   # start at a free end and walk the chain
        if s in link or s // 2 in used: continue
        pts = []; k = s
        while True:
            used.add(k // 2); pts += [E[k], E[k ^ 1]]; j = link.get(k ^ 1)
            if j is None or j // 2 in used: break
            k = j
        p = np.array(pts)
        if len(p) >= 4 and plen(p) >= short: out.append(cv2.approxPolyDP(p.astype(np.float32)[:, None, :], 2.5, False)[:, 0, :].astype(float))
    return out


def drop_alone(P, short, near):
    """railroad that stands alone and short is dropped: tracks lying within `near` px of one another form a group, and a
    group shorter than `short` px in all goes. On plates never placed (no street map) a lot line with hook marks, or a
    row of lot or house numbers, passes the tick rule now and then; such rows are short and lie by themselves or in
    small clusters, where a real spur or siding runs off a longer track"""
    if not P: return P
    S = [np.vstack([p[:1]] + [a[None] + np.linspace(0, 1, max(2, int(np.hypot(*(b - a)) / 5) + 1))[1:, None] * (b - a)[None] for a, b in zip(p[:-1], p[1:])]) for p in P]
    who = np.concatenate([np.full(len(s), i) for i, s in enumerate(S)]); T = cKDTree(np.vstack(S)); up = list(range(len(P)))
    def root(i):
        while up[i] != i: up[i] = up[up[i]]; i = up[i]
        return i
    for i, s in enumerate(S):
        for j in {int(j) for js in T.query_ball_point(s, near) for j in who[js]} - {i}: up[root(i)] = root(j)
    total = {}
    for i, p in enumerate(P): total[root(i)] = total.get(root(i), 0.0) + plen(p)
    return [p for i, p in enumerate(P) if total[root(i)] >= short]


def tracks(B):
    """the bins of a plate (ink_bins.py) -> its rule tracks [{kind, src, pts}]"""
    rr = railroad_tracks((B == 4).astype(np.uint8)); car = streetcar_tracks((B == 5).astype(np.uint8))
    if TRACKS['rr_alone']: rr = drop_alone(rr, *TRACKS['rr_alone'])
    return [dict(kind=k, src='rule', pts=[[round(float(x), 1), round(float(y), 1)] for x, y in p]) for k, P in (('railroad', rr), ('streetcar', car)) for p in P]


def run(N):
    f = f'unet_data/{N}_bins.png'; B = cv2.imread(f, 0); t0 = time.time()
    if B is None: print(f'plate {N}: no {f}'); return
    tr = tracks(B); rr = [t['pts'] for t in tr if t['kind'] == 'railroad']; car = [t['pts'] for t in tr if t['kind'] == 'streetcar']
    o = f'unet_data/{N}_rail_rule.json'
    json.dump(dict(plate=N, made=int(time.time()), bins_made=int(os.path.getmtime(f)), note="the rules' rail finds as tracks, to be checked by Ben in the line editor; not ground truth", tracks=tr), open(o + '.tmp', 'w', encoding='utf8', newline='\n'), separators=(',', ':')); os.replace(o + '.tmp', o)
    print(f'plate {N:4s} railroad {len(rr):3d} tracks {sum(plen(p) for p in rr):7.0f} px | streetcar {len(car):3d} tracks {sum(plen(p) for p in car):7.0f} px | {time.time() - t0:.0f} s', flush=True)


if __name__ == '__main__':
    order = lambda n: (int(re.match(r'\d+', n).group()), n)
    plates = sorted((f[:-len('_bins.png')] for f in os.listdir('unet_data') if f.endswith('_bins.png')), key=order) if '--all' in sys.argv else [a for a in sys.argv[1:] if not a.startswith('--')]
    for n in plates: run(n)
