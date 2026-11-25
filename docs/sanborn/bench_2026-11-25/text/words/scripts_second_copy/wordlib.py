"""Grouping character candidates into strings (words and numbers) at any angle, along a curve too, with no OCR engine.

Written 25 Nov 2026 for Ben's text-first stage (words agent). Prototype: rules only, nothing trained, nothing downloaded.

A 'glyph' is one connected piece of candidate ink (ink_bins bin 8, or the finder's mask). A 'string' is a chain of
glyphs of one size that follow one another along a common centre line. The chain is built from each glyph's two
neighbours on opposite sides (its 'through pair'), so the line may turn a little at every glyph and follow a curved
street. Small marks (apostrophes, ditto marks, periods, hyphens) are kept out of the chaining and attached afterwards,
with their place (high, low, middle) recorded, because they tell a lot dimension (25', 18.72) from a house number.

Every size is in scan pixels (about 300 dpi)."""
import numpy as np
import cv2
from scipy.spatial import cKDTree

K = 72                                                     # directions of the support-function table (5 degrees apart)
ANG = 2 * np.pi * np.arange(K) / K
DIRS = np.stack([np.cos(ANG), np.sin(ANG)], 1)

P = dict(min_area=6,          # smaller pieces are dropped (noise)
         min_h=7.0,           # a glyph whose height across the link is under this cannot be a chained character
         ratio=1.8,           # heights of two chained glyphs within this factor
         gap=1.15,            # edge-to-edge gap between chained glyphs at most this times the taller height
         align=0.42,          # tops and bottoms of the two glyphs within this times the height (a common centre band)
         through=25.0,        # a through pair: the two links within this many degrees of opposite
         keep=20.0,           # a link is kept if within this many degrees of both glyphs' own directions
         turn=40.0,           # a chain is cut where it turns more than this between one link and the next
         mark=0.55,           # a piece shorter (long side) than this times a string's height is a mark, not a character
         mark_reach=0.9,      # a mark attaches within this times h beyond a string's ends
         mark_band=0.85,      # ... and within this times h of its centre line
         asp=1.35,            # mean width / height of two chained glyphs at most this (digits and capitals are taller than wide;
                              # two digits stacked one above the other are wider than tall across the link between them)
         ring=0.2)            # a piece with solidity under this and long side over 40 px is a building outline ring, not a glyph      # ... and within this times h of its centre line


def kidx(a):
    return np.round(np.asarray(a) / (2 * np.pi / K)).astype(int) % K


def glyphs(mask, min_area=None):
    """the connected pieces of mask as glyph records (arrays). Returns dict with
    lab (label image), n, c (centroid), A (area), box (x, y, w, h), S (support function, n x K), s (long side), t (short
    side) and ang (angle of the long side) of the minimum-area rectangle, hull (list of hull point arrays)"""
    min_area = P['min_area'] if min_area is None else min_area
    m8 = mask.astype(np.uint8)
    n, lab, st, cen = cv2.connectedComponentsWithStats(m8, connectivity=8)
    cs, hier = cv2.findContours(m8, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    hull = [None] * n
    for k, c in enumerate(cs):
        if hier[0][k][3] != -1: continue                       # a hole's boundary
        p = c[0, 0]; l = lab[p[1], p[0]]
        if l == 0: continue
        h = cv2.convexHull(c).reshape(-1, 2)
        if hull[l] is None or len(h) > len(hull[l]): hull[l] = h
    keep = [l for l in range(1, n) if st[l, 4] >= min_area and hull[l] is not None]
    keep = np.array(keep, int)
    remap = np.zeros(n, np.int32); remap[keep] = np.arange(1, len(keep) + 1)
    lab2 = remap[lab]
    c = cen[keep].astype(float); A = st[keep, 4].astype(float); box = st[keep, :4]
    H = [hull[l].astype(float) for l in keep]
    idx = np.repeat(np.arange(len(keep)), [len(h) for h in H]); pts = np.vstack(H) if H else np.zeros((0, 2))
    D = (pts - c[idx]) @ DIRS.T
    starts = np.r_[0, np.cumsum([len(h) for h in H])[:-1]]
    S = np.maximum.reduceat(D, starts, axis=0) if len(H) else np.zeros((0, K))
    S = np.maximum(S, 0.5)
    s = np.zeros(len(keep)); t = np.zeros(len(keep)); ang = np.zeros(len(keep))
    for i, h in enumerate(H):
        (_, _), (w_, h_), a = cv2.minAreaRect(h.astype(np.float32))
        if w_ >= h_: s[i], t[i], ang[i] = w_ + 1, h_ + 1, np.deg2rad(a)
        else: s[i], t[i], ang[i] = h_ + 1, w_ + 1, np.deg2rad(a + 90)
    harea = np.array([max(cv2.contourArea(h.astype(np.float32)), 1.0) for h in H])
    sol = A / np.maximum(harea, A)                          # solidity: ink over hull area (a building outline is a thin ring: low)
    per = np.zeros(n); 
    for k, c_ in enumerate(cs):                             # outer contour length of each piece
        if hier[0][k][3] != -1: continue
        p = c_[0, 0]; l = lab[p[1], p[0]]
        if l: per[l] = max(per[l], cv2.arcLength(c_, True))
    sw = 2 * A / np.maximum(per[keep], 1.0)                 # stroke width, roughly (area over half the outline)
    return dict(lab=lab2, n=len(keep), c=c, A=A, box=box, S=S, s=s, t=t, ang=ang, hull=H, sol=sol, sw=sw)


def pair_feats(G, I, J):
    """features of the links I->J (arrays): unit vector, length, gap, heights across, alignment of tops and bottoms"""
    c, S = G['c'], G['S']
    v = c[J] - c[I]; d = np.hypot(*v.T); d = np.maximum(d, 1e-6); u = v / d[:, None]
    a = np.arctan2(u[:, 1], u[:, 0])
    kf, kb, kn, km = kidx(a), kidx(a + np.pi), kidx(a + np.pi / 2), kidx(a - np.pi / 2)
    gap = d - S[I, kf] - S[J, kb]
    ti, bi = S[I, kn], S[I, km]; tj, bj = S[J, kn], S[J, km]
    pi, pj = ti + bi, tj + bj
    wi, wj = S[I, kf] + S[I, kb], S[J, kf] + S[J, kb]      # widths along the link
    asp = (wi / np.maximum(pi, 1e-6) + wj / np.maximum(pj, 1e-6)) / 2
    h = np.maximum(pi, pj); ratio = h / np.maximum(np.minimum(pi, pj), 1e-6)
    mis = np.maximum(np.abs(ti - tj), np.abs(bi - bj)) / h
    return dict(u=u, d=d, gap=gap, pi=pi, pj=pj, h=h, ratio=ratio, mis=mis, asp=asp)


def candidate_links(G, core):
    """every plausible neighbour pair among the core glyphs (indices into G)"""
    ci = np.nonzero(core)[0]
    if len(ci) < 2: return np.zeros((0, 2), int), {}
    tree = cKDTree(G['c'][ci])
    r = (1.0 + P['gap']) * G['s'][ci] + 6
    L = tree.query_ball_point(G['c'][ci], r)
    I = np.repeat(np.arange(len(ci)), [len(x) for x in L]); J = np.concatenate([np.array(x, int) for x in L]) if len(L) else np.zeros(0, int)
    ok = I != J; I, J = ci[I[ok]], ci[J[ok]]
    E = np.unique(np.sort(np.c_[I, J], 1), axis=0)
    f = pair_feats(G, E[:, 0], E[:, 1])
    # tried 25 Nov: heights within 2.1 when the two share a top or bottom, and overlap to -0.5 h: worse on T1 (exact 131 -> 123)
    good = (f['h'] >= P['min_h']) & (f['ratio'] <= P['ratio']) & (f['gap'] <= P['gap'] * f['h']) & (f['gap'] >= -0.35 * f['h']) & (f['mis'] <= P['align']) & (f['asp'] <= P['asp'])
    E = E[good]; f = {k: v[good] for k, v in f.items()}
    return E, f


def chain(G, core):
    """strings of core glyphs: lists of glyph indices in order along the string"""
    E, f = candidate_links(G, core)
    n = G['n']
    nb = [[] for _ in range(n)]                     # (other, unit vector from me to other, gap, height)
    for e, (i, j) in enumerate(E):
        nb[i].append((j, f['u'][e], f['gap'][e], f['h'][e]))
        nb[j].append((i, -f['u'][e], f['gap'][e], f['h'][e]))
    dirv = np.zeros((n, 2)); has = np.zeros(n, bool); thr = np.zeros(n, bool)
    cth = -np.cos(np.deg2rad(P['through']))
    for i in range(n):                              # the best through pair
        L = nb[i]; best = None
        for a in range(len(L)):
            for b in range(a + 1, len(L)):
                dot = L[a][1] @ L[b][1]
                if dot > cth: continue
                h = max(L[a][3], L[b][3])
                cost = (max(L[a][2], 0) + max(L[b][2], 0)) / h + 3 * (1 + dot)
                if best is None or cost < best[0]: best = (cost, L[a][1] - L[b][1])
        if best is not None:
            dirv[i] = best[1] / np.hypot(*best[1]); has[i] = thr[i] = True
    for i in range(n):                              # a string's end glyph: the link that best agrees with its neighbour's own line
        if has[i] or not nb[i]: continue
        best = None
        for j, u, g, h in nb[i]:
            agree = abs(u @ dirv[j]) if thr[j] else 0.7
            cost = max(g, 0) / h + 2 * (1 - agree)
            if best is None or cost < best[0]: best = (cost, u)
        dirv[i] = best[1]; has[i] = True
    ck = np.cos(np.deg2rad(P['keep']))
    side = {}                                       # (glyph, side) -> (gap, other)
    for e, (i, j) in enumerate(E):
        u = f['u'][e]
        if not (has[i] and has[j]): continue
        if abs(u @ dirv[i]) < ck or abs(u @ dirv[j]) < ck: continue
        for a, b, w in ((i, j, u), (j, i, -u)):
            sd = (a, int(np.sign(w @ dirv[a]) or 1)); g = f['gap'][e]
            if sd not in side or g < side[sd][0]: side[sd] = (g, b)
    adj = [[] for _ in range(n)]
    for (a, sd), (g, b) in side.items():
        # kept if b also keeps a on one of its sides
        if any(side.get((b, s2), (0, -1))[1] == a for s2 in (-1, 1)):
            if b not in adj[a]: adj[a].append(b)
    # paths: every glyph has at most one neighbour per side, so the graph is paths (and rare cycles: break them)
    seen = np.zeros(n, bool); out = []
    for s0 in range(n):
        if seen[s0] or not core[s0]: continue
        comp = [s0]; seen[s0] = True; k = 0
        while k < len(comp):
            for b in adj[comp[k]]:
                if not seen[b]: seen[b] = True; comp.append(b)
            k += 1
        ends = [x for x in comp if len(adj[x]) <= 1]
        start = ends[0] if ends else comp[0]
        order = [start]; prev = -1; cur = start; vis = {start}
        while True:
            nxt = [b for b in adj[cur] if b != prev and b not in vis]
            if not nxt: break
            prev, cur = cur, nxt[0]; order.append(cur); vis.add(cur)
        rest = [x for x in comp if x not in vis]    # a branch left over (should be rare): its own strings, one glyph each
        if len(order) >= 3:                         # cut where the chain turns sharply (text along a curve turns a little at each glyph)
            V = np.diff(G['c'][order], axis=0); V /= np.maximum(np.hypot(*V.T), 1e-6)[:, None]
            cos = (V[:-1] * V[1:]).sum(1); cut = [k + 1 for k in np.nonzero(cos < np.cos(np.deg2rad(P['turn'])))[0]]
            # cut at the longer of the two links meeting at the sharp turn
            pieces = []; b0 = 0
            for k in cut:
                g1 = np.hypot(*(G['c'][order[k]] - G['c'][order[k - 1]])); g2 = np.hypot(*(G['c'][order[k + 1]] - G['c'][order[k]]))
                at = k if g1 >= g2 else k + 1
                if at > b0: pieces.append(order[b0:at]); b0 = at
            pieces.append(order[b0:])
            out += [p for p in pieces if p]
        else:
            out.append(order)
        out += [[x] for x in rest]
    return out, dirv


def fit_line(pts):
    m = pts.mean(0)
    if len(pts) == 1: return m, np.array([1.0, 0.0])
    w, v = np.linalg.eigh(np.cov((pts - m).T)); d = v[:, -1]
    return m, d / np.hypot(*d)


def centre_curve(pts, h):
    """a smooth centre line through the glyph centres: a straight line for short or straight strings, else a quadratic
    (or cubic, for long strings) in chord length. Returns (n x 2 dense points spaced 1 px, kind, rms residual / h)"""
    n = len(pts)
    m, d = fit_line(pts)
    if n >= 2:
        t = (pts - m) @ d; r = (pts - m) @ np.array([-d[1], d[0]])
        rms_line = float(np.sqrt(np.mean(r ** 2))) / max(h, 1)
        if np.dot(pts[-1] - pts[0], d) < 0: d = -d
    else:
        rms_line = 0.0
    kind = 'line'
    if n >= 5 and rms_line > 0.12:
        s = np.r_[0, np.cumsum(np.hypot(*np.diff(pts, axis=0).T))]
        deg = 3 if n >= 9 else 2
        cx = np.polyfit(s, pts[:, 0], deg); cy = np.polyfit(s, pts[:, 1], deg)
        ss = np.linspace(s[0], s[-1], max(2, int(s[-1]) + 1))
        Q = np.c_[np.polyval(cx, ss), np.polyval(cy, ss)]
        res = np.hypot(np.polyval(cx, s) - pts[:, 0], np.polyval(cy, s) - pts[:, 1])
        kind = 'curve'; rms = float(np.sqrt(np.mean(res ** 2))) / max(h, 1)
    else:
        t = (pts - m) @ d
        ss = np.linspace(t.min(), t.max(), max(2, int(t.max() - t.min()) + 1))
        Q = m[None] + ss[:, None] * d[None]
        rms = rms_line
    return Q, kind, rms, rms_line


def resample(Q, step=1.0):
    s = np.r_[0, np.cumsum(np.hypot(*np.diff(Q, axis=0).T))]
    if s[-1] < 1e-6: return Q[:1]
    t = np.arange(0, s[-1] + 1e-6, step)
    return np.c_[np.interp(t, s, Q[:, 0]), np.interp(t, s, Q[:, 1])]


def strip_maps(Q, h, head, tail, up_sign=1.0, half=None):
    """sampling maps for a strip along the centre line Q (reading order), extended by head / tail px at the ends.
    Row 0 of the strip is the text's top"""
    Q = resample(Q)
    if len(Q) < 2:
        Q = np.vstack([Q[0] - [0.5, 0], Q[0] + [0.5, 0]])
    t0 = Q[1] - Q[0]; t0 /= np.hypot(*t0); t1 = Q[-1] - Q[-2]; t1 /= np.hypot(*t1)
    pre = Q[0][None] - np.arange(int(head), 0, -1)[:, None] * t0[None]
    post = Q[-1][None] + np.arange(1, int(tail) + 1)[:, None] * t1[None]
    Q = np.vstack([pre, Q, post])
    T = np.gradient(Q, axis=0)
    k = max(1, int(h // 3))
    if len(T) > 2 * k + 1:                          # smooth the tangent over about a third of a character
        ker = np.ones(2 * k + 1) / (2 * k + 1)
        T = np.c_[np.convolve(np.pad(T[:, 0], k, mode='edge'), ker, 'valid'), np.convolve(np.pad(T[:, 1], k, mode='edge'), ker, 'valid')]
    T /= np.maximum(np.hypot(*T.T), 1e-6)[:, None]
    up = np.c_[T[:, 1], -T[:, 0]] * up_sign
    half = half or 0.85 * h
    v = np.arange(half, -half - 1e-6, -1.0)
    mx = (Q[None, :, 0] + v[:, None] * up[None, :, 0]).astype(np.float32)
    my = (Q[None, :, 1] + v[:, None] * up[None, :, 1]).astype(np.float32)
    return mx, my, Q, T, up
