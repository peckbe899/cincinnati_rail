"""Proposed changes to the rail tracing, as functions to try against the benchmark (bench_2026-11-21/rail).
Nothing here writes anywhere; the experiment scripts call these.

streetcar_tracks_v2   rail_tracks.streetcar_tracks with its settings exposed, plus two proposed changes:
                      single=S   a lone piece of S px or more is a track by itself (rail-10; S above dash length, 250)
                      curved=True a piece longer than 250 px that bends more than 6 px off its chord is traced along its
                                  centre line (skeleton) instead of the straight chord, and joined by its end directions
drop_lone_short       railroad tracks shorter than `short` px with no other railroad track within `near` px anywhere
                      along them are dropped (the lot-line hook rows: short, straight and alone)
drop_in_box           tracks with more than half their points inside a box (the printed KEY)"""
import numpy as np, cv2
from scipy.spatial import cKDTree
import rail_tracks_copy as rt


def _piece_path(mask_crop, x, y):
    """the longest path of a piece's centre line, as (x, y) points in plate px"""
    sk = rt.thin(mask_crop)
    G = rt.graph(sk)
    if not G: return None
    # longest single branch is enough for a dash or a curved run of touching dashes
    p = max((g[0] for g in G), key=len)
    return np.array(p, float) + [x, y]


def streetcar_tracks_v2(m, reach=150, ang=25, across=18, short=150, single=None, curved=False, minpx=150):
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)); n, lb, st, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
    D = []   # pieces: (end a, end b, direction at a pointing out, direction at b pointing out, path a->b)
    for i in range(1, n):
        if st[i, 4] < minpx: continue
        x, y, w, h = st[i, :4]; crop = (lb[y:y + h, x:x + w] == i); ys, xs = np.nonzero(crop); q = np.c_[xs + x, ys + y].astype(float); c = q.mean(0)
        d = np.linalg.svd(q - c, full_matrices=False)[2][0]; t = (q - c) @ d; a, b = c + t.min() * d, c + t.max() * d
        path = np.array([a, b])
        if curved and (t.max() - t.min()) > 250:
            off = np.abs((q - c) @ np.array([-d[1], d[0]]))
            if np.percentile(off, 95) > 6 + np.percentile(off, 50):   # bends off its chord
                p = _piece_path(crop.astype(np.uint8), x, y)
                if p is not None and len(p) >= 10: path = p
        if len(path) > 2:
            k = min(len(path) - 1, 15); da = path[0] - path[k]; db = path[-1] - path[-1 - k]
            D.append((path[0], path[-1], da / max(1e-6, np.hypot(*da)), db / max(1e-6, np.hypot(*db)), path))
        else:
            D.append((a, b, -d, d, path))
    if not D: return []
    E = np.array([e for a, b, _, _, _ in D for e in (a, b)]); O = np.array([o for _, _, oa, ob, _ in D for o in (oa, ob)]); cosa = np.cos(np.radians(ang)); best = {}
    if len(D) >= 2:
        for k, js in enumerate(cKDTree(E).query_ball_point(E, reach)):
            for j in js:
                if j // 2 == k // 2: continue
                v = E[j] - E[k]; L = np.hypot(*v)
                if np.hypot(*(E[j ^ 1] - E[k])) < L: continue
                if -(O[k] @ O[j]) < cosa: continue                          # the two ends must face each other (out-directions opposite)
                if L > 10 and ((v @ O[k]) / L < cosa or abs(v[0] * O[k][1] - v[1] * O[k][0]) > across): continue
                if k not in best or L < best[k][0]: best[k] = (L, j)
    link = {k: j for k, (L, j) in best.items() if best.get(j, (0, -1))[1] == k}; used = set(); out = []
    for s in range(len(E)):
        if s in link or s // 2 in used: continue
        pts = []; k = s; npc = 0
        while True:
            used.add(k // 2); npc += 1; P = D[k // 2][4]; pts += list(P if k % 2 == 0 else P[::-1]); j = link.get(k ^ 1)
            if j is None or j // 2 in used: break
            k = j
        p = np.array(pts)
        if (npc >= 2 and rt.plen(p) >= short) or (single is not None and rt.plen(p) >= single):
            out.append(cv2.approxPolyDP(p.astype(np.float32)[:, None, :], 2.5, False)[:, 0, :].astype(float))
    return out


def drop_lone_short(tracks, short=600, near=60, anchor=0):
    """anchor: only railroad tracks at least this long count as 'another track' (F1b: anchor=600)"""
    rr = [np.asarray(t['pts'], float) for t in tracks if t['kind'] == 'railroad']
    S = []
    for p in rr:
        s = [p[0][None]]
        for a, b in zip(p[:-1], p[1:]):
            L = np.hypot(*(b - a)); s.append(a[None] + np.linspace(0, 1, max(2, int(L / 5) + 1))[:, None] * (b - a)[None])
        S.append(np.vstack(s))
    keep = []; dropped = []; ri = 0
    for t in tracks:
        if t['kind'] != 'railroad': keep.append(t); continue
        i = ri; ri += 1; L = rt.plen(rr[i])
        if L >= short: keep.append(t); continue
        others = [S[j] for j in range(len(S)) if j != i and rt.plen(rr[j]) >= anchor]
        dmin = cKDTree(np.vstack(others)).query(S[i])[0].min() if others else 1e9
        (keep if dmin <= near else dropped).append(t)
    return keep, dropped


def drop_in_box(tracks, box):
    x0, y0, x1, y1 = box; keep = []; dropped = []
    for t in tracks:
        p = np.asarray(t['pts']); f = ((p[:, 0] >= x0) & (p[:, 0] < x1) & (p[:, 1] >= y0) & (p[:, 1] < y1)).mean()
        (dropped if f > 0.5 else keep).append(t)
    return keep, dropped
