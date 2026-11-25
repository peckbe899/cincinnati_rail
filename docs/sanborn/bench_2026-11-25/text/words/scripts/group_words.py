"""Group a plate's character candidates into strings (phrases), split them into words, attach the small marks, and
find each string's centre line and height. Library for run_words.py (also runnable by itself).

    cd data/sanborn
    python -B bench_2026-11-25/text/words/scripts/group_words.py N [--src bins|finder]

Candidates: ink_bins bin 8 (unet_data/N_bins.png), or the finder agent's mask (--src finder) if it exists.
Written 25 Nov 2026 (words agent); rules only, nothing fitted."""
import json, os, sys, time
import numpy as np
import cv2
from scipy.spatial import cKDTree
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wordlib as wl  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'out')
MULTI = 2.0          # a lone piece this many times longer than wide (and 12 px or more wide) is several touching characters
WORD_GAP = 0.6       # a gap wider than this times the height splits a phrase into words ...
JOIN_GAP = 1.0       # ... unless a hyphen, decimal point or period sits mid-gap and the gap is under this times the height
SPACED = dict(min_s=26, reach=4.0, size=1.35, ang=10.0, even=1.5, perp=0.15, across=0.5)   # widely spaced capitals (A  V  E, A L L E Y)


def arg(k, d=None, n=1):
    if k not in sys.argv: return d
    i = sys.argv.index(k)
    return sys.argv[i + 1] if n == 1 else sys.argv[i + 1:i + 1 + n]


def load_candidates(N, src):
    """the candidate text ink: ink_bins bin 8, or the finder agent's text codes (2 glyph or cluster, 3 stroke or dot taken
    in by a glyph, 4 lone stroke) in finder/out/N_finder.png"""
    if src == 'finder':
        f = f'bench_2026-11-25/text/finder/out/{N}_finder.png'
        if not os.path.exists(f): sys.exit('no finder output for plate ' + N)
        m = cv2.imread(f, 0); return (m >= 2) & (m <= 4), f
    b = cv2.imread(f'unet_data/{N}_bins.png', 0)
    return b == 8, f'unet_data/{N}_bins.png'


def in_rows(G, idx):
    """small pieces that are one of a row of like pieces (the dashes of a dashed line, the dots of a dotted one): not marks"""
    if len(idx) < 3: return np.zeros(len(idx), bool)
    c = G['c'][idx]; s = G['s'][idx]; t = G['t'][idx]; a = G['ang'][idx]
    tree = cKDTree(c); row = np.zeros(len(idx), bool)
    for i, js in enumerate(tree.query_ball_point(c, 3.2 * s + 2)):
        el = s[i] / max(t[i], 1) >= 2.5; u = np.array([np.cos(a[i]), np.sin(a[i])]); sides = set()
        for j in js:
            if j == i or max(s[i], s[j]) / max(min(s[i], s[j]), 1) > 1.5: continue
            v = c[j] - c[i]; d = np.hypot(*v)
            if d < 1: continue
            if el:
                if s[j] / max(t[j], 1) < 2.5: continue
                da = abs(((a[j] - a[i] + np.pi / 2) % np.pi) - np.pi / 2)
                if da > np.deg2rad(15) or abs(v[0] * u[1] - v[1] * u[0]) > 0.3 * s[i] + 1.5: continue
                row[i] = True; break
            else:
                sides.add((round(np.arctan2(v[1], v[0]) / (np.pi / 6)) % 12, j))
        if not el and not row[i] and len(sides) >= 2:
            angs = np.array([k for k, _ in sides]) * np.pi / 6
            for p in range(len(angs)):
                for q in range(p + 1, len(angs)):
                    if np.cos(angs[p] - angs[q]) < -0.95: row[i] = True
    return row


def spaced_caps(G, lone, h_of):
    """widely spaced capitals: three or more lone glyphs of one size, evenly spaced on a straight line, gaps up to
    SPACED['reach'] heights. Returns lists of glyph indices in order"""
    idx = np.array([g for g in lone if G['s'][g] >= SPACED['min_s']], int)
    if len(idx) < 3: return []
    c = G['c'][idx]; s = G['s'][idx]; tree = cKDTree(c)
    nb = [[] for _ in idx]
    for i, js in enumerate(tree.query_ball_point(c, SPACED['reach'] * s + s)):
        for j in js:
            if j != i and max(s[i], s[j]) / min(s[i], s[j]) <= SPACED['size']: nb[i].append(j)
    links = set(); ca = np.cos(np.deg2rad(180 - SPACED['ang']))
    for i in range(len(idx)):
        best = None
        for a in range(len(nb[i])):
            for b in range(a + 1, len(nb[i])):
                j, k = nb[i][a], nb[i][b]; v1 = c[j] - c[i]; v2 = c[k] - c[i]; d1, d2 = np.hypot(*v1), np.hypot(*v2)
                if (v1 @ v2) / (d1 * d2) > ca: continue
                if max(d1, d2) / min(d1, d2) > SPACED['even']: continue
                cost = d1 + d2
                if best is None or cost < best[0]: best = (cost, j, k)
        if best: links.add(tuple(sorted((i, best[1])))); links.add(tuple(sorted((i, best[2]))))
    adj = [[] for _ in idx]
    for i, j in links: adj[i].append(j); adj[j].append(i)
    seen = np.zeros(len(idx), bool); out = []
    for s0 in range(len(idx)):
        if seen[s0] or not adj[s0]: continue
        comp = [s0]; seen[s0] = True; k = 0
        while k < len(comp):
            for b in adj[comp[k]]:
                if not seen[b]: seen[b] = True; comp.append(b)
            k += 1
        if len(comp) < 3: continue
        P = c[comp]; m, d = wl.fit_line(P); r = np.abs((P - m) @ np.array([-d[1], d[0]]))
        if r.max() > SPACED['perp'] * np.median(s[comp]) + 3: continue          # not one straight line
        order = np.argsort((P - m) @ d); gs = idx[np.array(comp)[order]]
        sp = np.hypot(*np.diff(c[np.array(comp)[order]], axis=0).T)
        if sp.max() / sp.min() > SPACED['even']: continue                      # not evenly spaced
        # the line must run across the letters' long sides (their heights), not along them: a column of story
        # numbers, one above the other, is evenly spaced too
        el = G['s'][gs] / np.maximum(G['t'][gs], 1) >= 1.15
        if el.sum() >= 2 and np.median(np.abs(np.cos(G['ang'][gs][el] - np.arctan2(d[1], d[0])))) > SPACED['across']: continue
        out.append([int(g) for g in gs])
    return out


MERGE = dict(gap=1.7, ang=15.0, perp=0.35, size=1.4)   # joining strings across a word space (30"  W.P.,  10"  W. PIPE)


def merge_strings(G, strings, core):
    """join strings end to end across word spaces wider than the chaining allows: the next string must start within
    MERGE['gap'] heights of the end of this one, on its line (MERGE['perp'] heights off it), run the same way
    (MERGE['ang'] degrees), and be of the same height (MERGE['size']). A lone core glyph may be joined too (a word of one
    character). Greedy, smallest gap first; each string end takes one partner."""
    S, c = G['S'], G['c']
    units = [list(s) for s in strings]
    nU = len(units)
    mp = (G['s'] / np.maximum(G['t'], 1) >= MULTI) & (G['t'] >= 12)   # one piece of several touching characters
    def ends(s):
        """for each end (0 first, 1 last): glyph, outward unit direction (None for a lone one-character glyph), height"""
        if len(s) == 1 and mp[s[0]]:
            d = np.array([np.cos(G['ang'][s[0]]), np.sin(G['ang'][s[0]])])
            if d[0] < 0: d = -d
            return [(s[0], -d), (s[0], d)]
        if len(s) == 1: return [(s[0], None), (s[0], None)]
        P = c[s]; m, d = wl.fit_line(P)
        if (P[-1] - P[0]) @ d < 0: d = -d
        return [(s[0], -d), (s[-1], d)]
    def hgt(s, d):
        a = np.arctan2(d[1], d[0]); return float(np.median([S[g, wl.kidx(a + np.pi / 2)] + S[g, wl.kidx(a - np.pi / 2)] for g in s]))
    E = [ends(s) for s in units]
    H = [hgt(s, E[i][1][1]) if E[i][1][1] is not None else None for i, s in enumerate(units)]
    ok_u = [len(s) >= 2 or core[s[0]] for s in units]
    ept = np.array([c[E[i][k][0]] for i in range(nU) for k in (0, 1)]); tree = cKDTree(ept)
    cand = []
    ca = np.cos(np.deg2rad(MERGE['ang']))
    for i in range(nU):
        if H[i] is None: continue
        hA = H[i]
        for k in (0, 1):
            gA, dA = E[i][k]
            for q in tree.query_ball_point(c[gA], (MERGE['gap'] + 1.5) * hA):
                j, kb = divmod(q, 2)
                if j == i or not ok_u[j]: continue
                gB, dB = E[j][kb]
                v = c[gB] - c[gA]; L = np.hypot(*v)
                if L < 1: continue
                u = v / L
                if u @ dA < ca: continue                               # B lies ahead of A's end, on its line
                if abs(v[0] * dA[1] - v[1] * dA[0]) > MERGE['perp'] * hA: continue
                if dB is not None and (-dB) @ dA < ca: continue        # B runs the same way, starting at this end
                a = np.arctan2(dA[1], dA[0])
                hB = H[j] if dB is not None else S[gB, wl.kidx(a + np.pi / 2)] + S[gB, wl.kidx(a - np.pi / 2)]
                if max(hA, hB) / max(min(hA, hB), 1e-6) > MERGE['size']: continue
                gap = L - S[gA, wl.kidx(a)] - S[gB, wl.kidx(a + np.pi)]
                if gap > MERGE['gap'] * hA or gap < -0.2 * hA: continue
                cand.append((gap / hA, i, k, j, kb, u))
    cand.sort(key=lambda x: x[0])
    taken = {}; lone_dir = {}
    for gq, i, k, j, kb, u in cand:
        if (i, k) in taken: continue
        if E[j][0][1] is None:
            # a lone glyph has two free sides: the second join must leave it the opposite way
            if j in lone_dir:
                if len(lone_dir[j]) >= 2 or (u @ lone_dir[j][0]) > -ca: continue   # u points into j; the first join's u too
                kb = 1 - taken_side(taken, j)
            else: kb = 0
        if (j, kb) in taken: continue
        taken[(i, k)] = (j, kb); taken[(j, kb)] = (i, k)
        if E[j][0][1] is None: lone_dir.setdefault(j, []).append(u)
    # walk the joined units into phrases
    seen = set(); out = []
    for i in range(nU):
        if i in seen: continue
        # find a free end of i's group: walk backwards from end 0
        cur, k = i, 0; guard = 0
        while (cur, k) in taken and guard < nU:
            j, kb = taken[(cur, k)]; cur, k = j, 1 - kb; guard += 1
            if cur == i: break
        start, kin = cur, k                                    # (unit, the end that is free): read from it
        seq = []; cur, k = start, kin; guard = 0
        while guard <= nU:
            if cur in seen: break
            seen.add(cur); s = units[cur]
            seq += (s if k == 0 else s[::-1])
            out_end = 1 - k
            if (cur, out_end) not in taken: break
            cur, k = taken[(cur, out_end)]; guard += 1
        if seq: out.append(seq)
    return out


def taken_side(taken, j):
    return 0 if (j, 0) in taken else 1


def build(N, mask, fill_at=None):
    t0 = time.time()
    G = wl.glyphs(mask)
    n = G['n']; S = G['S']
    # building outline rings and their pieces: big and thin-stroked with little ink for their hull (a small building on a
    # 200 ft plate is a 40 px square of 2 px line); letters this big are drawn with 4 px strokes or more
    ring = ((G['sol'] < wl.P['ring']) & (G['s'] > 40)) | ((G['s'] > 35) & (G['sol'] < 0.32) & (G['sw'] < 3.4))
    core = (G['s'] >= 9) & (G['A'] >= 20) & ~ring
    strings, dirv = wl.chain(G, core)
    strings = merge_strings(G, strings, core)
    lone = [s[0] for s in strings if len(s) == 1]
    sp = spaced_caps(G, lone, None)
    sp_set = {g for s in sp for g in s}
    strings = [s for s in strings if not (len(s) == 1 and s[0] in sp_set)] + sp
    spaced_ids = set(range(len(strings) - len(sp), len(strings)))
    info = []
    in_multi = np.zeros(n, bool)
    for s in strings:
        if len(s) >= 2: in_multi[s] = True
    for sid, s in enumerate(strings):
        pts = G['c'][s]
        if len(s) >= 2:
            hs = []
            for k, g in enumerate(s):
                a, b = s[max(0, k - 1)], s[min(len(s) - 1, k + 1)]
                tg = G['c'][b] - G['c'][a]; tg = tg / max(np.hypot(*tg), 1e-6)
                an = np.arctan2(tg[1], tg[0])
                hs.append(S[g, wl.kidx(an + np.pi / 2)] + S[g, wl.kidx(an - np.pi / 2)])
            h = float(np.median(hs))
            Q, kind, rms, rms_line = wl.centre_curve(pts, h)
        else:
            g = s[0]
            # several touching characters (285): read along the long side. 25 Nov: 1.5 took single tall digits (a 7, a 3:
            # 1.6-1.9) for runs and turned them sideways (seen on plate 1A's audit sheet); three touching digits are about 1.8-2
            if G['s'][g] / G['t'][g] >= MULTI and G['t'][g] >= 12:
                ang = G['ang'][g]; h = float(G['t'][g]); I_multi = True
            else:                                                   # one character: its long side is its height, reading across it
                ang = G['ang'][g] + np.pi / 2; h = float(G['s'][g]); I_multi = False
            d = np.array([np.cos(ang), np.sin(ang)])
            if I_multi:
                if d[0] < 0: d = -d
                hl = max(G['s'][g] / 2 - G['t'][g] / 3, 1.0); Q = np.vstack([pts[0] - d * hl, pts[0] + d * hl]); kind = 'single'; rms = rms_line = 0.0
            else: Q = np.vstack([pts[0] - d * 0.5, pts[0] + d * 0.5]); kind = 'single'; rms = rms_line = 0.0
        info.append(dict(g=list(map(int, s)), h=h, Q=Q, kind=kind, rms=rms, rms_line=rms_line, spaced=sid in spaced_ids, marks=[],
                         d0=(d if len(s) == 1 else None), multi_piece=(I_multi if len(s) == 1 else False)))
    # marks: small pieces outside every multi-glyph string, not one of a row of like pieces
    cand = np.nonzero(~in_multi & ~ring & (G['s'] >= 3))[0]
    cand = cand[~in_rows(G, cand)]
    tree = cKDTree(G['c'][cand]) if len(cand) else None
    owner = np.full(n, -1); best = np.full(n, np.inf); rel = {}
    for sid, I in enumerate(info):
        s = I['g']
        if (len(s) < 2 and not I['multi_piece']) or tree is None or I['spaced']: continue
        h = I['h']; pts = G['c'][s] if len(s) >= 2 else I['Q']
        Qs = wl.resample(I['Q'], 2.0)
        near = set()
        for q in Qs[::max(1, int(h // 4))]:
            near.update(tree.query_ball_point(q, (wl.P['mark_reach'] + 0.6) * h))
        if not near: continue
        qt = cKDTree(Qs)
        _, gi = qt.query(pts); a0, a1 = gi.min(), gi.max()
        T = np.gradient(Qs, axis=0); T /= np.maximum(np.hypot(*T.T), 1e-6)[:, None]
        for k in near:
            g = cand[k]
            if g in s or G['s'][g] >= wl.P['mark'] * h: continue
            dq, qi = qt.query(G['c'][g])
            tg = T[qi]; up = np.array([tg[1], -tg[0]])
            off = (G['c'][g] - Qs[qi]) @ up
            if abs(off) > wl.P['mark_band'] * h: continue
            past = 0.0
            if qi <= a0: past = (a0 - qi) * 2.0 - 0.5 * G['s'][s[0]]
            elif qi >= a1: past = (qi - a1) * 2.0 - 0.5 * G['s'][s[-1]]
            if past > wl.P['mark_reach'] * h: continue
            place = 'high' if off > 0.22 * h else ('low' if off < -0.22 * h else 'mid')
            inside = a0 < qi < a1
            al = abs(np.cos(G['ang'][g] - np.arctan2(tg[1], tg[0])))   # 1: the mark's long side runs along the string
            if place == 'mid' and not inside:
                if al < 0.85 or G['s'][g] / max(G['t'][g], 1) < 1.8: continue      # only a dash along the string at its end
            score = abs(off) / h + max(past, 0) / h
            if score < best[g]: best[g] = score; owner[g] = sid; rel[g] = (off, qi, a0, a1, place, inside, al)
    for g in np.nonzero(owner >= 0)[0]:
        sid = owner[g]; I = info[sid]; off, qi, a0, a1, place, inside, al = rel[g]
        pos = 'inside' if inside else ('before' if qi <= a0 else 'after')
        I['marks'].append(dict(g=int(g), off=round(float(off / I['h']), 3), place=place, pos=pos, at=int(qi) * 2,
                               s=round(float(G['s'][g]), 1), t=round(float(G['t'][g]), 1), along=round(float(al), 2)))
    taken = owner >= 0
    info = [I for I in info if not (len(I['g']) == 1 and taken[I['g'][0]])]
    # words: split a phrase where the gap is wide, unless a joining mark sits mid-gap
    for I in info:
        s = I['g']; h = I['h']
        if len(s) < 2: I['words'] = [[0, 1]]; I['gaps'] = []; continue
        f = wl.pair_feats(G, np.array(s[:-1]), np.array(s[1:])); gaps = f['gap']
        Qs = wl.resample(I['Q'], 2.0); qt = cKDTree(Qs); _, gi = qt.query(G['c'][s]); gi = gi * 2
        cuts = []
        for k in range(len(s) - 1):
            if gaps[k] <= WORD_GAP * h: continue
            lo, hi = sorted((gi[k], gi[k + 1])); mid = (lo + hi) / 2
            join = gaps[k] <= JOIN_GAP * h and any(m['place'] in ('mid', 'low') and abs(m['at'] - mid) <= 0.3 * (hi - lo) + 2 for m in I['marks'])
            if not join: cuts.append(k + 1)
        if fill_at is not None:                   # a story count in a building beside a lot number outside it
            fl = fill_at(G['c'][s][:, 0], G['c'][s][:, 1])
            for k in range(len(s) - 1):
                if fl[k] != fl[k + 1] and gaps[k] > 0.15 * h and (k + 1) not in cuts: cuts.append(k + 1)
            cuts.sort()
        b = [0] + cuts + [len(s)]
        I['words'] = [[b[i], b[i + 1]] for i in range(len(b) - 1)]
        I['gaps'] = [round(float(g / h), 3) for g in gaps]
    return G, info, ring, time.time() - t0


def main():
    N = sys.argv[1]; src = arg('--src', 'bins')
    mask, mf = load_candidates(N, src)
    G, info, ring, dt = build(N, mask)
    ns = np.array([len(I['g']) for I in info])
    print(f'plate {N}: {G["n"]} glyphs, {len(info)} strings ({(ns >= 2).sum()} of 2+ glyphs, {(ns == 1).sum()} lone, '
          f'{sum(I["spaced"] for I in info)} spaced capitals), {sum(len(I["words"]) for I in info if len(I["g"]) >= 2)} words in the multi-glyph strings, '
          f'{sum(len(I["marks"]) for I in info)} marks attached, {int(ring.sum())} ring pieces left out, {dt:.1f} s')


if __name__ == '__main__':
    main()
