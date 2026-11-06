"""Block faces: which parts of each block's edge face a street (frontage), an alley, or nothing; and lot-line candidates
found on the Sanborn tiles along each street face (thin dark lines square to the street, seen at 3.5, 6 and 9 m in)."""
import math, numpy as np
from shapely.geometry import LineString, Point, Polygon
from shapely.geometry.polygon import orient
from shapely.strtree import STRtree
from scipy.ndimage import median_filter
from common import load_layers, Tiles
STEP = 1.0
class Faces:
    def __init__(s):
        s.blocks, s.streets, s.open = load_layers()
        s.main = [q for q in s.streets if not q['alley']]; s.alleys = [q for q in s.streets if q['alley']]
        s.t_main = STRtree([q['line'] for q in s.main]); s.t_alley = STRtree([q['line'] for q in s.alleys]); s.t_open = STRtree([q['g'] for q in s.open])
    def classify(s, ring):
        """ring: CCW exterior coords. Returns samples [(x, y, tx, ty, label)] every STEP m; label = street id, 'open:..', 'alley' or None"""
        L = LineString(ring); n = max(4, int(L.length / STEP)); out = []
        for i in range(n):
            d = L.length * i / n; p = L.interpolate(d); q = L.interpolate(min(L.length, d + 0.5)); r = L.interpolate(max(0, d - 0.5))
            tx, ty = q.x - r.x, q.y - r.y; m = math.hypot(tx, ty) or 1; tx, ty = tx / m, ty / m
            lab, best = None, 3.0
            for j in s.t_main.query(p.buffer(25)):
                st = s.main[j]; dd = st['line'].distance(p) - st['w'] / 2
                if dd < best: best, lab = dd, st['id']
            if lab is None:
                for j in s.t_open.query(p.buffer(4)):
                    if s.open[j]['g'].distance(p) < 3.0: lab = 'open:' + s.open[j]['id']; break
            if lab is None:
                for j in s.t_alley.query(p.buffer(12)):
                    st = s.alleys[j]
                    if st['line'].distance(p) - st['w'] / 2 < 2.5: lab = 'alley'; break
            out.append((p.x, p.y, tx, ty, lab))
        return out
    def runs(s, samples):
        """frontage runs: consecutive samples facing one street (cyclic), runs under 4 m folded into a neighbour"""
        n = len(samples); labs = [q[4] for q in samples]
        if not any(l and l != 'alley' for l in labs): return []
        # start at a label change so the cyclic run does not wrap
        k0 = next((i for i in range(n) if labs[i] != labs[i - 1]), 0)
        seq = labs[k0:] + labs[:k0]; pts = samples[k0:] + samples[:k0]
        groups = []
        for i, l in enumerate(seq):
            if groups and groups[-1][0] == l: groups[-1][1].append(i)
            else: groups.append([l, [i]])
        changed = True
        while changed and len(groups) > 1:
            changed = False
            for gi, g in enumerate(groups):
                if len(g[1]) * STEP < 4.0:
                    nb = groups[gi - 1] if gi > 0 else groups[gi + 1]
                    if gi > 0: groups[gi - 1][1].extend(g[1])
                    else: groups[gi + 1][1][:0] = g[1]
                    groups.pop(gi); changed = True; break
            merged = []
            for g in groups:
                if merged and merged[-1][0] == g[0]: merged[-1][1].extend(g[1])
                else: merged.append(g)
            groups = merged
        out = []
        for l, idx in groups:
            if not l or l == 'alley': continue
            c = [pts[i][:2] for i in idx]
            if len(c) >= 2: out.append(dict(street=l, pts=c))
        return out
def scan(tiles, run, depths=(3.5, 6.0, 9.0), step=0.25):
    """lot-line candidates along a run (positions in metres from its start); also the run length"""
    L = LineString(run['pts']); n = int(L.length / step)
    if n < 20: return [], L.length
    S = np.linspace(0, L.length, n + 1); P = np.array([L.interpolate(d).coords[0] for d in S])
    T = np.gradient(P, axis=0); T /= np.hypot(T[:, 0], T[:, 1])[:, None] + 1e-9
    for _ in range(6): T[1:-1] = (T[:-2] + 2 * T[1:-1] + T[2:]) / 4
    T /= np.hypot(T[:, 0], T[:, 1])[:, None] + 1e-9; N = np.c_[-T[:, 1], T[:, 0]]
    hits = []
    for dep in depths:
        Q = P + N * dep; v = tiles.sample(Q[:, 0], Q[:, 1])
        if np.isnan(v).mean() > 0.5: return [], L.length
        v = np.where(np.isnan(v), np.nanmedian(v), v); b = median_filter(v, size=13, mode='nearest'); drop = b - v
        dark = drop > 32
        i = 0; h = []
        while i < len(dark):
            if dark[i]:
                j = i
                while j + 1 < len(dark) and dark[j + 1]: j += 1
                if j - i <= 3: h.append(S[(i + j) // 2])
                i = j + 1
            else: i += 1
        hits.append(np.array(h))
    cand = []
    for x in hits[1]:                 # seen at 6 m and at 3.5 or 9 m
        if any(len(h) and np.min(np.abs(h - x)) < 0.6 for h in (hits[0], hits[2])): cand.append(x)
    cand = [x for x in cand if 1.5 < x < L.length - 1.5]
    out = []
    for x in sorted(cand):
        if out and x - out[-1] < 1.0: continue
        out.append(x)
    return out, L.length

def scan2(tiles, run, d0=2.0, d1=14.0, step=0.25, frac_min=0.45):
    """lot-line candidates: along each street face, the fraction of depths (2-14 m in) at which a thin dark line crosses
    each point; a straight lot line or party wall square to the street scores high, lettering and hatching do not."""
    L = LineString(run['pts']); n = int(L.length / step)
    if n < 20: return [], L.length, None
    S = np.linspace(0, L.length, n + 1); P = np.array([L.interpolate(d).coords[0] for d in S])
    T = np.gradient(P, axis=0); T /= np.hypot(T[:, 0], T[:, 1])[:, None] + 1e-9
    for _ in range(8): T[1:-1] = (T[:-2] + 2 * T[1:-1] + T[2:]) / 4
    T /= np.hypot(T[:, 0], T[:, 1])[:, None] + 1e-9; N = np.c_[-T[:, 1], T[:, 0]]
    deps = np.arange(d0, d1 + 1e-6, step); G = np.empty((len(deps), len(S)))
    for k, dep in enumerate(deps):
        Q = P + N * dep; G[k] = tiles.sample(Q[:, 0], Q[:, 1])
    if np.isnan(G).mean() > 0.4: return [], L.length, None
    med = np.nanmedian(G); G = np.where(np.isnan(G), med, G)
    hp = median_filter(G, size=(1, 13), mode='nearest') - G
    line = (hp > 25).astype(float)
    # allow a line to wander one pixel either way between depths
    line = np.maximum(line, np.maximum(np.roll(line, 1, axis=1), np.roll(line, -1, axis=1)))
    frac = line.mean(axis=0)
    cand = []
    for i in range(2, len(frac) - 2):
        if frac[i] >= frac_min and frac[i] == frac[max(0, i - 6):i + 7].max() and 1.5 < S[i] < L.length - 1.5:
            if cand and S[i] - cand[-1][0] < 2.0:
                if frac[i] > cand[-1][1]: cand[-1] = (S[i], frac[i])
                continue
            cand.append((S[i], frac[i]))
    return [c[0] for c in cand], L.length, frac

def face_width(frac, step=0.25, lo=4.5, hi=20.0):
    """the face's repeating lot width from the autocorrelation of its line-strength profile, or None if nothing repeats"""
    if frac is None or len(frac) < int(2.5 * lo / step): return None
    f = frac - frac.mean(); n = len(f); z = float((f * f).sum())
    if z <= 1e-9: return None
    best, bw = 0.0, None
    for lag in range(int(lo / step), min(int(hi / step), n // 2)):
        r = float((f[:-lag] * f[lag:]).sum()) / z
        if r > best: best, bw = r, lag * step
    return bw if best >= 0.22 else None
def cuts_for(L, frac, w, step=0.25, snap=2.5, fmin=0.45, wmin=3.5):
    """even cuts at width w from the corners, each snapped to the strongest sheet line within 2.5 m"""
    n = max(1, int(round(L / w))); cuts = []
    for k in range(1, n):
        x = L * k / n
        if frac is not None:
            i0, i1 = max(0, int((x - snap) / step)), min(len(frac) - 1, int((x + snap) / step))
            if i1 > i0:
                j = i0 + int(np.argmax(frac[i0:i1 + 1]))
                if frac[j] >= fmin: x = j * step
        if (cuts and x - cuts[-1] < wmin) or x < wmin or L - x < wmin: continue
        cuts.append(x)
    return cuts
