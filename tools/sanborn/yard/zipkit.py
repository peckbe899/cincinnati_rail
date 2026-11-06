try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Orientation study inside Ben's buildable area (27 October). Generic tools: smoothed spine, room edges, yards with leads anywhere.
import json, math, sys
sys.path.insert(0, (_ws.CODE + 'yard'))
import ygen
from ygen import CurveFrame, ladder_fan, fil, SP, A8
from shapely.geometry import shape, LineString, Point, Polygon
from shapely.ops import unary_union
A = shape(json.load(open((_ws.DATA + 'yard/ben_area.json')))['geometry'])
ROOM0 = A.buffer(-2.5)
ygen.G = 4
def radii(pts):
    m = 1e9
    for a, b, c in zip(pts, pts[1:], pts[2:]):
        ab = math.dist(a, b); bc = math.dist(b, c); ac = math.dist(a, c)
        cr = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        if abs(cr) < 1e-9 or ab < 0.3 or bc < 0.3: continue
        m = min(m, ab * bc * ac / (2 * abs(cr)))
    return m
def filr(pts, rads):
    out = [tuple(pts[0])]
    for i in range(1, len(pts) - 1):
        out += fil([pts[i - 1], pts[i], pts[i + 1]], rads[i - 1])[1:-1]
    out.append(tuple(pts[-1])); return out
CL = json.load(open((_ws.DATA + 'yard/cline.json')))
PI = list(LineString(CL).simplify(35).coords)
SPINE = filr(PI, [800.0] * (len(PI) - 2))
F = CurveFrame(SPINE)
def edges(t):
    xs = [x for x in range(-220, 221, 1) if Point(F.W(x, t)).within(ROOM0)]
    if not xs: return None
    # the run containing (or nearest) 0
    runs = []
    for x in xs:
        if runs and x == runs[-1][1] + 1: runs[-1][1] = x
        else: runs.append([x, x])
    return min(runs, key=lambda r: 0 if r[0] <= 0 <= r[1] else min(abs(r[0]), abs(r[1])))
def lat_range(a, b, s=SP):
    if b < a: a, b = b, a
    n = int(math.floor((b - a) / s + 1e-9)); return [round(a + k * s, 2) for k in range(n + 1)]
def MF(xs, lead, off):
    sg, bd = ladder_fan(xs, (lead, 0.0)); return [[(x, t + off) for x, t in q] for q in sg], {k: v + off for k, v in bd.items()}
def yard(room, xs, lead, t0, t1, minbody=200.0, it=40):
    """through yard between t0 and t1, one lead lateral at both ends; returns (track lines, throat lines)"""
    fS = CurveFrame(SPINE[::-1]); L = F.L
    xs = list(xs)
    for _ in range(it):
        sN, bN = MF(xs, lead, t0); sS, bS = MF([-x for x in xs], -lead, L - t1)
        keep = []
        for x in xs:
            a, b = bN[x], L - bS[-x]
            if b - a < minbody: continue
            if not LineString(F.poly([(x, a), (x, b)], 10)).within(room): continue
            keep.append(x)
        if keep and keep == xs:
            bad = None
            for p in sN:
                if not LineString(F.poly(p, 4)).within(room.buffer(0.5)): bad = p; break
            if bad is None:
                for p in sS:
                    if not LineString(fS.poly(p, 4)).within(room.buffer(0.5)): bad = [(-x, t) for x, t in p]; break
            if bad is None: break
            far = max(keep, key=lambda v: abs(v - lead)); keep = [x for x in keep if x != far]
        if not keep: return [], []
        xs = keep
    sN, bN = MF(xs, lead, t0); sS, bS = MF([-x for x in xs], -lead, L - t1)
    tr = [LineString(F.poly([(x, bN[x]), (x, L - bS[-x])], 10)) for x in xs]
    th = [LineString(F.poly(p, 4)) for p in sN] + [LineString(fS.poly(p, 4)) for p in sS]
    return tr, th
def fp(lines):
    g = unary_union([l.buffer(3) for l in lines]).buffer(12).buffer(-12)
    return unary_union([x for x in getattr(g, 'geoms', [g]) if x.area > 2000])
def take(room, lines): return room.difference(unary_union([l.buffer(SP / 2 + 3.0) for l in lines])) if lines else room

def stub_south(room, xs, lead, t1, minbody=200.0, it=40):
    """stub yard: one fan at t1 opening southward; each track runs south until it leaves the room (the river end)"""
    fS = CurveFrame(SPINE[::-1]); L = F.L; xs = list(xs)
    def ends(x, a):
        t = a
        while t > 0 and Point(F.W(x, t - 5)).within(room): t -= 5
        return t
    for _ in range(it):
        sS, bS = MF([-x for x in xs], -lead, L - t1)
        keep = [x for x in xs if Point(F.W(x, L - bS[-x])).within(room) and (L - bS[-x]) - ends(x, L - bS[-x]) >= minbody]
        if keep and keep == xs:
            bad = None
            for p in sS:
                if not LineString(fS.poly(p, 4)).within(room.buffer(0.5)): bad = p; break
            if bad is None: break
            far = max(keep, key=lambda v: abs(v - lead)); keep = [x for x in keep if x != far]
        if not keep: return [], []
        xs = keep
    sS, bS = MF([-x for x in xs], -lead, L - t1)
    tr = [LineString(F.poly([(x, ends(x, L - bS[-x])), (x, L - bS[-x])], 10)) for x in xs]
    th = [LineString(fS.poly(p, 4)) for p in sS]
    return tr, th
def side_yards(room, core_lines, core_lo, core_hi, t0, t1, minbody=200.0, min_extra=20.0, min_len=500.0, only=0):
    """tracks beyond the core yard's outer tracks where the room widens: a one-sided yard off the outermost core track"""
    out = []
    for sgn, core in ((-1, core_lo), (+1, core_hi)):
        if only and sgn != only: continue
        spans, cur = [], None
        for t in range(int(t0), int(t1) + 1, 25):
            e = edges(t); extra = (core - e[0]) if sgn < 0 else (e[1] - core)
            if extra >= min_extra + SP: cur = [t, t] if cur is None else [cur[0], t]
            else:
                if cur and cur[1] - cur[0] >= min_len: spans.append(cur)
                cur = None
        if cur and cur[1] - cur[0] >= min_len: spans.append(cur)
        for a, b in spans:
            edge = [edges(t) for t in range(a, b + 1, 25)]
            far = min(e[0] for e in edge) if sgn < 0 else max(e[1] for e in edge)
            xs = lat_range(core + sgn * SP, far) 
            corel = LineString(F.poly([(core, a - 80), (core, b + 80)], 10))
            rx = room.union(corel.buffer(SP / 2 + 3.5))
            tr, th = yard(rx, xs, core, float(a), float(b), minbody)
            if tr: room = take(room, tr + th); out += tr + th
    return room, out
