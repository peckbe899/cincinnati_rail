"""Stage contours, step 2: join fragments into contour lines and mark index contours by local stroke weight.

Fragments break where a contour crosses a black street line, a label or a junction. Two ends are joined when they
are close (gap <= MAX_GAP px), point the same way (angle <= MAX_ANG), and the gap runs along both lines (lateral
offset <= MAX_LAT px); pairs are taken best first, each end once. A chain's stroke weight (peak x width, length
weighted) is compared with the weights of the chains around it (within LOCAL_M ground metres); index contours are
the ones clearly stronger than their neighbours, which is robust to the print getting darker or lighter across a sheet.
"""
import numpy as np
from scipy.spatial import cKDTree

MAX_GAP = 16.0      # px (about 6 m)
LONG_GAP = 60.0     # px: a longer gap is bridged only where black ink hides the contour (street lines, lettering)
LONG_ANG = 25.0     # degrees, for the long gaps
HIDDEN = 0.5        # share of a long gap that must lie under black ink
MAX_ANG = 35.0      # degrees
MAX_LAT = 3.5       # px
TAIL = 10           # px used for an end's direction


def ends(paths):
    E = []   # (seg, which_end, x, y, dx, dy) with (dx, dy) pointing out of the segment
    for k, p in enumerate(paths):
        n = len(p); t = min(TAIL, n - 1)
        for w, a, b in ((0, p[0], p[t]), (1, p[-1], p[-1 - t])):
            d = a - b; L = np.hypot(*d)
            if L < 1e-6:
                continue
            E.append((k, w, a[0], a[1], d[0] / L, d[1] / L))
    return np.array(E, float)


def hidden_share(blk, a, b):
    n = max(2, int(np.hypot(*(b - a))))
    t = np.linspace(0, 1, n)[:, None]; q = (a + (b - a) * t).astype(int)
    q[:, 0] = np.clip(q[:, 0], 0, blk.shape[1] - 1); q[:, 1] = np.clip(q[:, 1], 0, blk.shape[0] - 1)
    return blk[q[:, 1], q[:, 0]].mean()


def link(paths, blk=None, forced=()):
    """Return chains: list of [(seg, reversed)] in order. blk: black-ink mask (full res) for the long gaps.
    forced: end-index pairs (into ends(paths)) joined first, e.g. heals found by pathfinding across street lines."""
    E = ends(paths)
    if not len(E):
        return [[(k, False)] for k in range(len(paths))]
    tr = cKDTree(E[:, 2:4])
    pairs = tr.query_pairs(LONG_GAP if blk is not None else MAX_GAP, output_type='ndarray')
    cand = []
    for i, j in pairs:
        if E[i, 0] == E[j, 0]:
            continue
        gap = E[j, 2:4] - E[i, 2:4]; g = np.hypot(*gap)
        di, dj = E[i, 4:6], E[j, 4:6]
        long_ = g > MAX_GAP
        ang = LONG_ANG if long_ else MAX_ANG
        if np.dot(di, -dj) < np.cos(np.radians(ang)):   # ends must face each other
            continue
        if g > 0.5:
            u = gap / g
            if np.dot(di, u) < np.cos(np.radians(ang)) or np.dot(-dj, u) < np.cos(np.radians(ang)):
                continue
            lat = max(abs(di[0] * gap[1] - di[1] * gap[0]), abs(dj[0] * gap[1] - dj[1] * gap[0]))
            if lat > (MAX_LAT + 0.08 * g if long_ else MAX_LAT + 0.15 * g):
                continue
        if long_ and hidden_share(blk, E[i, 2:4], E[j, 2:4]) < HIDDEN:
            continue
        cost = g + 10 * (1 - np.dot(di, -dj)) + (20 if long_ else 0)
        cand.append((cost, i, j))
    cand.sort()
    cand = [(-1.0, int(i), int(j)) for i, j in forced] + cand
    used = set(); nxt = {}
    parent = list(range(len(paths)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]; a = parent[a]
        return a
    for c, i, j in cand:
        if i in used or j in used:
            continue
        a, b = int(E[i, 0]), int(E[j, 0])
        if find(a) == find(b):          # would close a loop; allowed only to close a single chain on itself later
            continue
        used.add(i); used.add(j)
        parent[find(a)] = find(b)
        nxt[(a, int(E[i, 1]))] = (b, int(E[j, 1])); nxt[(b, int(E[j, 1]))] = (a, int(E[i, 1]))
    # walk chains
    seen = set(); chains = []
    linked_end = lambda k, w: (k, w) in nxt
    for k in range(len(paths)):
        if k in seen:
            continue
        # find a start: walk backwards from k's start end
        cur, w = k, 0; guard = 0
        while linked_end(cur, w) and guard < 100000:
            cur, w2 = nxt[(cur, w)]; w = 1 - w2; guard += 1
            if cur == k:
                break
        start = (cur, w)
        chain = []; cur, w = start
        while True:
            chain.append((cur, w == 1)); seen.add(cur)
            other = 1 - w
            if not linked_end(cur, other):
                break
            cur, w = nxt[(cur, other)]
            if cur in seen:
                break
        chains.append(chain)
    return chains


def chain_xy(paths, chain):
    return np.vstack([paths[k][::-1] if rev else paths[k] for k, rev in chain])


def index_flags(chain_pts, weight, length, mpp, local_m=60.0, ratio=1.35):
    """chain_pts: per chain sample points (px); weight/length per chain. Index if weight >= ratio x the
    length-weighted median weight of chains within local_m."""
    rep = np.vstack([p[::max(1, len(p) // 20)] for p in chain_pts]); owner = np.concatenate(
        [np.full(len(p[::max(1, len(p) // 20)]), i) for i, p in enumerate(chain_pts)])
    tr = cKDTree(rep); R = local_m / mpp
    rel = np.zeros(len(chain_pts))
    for i, p in enumerate(chain_pts):
        q = p[::max(1, len(p) // 5)]
        nb = set()
        for lst in tr.query_ball_point(q, R):
            nb.update(owner[lst].tolist())
        nb.discard(i)
        nb = np.array(sorted(nb), int)
        if len(nb) < 3:
            rel[i] = np.nan; continue
        w = weight[nb]; L = length[nb]; o = np.argsort(w); cw = np.cumsum(L[o])
        med = w[o][np.searchsorted(cw, cw[-1] / 2)]
        rel[i] = weight[i] / max(med, 1e-6)
    return rel >= ratio, rel
