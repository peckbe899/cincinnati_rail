"""HAND-OFF COPY (text_v1/handoff, 26 Nov 2026) of tools/sanborn/unet/rail_tracks.py (sha256 16a4c4ed..., commit 81deb06).
NOT the repo file; never writes the repo. Changes, marked '# TEXT-FIRST':
  - run() reads a given bins PNG (not unet_data/N_bins.png) and writes a given json inside text_v1/handoff;
  - --text N_text.png [--text-codes 2,3]: masked ink cannot be rails: the text pixels are taken out of bin 4 (railroad)
    and bin 5 (streetcar) before the tracks are traced. On bins made by ink_bins_text.py --text this changes nothing
    (that ink is bin 8 already); it matters only for bins sorted without the mask.
  - with --text, two railroad tracks whose ends face each other across a gap that lies on text are joined into one
    (join_across_text): a track's line is broken where a letter is written over it (plate 44: the R of REILTY across
    Ben's track 16 at 5195,6100). The text stays text; only the traced centre line crosses the gap. --no-text-join: off.
The tracing itself (railroad_tracks, streetcar_tracks) is unchanged.

    cd data/sanborn
    python -B bench_2026-11-25/text_v1/handoff/code/rail_tracks_text.py N BINS.png OUT.json [--text N_text.png] [--text-codes 2,3]

The rest of this docstring is the original's.

The rules' rail finds of a plate as tracks for the line editor (19 November 2026).

    cd data/sanborn
    python ../../tools/sanborn/unet/rail_tracks.py N [N ...]      or  --all  (every plate that has unet_data/N_bins.png)

Ben, 19 November 2026: the rules run on every plate (run_plates.py), "and then you put them into the line editor program
for me to check". The ink the rules call railroad (bin 4) and streetcar (bin 5) is turned into lines he can delete, move
or keep, so a plate is checked instead of drawn from nothing:
  railroad   the bin is closed (7 px), thinned to its centre line, the ticks (side branches under 24 px) cut off, and
             the centre line followed from end to end; at a switch the two pieces that run straight on are one track;
  streetcar  every heavy dash is a short straight piece; dashes that follow one another along a line (an end within
             150 px of the next dash's end, within 25 degrees) are joined into one track.
Writes unet_data/N_rail_rule.json: {plate, made, note, tracks: [{kind, pts, src: 'rule'}]} in full-size px.
These are the rules' guess and nothing more. A track is Ben's only once he has kept it in the editor
(picks22_guided/22-N/rail_ben.json), and this script never writes there.
"""
import json, os, re, sys, time
import numpy as np
import cv2
from scipy.spatial import cKDTree

N8 = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


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


def streetcar_tracks(m, reach=150, ang=25, short=150):
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


SAFE = os.path.normcase(os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')))   # TEXT-FIRST: text_v1/handoff
JOIN = dict(gap=90.0, ang=25.0, off=8.0, share=0.3, near=4)   # TEXT-FIRST: ends <= 90 px apart, facing within 25 degrees (directions read over 40 px), one end <= 8 px off the other's line, >= 30% of the gap within 4 px of text


def join_across_text(P, T, gap=JOIN['gap'], ang=JOIN['ang'], off=JOIN['off'], share=JOIN['share'], near=JOIN['near']):   # TEXT-FIRST
    """join railroad tracks (lists of points) whose ends face each other across a gap lying on text (T, bool); the closest
    pair first, until none is left. Returns the tracks and the number of joins"""
    tn = cv2.dilate(T.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * near + 1, 2 * near + 1))) > 0; H, W = tn.shape
    P = [np.asarray(p, float) for p in P]; n = 0; cosa = np.cos(np.radians(ang))
    def end(p, e):   # the end point and the direction the track leaves it, read over the last 40 px or more (a short hook at the end does not count)
        pp = p if e == 1 else p[::-1]; q = pp[-1]; r = pp[-2]
        for r in pp[-2::-1]:
            if np.hypot(*(q - r)) >= 40: break
        d = q - r; return q, d / max(1e-6, np.hypot(*d))
    while True:
        best = None
        for k in range(len(P)):
            for j in range(k + 1, len(P)):
                for e in (0, 1):
                    for f in (0, 1):
                        qa, da = end(P[k], e); qb, db = end(P[j], f); v = qb - qa; L = np.hypot(*v)
                        if L > gap or L < 1 or da @ db > -cosa or (v / L) @ da < cosa or min(abs(v[0] * da[1] - v[1] * da[0]), abs(v[0] * db[1] - v[1] * db[0])) > off: continue   # off: the nearer of the two ends' lines
                        t = np.linspace(0, 1, max(2, int(L))); q = (qa[None] + t[:, None] * v[None]).round().astype(int)
                        sh = tn[np.clip(q[:, 1], 0, H - 1), np.clip(q[:, 0], 0, W - 1)].mean()
                        if sh >= share and (best is None or L < best[0]): best = (L, k, e, j, f)
        if best is None: return P, n
        _, k, e, j, f = best; a_ = P[k] if e == 1 else P[k][::-1]; b_ = P[j] if f == 0 else P[j][::-1]
        P = [p for i, p in enumerate(P) if i not in (k, j)] + [np.vstack([a_, b_])]; n += 1



JOIN_TEXT = True   # TEXT-FIRST: --no-text-join turns join_across_text off


def run(N, bins_png, out_json, text=None, codes=(2, 3)):   # TEXT-FIRST: given bins and output; optional text mask
    assert os.path.normcase(os.path.abspath(out_json)).startswith(SAFE + os.sep), f'rail_tracks_text.py: write only inside {SAFE}: {out_json}'
    B = cv2.imread(bins_png, 0); t0 = time.time()
    if B is None: print(f'plate {N}: no {bins_png}'); return
    T = np.zeros(B.shape, bool)
    if text:
        tc = cv2.imread(text, cv2.IMREAD_UNCHANGED); assert tc is not None and tc.shape[:2] == B.shape, text; T = np.isin(tc, codes); del tc
    rr = railroad_tracks(((B == 4) & ~T).astype(np.uint8)); car = streetcar_tracks(((B == 5) & ~T).astype(np.uint8))
    joins = 0
    if text and JOIN_TEXT: rr, joins = join_across_text(rr, T)   # TEXT-FIRST
    tr = [dict(kind=k, src='rule', pts=[[round(float(x), 1), round(float(y), 1)] for x, y in p]) for k, P in (('railroad', rr), ('streetcar', car)) for p in P]
    json.dump(dict(plate=N, made=int(time.time()), bins=bins_png, text=text, text_codes=list(codes), masked_rail_px=int((np.isin(B, (4, 5)) & T).sum()), joins_across_text=joins,
                   note="handoff copy: the rules' rail finds as tracks; not ground truth", tracks=tr), open(out_json, 'w', encoding='utf8'), separators=(',', ':'))
    print(f'joins across text {joins} | ' if text else '', end='')
    print(f'plate {N:4s} railroad {len(rr):3d} tracks {sum(plen(p) for p in rr):7.0f} px | streetcar {len(car):3d} tracks {sum(plen(p) for p in car):7.0f} px | {time.time() - t0:.0f} s', flush=True)


if __name__ == '__main__':   # TEXT-FIRST: N BINS.png OUT.json [--text P] [--text-codes 2,3]
    a = sys.argv; tx = a[a.index('--text') + 1] if '--text' in a else None
    cd = tuple(int(v) for v in a[a.index('--text-codes') + 1].split(',')) if '--text-codes' in a else (2, 3)
    JOIN_TEXT = '--no-text-join' not in a
    run(a[1], a[2], a[3], tx, cd)
