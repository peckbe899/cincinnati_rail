# Yard track generator: throats split by turnouts into a tree of leads; each group ends in a simple ladder at the frog angle.
# Turnouts: No. 8 in the yard (frog angle 2 atan(1/16) = 7.15 deg), No. 10 on leads (5.73 deg). Curves R 200 m (drawing value).
import math
from shapely.geometry import LineString, Point
A8 = 2 * math.atan(1 / 16); A10 = 2 * math.atan(1 / 20)
R_C = 280.0; PHI = math.radians(25.0); SP = 4.5; G = 8; RUN = 25.0; TAN = 40.0

def fil(pts, R=None):
    R = R_C if R is None else R
    pts = [tuple(map(float, p)) for p in pts]; res = [pts[0]]
    for i in range(1, len(pts) - 1):
        a, b, c = pts[i - 1], pts[i], pts[i + 1]
        u = (a[0] - b[0], a[1] - b[1]); lu = math.hypot(*u); v = (c[0] - b[0], c[1] - b[1]); lv = math.hypot(*v)
        if lu < 1e-6 or lv < 1e-6: continue
        u = (u[0] / lu, u[1] / lu); v = (v[0] / lv, v[1] / lv)
        ang = math.acos(max(-1, min(1, u[0] * v[0] + u[1] * v[1]))); defl = math.pi - ang
        if defl < 1e-4: res.append(b); continue
        T = min(R * math.tan(defl / 2), lu * 0.5 if i > 1 else lu, lv * 0.5 if i < len(pts) - 2 else lv); Rr = T / math.tan(defl / 2)
        t1 = (b[0] + u[0] * T, b[1] + u[1] * T); t2 = (b[0] + v[0] * T, b[1] + v[1] * T)
        bis = (u[0] + v[0], u[1] + v[1]); lb = math.hypot(*bis); bis = (bis[0] / lb, bis[1] / lb)
        cc = (b[0] + bis[0] * Rr / math.sin(ang / 2), b[1] + bis[1] * Rr / math.sin(ang / 2))
        a1 = math.atan2(t1[1] - cc[1], t1[0] - cc[0]); a2 = math.atan2(t2[1] - cc[1], t2[0] - cc[0]); d = (a2 - a1 + math.pi) % (2 * math.pi) - math.pi
        n = max(2, int(abs(d) * Rr / 3)); res += [(cc[0] + Rr * math.cos(a1 + d * k / n), cc[1] + Rr * math.sin(a1 + d * k / n)) for k in range(n + 1)]
    res.append(pts[-1]); return res

class Frame:
    def __init__(self, O, u):
        l = math.hypot(*u); self.O = O; self.u = (u[0] / l, u[1] / l)
        self.w = (-self.u[1], self.u[0])   # u south -> w east
    def W(self, x, t): return (self.O[0] + x * self.w[0] + t * self.u[0], self.O[1] + x * self.w[1] + t * self.u[1])
    def L(self, X, Y): dx, dy = X - self.O[0], Y - self.O[1]; return (dx * self.w[0] + dy * self.w[1], dx * self.u[0] + dy * self.u[1])

def branch_pts(x0, t0, th0, c):
    """from (x0, t0) heading th0 (lateral angle, 0 = along the yard), reach lateral c heading 0. Local polyline."""
    d = c - x0
    if abs(d) < 0.05 and abs(th0) < 1e-6: return [(x0, t0), (c, t0 + RUN)]
    s = 1 if d > 0 else -1
    k1 = (x0 + math.sin(th0) * RUN, t0 + math.cos(th0) * RUN)
    rem = c - k1[0]
    if s * rem <= 0.5:   # the turnout alone gets there: shorten its run
        if abs(th0) > 1e-6:
            run = abs(d) / math.sin(abs(th0)); k1 = (c, t0 + math.cos(th0) * run); return [(x0, t0), k1, (c, k1[1] + TAN)]
        rem = d; k1 = (x0, t0)
    phi = PHI
    # small moves: a flatter angle so the two curves fit
    need = 2 * R_C * (1 - math.cos(phi))
    if abs(rem) < need: phi = max(math.acos(max(-1, 1 - abs(rem) / (2 * R_C))) * 0.9, math.radians(3))
    k2 = (c, k1[1] + abs(rem) / math.tan(phi))
    return [(x0, t0), k1, k2, (c, k2[1] + TAN)]

def tree(xs, frame, start=(0.0, 0.0)):
    """xs: local laterals of the tracks (sorted). Returns (segments as world polylines, body start t per lateral)."""
    segs, body = [], {}
    def serve(x, t, th, tracks, first):
        if len(tracks) <= G:
            # leaf: arrive on the edge track nearest x, ladder across the rest
            edge = min(tracks, key=lambda v: abs(v - x)); far = max(tracks, key=lambda v: abs(v - edge))
            p = branch_pts(x, t, th, edge); segs.append(p); te = p[-1][1]
            body[edge] = te
            rest = sorted([v for v in tracks if v != edge], key=lambda v: abs(v - edge))
            if rest:
                s = 1 if rest[0] > edge else -1; sw = te + 20.0
                last = None
                for v in rest:
                    dd = abs(v - edge) / math.sin(A8); B = (v, sw + dd * math.cos(A8)); body[v] = B[1]; last = B
                segs.append([(edge, sw), last])
            return
        tracks = sorted(tracks); h = len(tracks) // 2; L, R = tracks[:h], tracks[h:]
        def target(half): return min(half, key=lambda v: abs(v - x)) if len(half) <= G else sum(half) / len(half)
        cl, cr = target(L), target(R)
        # the half whose target is nearer takes the straight route; the other the diverging route (No. 8)
        if abs(cl - x) <= abs(cr - x): near, far_, cn, cf = L, R, cl, cr
        else: near, far_, cn, cf = R, L, cr, cl
        sf = 1 if cf > x else -1
        pn = branch_pts(x, t, th, cn); pf = branch_pts(x, t, sf * A8 if abs(th) < 1e-6 else th, cf)
        segs.append(pn); segs.append(pf)
        serve(cn, pn[-1][1], 0.0, near, False); serve(cf, pf[-1][1], 0.0, far_, False)
    serve(start[0], start[1], 0.0, list(xs), True)
    world = [[frame.W(*q) for q in s] for s in segs]
    return world, body

class CurveFrame:
    """local (x, t): t = distance along the spine, x = offset (east of the spine when it heads south)"""
    def __init__(self, pts):
        self.sp = LineString(pts); self.L = self.sp.length
    def _ut(self, t):
        t = max(0.0, min(self.L, t)); a = self.sp.interpolate(max(0, t - 2)); b = self.sp.interpolate(min(self.L, t + 2))
        u = (b.x - a.x, b.y - a.y); l = math.hypot(*u); return (u[0] / l, u[1] / l)
    def W(self, x, t):
        if t > self.L:   # carry on straight past the end
            p = self.sp.interpolate(self.L); u = self._ut(self.L); e = t - self.L
            return (p.x + u[0] * e + x * -u[1], p.y + u[1] * e + x * u[0])
        if t < 0:
            p = self.sp.interpolate(0); u = self._ut(0)
            return (p.x + u[0] * t + x * -u[1], p.y + u[1] * t + x * u[0])
        p = self.sp.interpolate(t); u = self._ut(t)
        return (p.x + x * -u[1], p.y + x * u[0])
    def Lc(self, X, Y):
        t = self.sp.project(Point(X, Y)); p = self.sp.interpolate(t); u = self._ut(t)
        return ((X - p.x) * -u[1] + (Y - p.y) * u[0], t)
    def poly(self, pts, step=6.0):
        """map a local polyline, densified so curves of the spine carry through"""
        out = []
        for (x0, t0), (x1, t1) in zip(pts, pts[1:]):
            n = max(1, int(math.hypot(x1 - x0, t1 - t0) / step))
            for k in range(n): out.append(self.W(x0 + (x1 - x0) * k / n, t0 + (t1 - t0) * k / n))
        out.append(self.W(*pts[-1])); return out

def tree_local(xs, start=(0.0, 0.0)):
    """the throat tree in local coordinates: returns (local polylines, filleted), body start t per lateral"""
    segs, body = [], {}
    def serve(x, t, th, tracks):
        if len(tracks) <= G:
            # leaf: arrive on the middle track; a ladder off it each side (No. 8, at the frog angle), the second 25 m after the first
            tr = sorted(tracks); mid = tr[len(tr) // 2]
            p = fil(branch_pts(x, t, th, mid)); segs.append(p); te = p[-1][1]; body[mid] = te
            lo = sorted([v for v in tr if v < mid], key=lambda v: mid - v); hi = sorted([v for v in tr if v > mid], key=lambda v: v - mid)
            sw = te + 15.0
            for side in (hi, lo):
                if not side: continue
                last = None
                for v in side:
                    dd = abs(v - mid) / math.sin(A8); B = (v, sw + dd * math.cos(A8)); body[v] = B[1]; last = B
                segs.append([(mid, sw), last]); sw += 25.0
            return
        tracks = sorted(tracks); h = len(tracks) // 2; Lh, Rh = tracks[:h], tracks[h:]
        def target(half): return min(half, key=lambda v: abs(v - x)) if len(half) <= G else sum(half) / len(half)
        cl, cr = target(Lh), target(Rh)
        if abs(cl - x) <= abs(cr - x): near, far_, cn, cf = Lh, Rh, cl, cr
        else: near, far_, cn, cf = Rh, Lh, cr, cl
        sf = 1 if cf > x else -1
        pn = fil(branch_pts(x, t, th, cn)); pf = fil(branch_pts(x, t, sf * A8, cf))
        segs.append(pn); segs.append(pf)
        serve(cn, pn[-1][1], 0.0, near); serve(cf, pf[-1][1], 0.0, far_)
    serve(start[0], start[1], 0.0, list(xs))
    return segs, body

TO = 25.0                     # turnout length, switch point to the next switch (drawing value)
PHI_MAX = math.radians(22.0)  # steepest heading in a fan before the tracks curve back
def spray_local(xs, start=(0.0, 0.0)):
    """a hump-yard style fan: every split is a No. 8 turnout (straight route and a 7.15 deg diverging route),
    splits follow one another a turnout length apart, so the fan stays dense like a real throat; each track then curves (R 150) back parallel"""
    segs, body = [], {}
    def head(th): return (math.sin(th), math.cos(th))
    def leaf(x, t, th, xt):
        d = xt - x
        pts = [(x, t)]
        if abs(th) < 1e-6 and abs(d) < 0.05:
            pts.append((xt, t + 30)); segs.append(pts); body[xt] = t + 30; return
        s = 1 if d > 0 else -1
        # keep the heading if it points the right way and the move is big enough, else swing to a heading that does
        need = R_C * (1 - math.cos(abs(th)))
        if th * s > 0 and abs(d) >= need:
            run = (abs(d) - need) / math.sin(abs(th)) + R_C * math.tan(abs(th) / 2)
            p1 = (x + math.sin(th) * run, t + math.cos(th) * run)
            pts += [p1, (xt, p1[1] + max(30.0, R_C * math.tan(abs(th) / 2) + 5))]
        else:
            ang = min(PHI_MAX, max(math.radians(4), math.acos(max(-1, 1 - abs(d) / (2 * R_C))) if abs(d) < 2 * R_C * (1 - math.cos(PHI_MAX)) else PHI_MAX))
            p1 = (x + math.sin(th) * 15, t + math.cos(th) * 15)
            p2 = (xt, p1[1] + abs(xt - p1[0]) / math.tan(ang) + 10)
            pts += [p1, p2, (xt, p2[1] + 30)]
        p = fil(pts); segs.append(p); body[xt] = p[-1][1]
    def serve(x, t, th, tracks):
        tracks = sorted(tracks)
        if len(tracks) == 1: leaf(x, t, th, tracks[0]); return
        h = len(tracks) // 2; Lh, Rh = tracks[:h], tracks[h:]
        cL, cR = sum(Lh) / len(Lh), sum(Rh) / len(Rh)
        # which half the straight route keeps: the one nearer the line the node is heading along
        ahead = x + math.tan(th) * 60
        if abs(cL - ahead) <= abs(cR - ahead): st, dv, sd = Lh, Rh, +1
        else: st, dv, sd = Rh, Lh, -1
        th_s = th; th_d = max(-PHI_MAX, min(PHI_MAX, th + sd * A8))
        hs, hd = head(th_s), head(th_d)
        ns = (x + hs[0] * TO, t + hs[1] * TO); nd = (x + hd[0] * TO, t + hd[1] * TO)
        segs.append([(x, t), ns]); segs.append([(x, t), nd])
        serve(ns[0], ns[1], th_s, st); serve(nd[0], nd[1], th_d, dv)
    lead = [(start[0], start[1]), (start[0], start[1] + 20)]
    segs.append(lead); serve(start[0], start[1] + 20, 0.0, list(xs))
    return segs, body

def spray2(xs, start=(0.0, 0.0), phi=None):
    """dense fan: splits a turnout length apart (No. 8: straight route and 7.15 deg diverging route); between splits a branch may
    curve (R >= R_C) toward its half of the tracks; each track then curves back parallel. Returns local polylines and body starts."""
    phi = phi or PHI
    segs, body = [], {}
    dmax = TO / R_C                       # most a branch can turn on one turnout length of curve
    def clampv(v, a, b): return max(a, min(b, v))
    def want(x, c): d = c - x; return clampv(math.atan2(d, max(60.0, abs(d) / math.tan(phi))), -phi, phi)
    def leaf(x, t, th, xt):
        pts = [(x, t)]; d = xt - x
        if abs(d) < 0.05 and abs(th) < 1e-6: pts.append((x, t + 15)); segs.append(pts); body[xt] = t + 15; return
        s = 1 if d > 0 else -1
        if th * s <= 1e-6: th = s * math.radians(3)   # never heading away: a small swing first (fil makes the curve)
        need = R_C * (1 - math.cos(abs(th)))
        run = max(0.0, (abs(d) - need)) / math.sin(abs(th))
        p1 = (x + math.sin(th) * (run + R_C * math.tan(abs(th) / 2)), t + math.cos(th) * (run + R_C * math.tan(abs(th) / 2)))
        p1 = (xt if abs(p1[0] - xt) < 0.01 else p1[0], p1[1])
        pts += [p1, (xt, p1[1] + R_C * math.tan(abs(th) / 2) + 10)]
        p = fil(pts); segs.append(p); body[xt] = p[-1][1]
    def serve(x, t, th, tracks):
        tracks = sorted(tracks)
        if len(tracks) == 1: leaf(x, t, th, tracks[0]); return
        h = len(tracks) // 2; Lh, Rh = tracks[:h], tracks[h:]
        cL, cR = sum(Lh) / len(Lh), sum(Rh) / len(Rh)
        wL, wR = want(x, cL), want(x, cR)
        if abs(wL - th) <= abs(wR - th): st, dv, ws, wd, sd = Lh, Rh, wL, wR, +1
        else: st, dv, ws, wd, sd = Rh, Lh, wR, wL, -1
        th_s = th; th_d = th + sd * A8
        for tr_, th0, w in ((st, th_s, ws), (dv, th_d, wd)):
            # the turnout (25 m at th0), then a curve toward the wanted heading over one more turnout length
            p0 = (x, t); p1 = (x + math.sin(th0) * TO, t + math.cos(th0) * TO)
            th1 = clampv(w, th0 - dmax, th0 + dmax)
            p2 = (p1[0] + math.sin((th0 + th1) / 2) * TO, p1[1] + math.cos((th0 + th1) / 2) * TO)
            segs.append([p0, p1, p2]); serve(p2[0], p2[1], th1, tr_)
    segs.append([(start[0], start[1]), (start[0], start[1] + 20)])
    serve(start[0], start[1] + 20, 0.0, list(xs))
    return segs, body

def ladder_fan(xs, start=(0.0, 0.0)):
    """compound ladder throat. The lead runs on as the centre track; the tracks 4.5 m either side leave by a No. 8 turnout and a curve back.
    Each side: a No. 8 turnout puts out a leg at the frog angle (7.15 deg) that is the first group's ladder; a second No. 8 turnout on that leg
    puts out the master ladder at twice the angle (14.3 deg); the other groups' ladders leave the master by No. 8 turnouts and run at 7.15 deg;
    every track leaves its ladder by a No. 8 turnout (diverging 7.15 deg, so it comes out parallel). No curves inside the ladders."""
    segs, body = [], {}
    x0, t0 = start
    B2 = 2 * A8
    t = t0 + 20.0
    segs.append([(x0, t0), (x0, t)])
    near = sorted([x for x in xs if abs(x - x0) < 2 * SP - 0.01], key=lambda v: abs(v - x0))
    for x in near:
        if abs(x - x0) < 0.01: body[x] = t; continue
        sd = 1 if x > x0 else -1
        p = fil(branch_pts(x0, t, sd * A8, x)); segs.append(p); body[x] = p[-1][1]; t += TO
    mstart = t
    for side, tsw in ((-1, mstart), (+1, mstart + TO)):
        tr = sorted([x for x in xs if (x - x0) * side > 0.01 and abs(x - x0) >= 2 * SP - 0.01], key=lambda v: abs(v - x0))
        if not tr: continue
        groups = [tr[i:i + G] for i in range(0, len(tr), G)]
        P0 = (x0, tsw); P1 = (x0 + side * TO * math.sin(A8), tsw + TO * math.cos(A8))
        last_b = None
        for gi, g in enumerate(groups):
            if gi == 0:
                B = P0; b_lat = 0.0; ang = A8
            else:
                b_lat = abs(g[0] - x0) - TO * math.sin(A8)
                e = (b_lat - TO * math.sin(A8)) / math.sin(B2)
                B = (x0 + side * b_lat, P1[1] + e * math.cos(B2)); last_b = B
            pl = None
            for x in g:
                d = (abs(x - x0) - b_lat) / math.sin(A8)
                P = (x, B[1] + d * math.cos(A8)); body[x] = P[1]; pl = P
            segs.append([B, pl])
        if last_b is not None: segs.append([P1, last_b])
    return segs, body

def ladder_fan3(xs, start=(0.0, 0.0)):
    """steeper compound throat: master ladder at three times the frog angle (21.5 deg: a No. 8 turnout, then a curve);
    each group lead leaves the master by a No. 8 turnout (to 14.3 deg) and curves to 7.15 deg, then a simple ladder feeds its tracks.
    The first group's ladder is the master turnout's own leg. Curves R_C or more; turnouts 25 m apart or more."""
    segs, body = [], {}
    x0, t0 = start
    t = t0 + 20.0
    segs.append([(x0, t0), (x0, t)])
    near = sorted([x for x in xs if abs(x - x0) < 2 * SP - 0.01], key=lambda v: abs(v - x0))
    for x in near:
        if abs(x - x0) < 0.01: body[x] = t; continue
        sd = 1 if x > x0 else -1
        p = fil(branch_pts(x0, t, sd * A8, x)); segs.append(p); body[x] = p[-1][1]; t += TO
    mstart = t
    B3 = 3 * A8
    for side, tsw in ((-1, mstart), (+1, mstart + TO)):
        tr = sorted([x for x in xs if (x - x0) * side > 0.01 and abs(x - x0) >= 2 * SP - 0.01], key=lambda v: abs(v - x0))
        if not tr: continue
        groups = [tr[i:i + G] for i in range(0, len(tr), G)]
        P0 = (x0, tsw); P1 = (x0 + side * TO * math.sin(A8), tsw + TO * math.cos(A8))
        # master: from P1 a No. 8 turnout to 14.3 deg, then a curve to 21.5 deg; laid as a polyline P1 -> K -> far point, filleted
        K = (P1[0] + side * TO * math.sin(2 * A8), P1[1] + TO * math.cos(2 * A8))
        def mpt(e): return (K[0] + side * e * math.sin(B3), K[1] + e * math.cos(B3))
        last = None
        e_prev = R_C * math.tan(A8 / 2) + 10.0
        for gi, g in enumerate(groups):
            if gi == 0:
                pl = None
                for x in g:
                    d = abs(x - x0) / math.sin(A8); P = (x, tsw + d * math.cos(A8)); body[x] = P[1]; pl = P
                segs.append([P0, pl]); continue
            # group lead: leaves the master at e, diverges to 14.3 deg for a turnout length, curves to 7.15 deg, ladder at 7.15 deg
            target = abs(g[0] - x0)
            # find e so that after the turnout (14.3 deg) and the curve the ladder starts at a lateral that puts its first track at 'target'
            for e in [e_prev + 5.0 * k for k in range(0, 400)]:
                Bm = mpt(e)
                Q1 = (Bm[0] + side * TO * math.sin(2 * A8), Bm[1] + TO * math.cos(2 * A8))
                Tc = R_C * math.tan(A8 / 2)
                Q2 = (Q1[0] + side * Tc * math.sin(2 * A8), Q1[1] + Tc * math.cos(2 * A8))   # vertex of the curve to 7.15 deg
                lat_after = abs(Q2[0] - x0) + Tc * math.sin(A8)
                if lat_after + TO * math.sin(A8) >= target - 0.01: break
            e_prev = e + G * SP / math.sin(B3) * 0.6
            # ladder at 7.15 deg from Q2 (after the curve), tracks peel at their laterals
            pl = None
            for x in g:
                d = (abs(x - x0) - abs(Q2[0] - x0)) / math.sin(A8); P = (x, Q2[1] + d * math.cos(A8)); body[x] = P[1]; pl = P
            segs.append(fil([Bm, Q1, Q2, pl], R_C))
            last = Bm
        if last is not None: segs.append(fil([P1, K, (last[0] + side * 30 * math.sin(B3), last[1] + 30 * math.cos(B3))], R_C))
    return segs, body
