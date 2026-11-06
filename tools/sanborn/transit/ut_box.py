"""Union Terminal TRI box (RER A, B, D), set by direction as at Chatelet-Les Halles, two tracks per island (Ben, 2026-10-11/12).

Chatelet-Les Halles: 1A (A east) | quai 1 | 1B (B south), 3 (D south) | quai 3 | Z | quai 4 | 4 (D north), 2B (B north) | quai 2 |
2A (A west). Every track of one direction is on one side; A and B share the outer islands in the same direction, D has the
centre. Here the centre is one island with D's two tracks (no Z), so every island has two tracks; D's tracks connect to A's tracks
east of the box (D runs on A's trunk to City Hall), as Ben asked.

Right-hand running, westbound on the north side:
    north island:  A westbound | B westbound            (cross-platform A <-> B, same direction)
    centre island: D westbound | D eastbound
    south island:  B eastbound | A eastbound            (cross-platform B <-> A)
B and D arrive together from Western (one pair) and split in the box; west of it A goes on to Evans; east of it B leaves on its own
pair (Music Hall/Washington) north of the A/D trunk, and A and D merge onto one pair (A eastbound into D eastbound, A westbound
off D westbound). Platforms 670 ft (204.2 m, canon); island 11 m, 14.5 m across an island, 4.5 m back to back (drawing values).

Crossings at separate levels that this layout needs (marked): west, A westbound across the B/D bundle on its way to Evans; east,
B eastbound across D eastbound, A westbound across B westbound, and A/D westbound across B eastbound, all three B against A/D,
so one level change for the B pair covers them. TRI B/D share TRI A's level in the box (10l.26)."""
import numpy as np
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

C0 = np.array([713157.5, 4331848.3])                    # station point (Cincinnati Rail.kmz)
U = np.array([713405.0 - 713024.0, 4331835.0 - 4331860.0]); U = U / np.linalg.norm(U)   # A/D trunk heading through the box
N_ = np.array([-U[1], U[0]])                            # north (left of eastbound)
PL, ISL, EDGE, BB = 204.2, 11.0, 1.75, 4.5
X = ISL + 2 * EDGE                                      # track centres across an island
OFF = {'D wb': X / 2, 'D eb': -X / 2}
OFF['B wb'] = OFF['D wb'] + BB; OFF['B eb'] = OFF['D eb'] - BB
OFF['A wb'] = OFF['B wb'] + X; OFF['A eb'] = OFF['B eb'] - X
ISLANDS = {'north (A/B westbound)': (OFF['A wb'] + OFF['B wb']) / 2, 'centre (D)': 0.0, 'south (B/A eastbound)': (OFF['B eb'] + OFF['A eb']) / 2}
S_BOX = 130.0                                           # straight box: platforms +- 102.1 m and turnouts beyond
S_W, S_E = -330.0, 500.0                                # where the custom tracks hand over to the line tracks
def at(s, h): return C0 + U * s + N_ * h
def ease(a, b, t): t = min(1.0, max(0.0, t)); return a + (b - a) * (1 - np.cos(np.pi * t)) / 2
def track(ctrl, step=2.0):
    """ctrl: [(s, h), ...] in increasing s; offsets eased between controls (cosine)."""
    out = []
    for (s0, h0), (s1, h1) in zip(ctrl[:-1], ctrl[1:]):
        n = max(1, int((s1 - s0) / step))
        for k in range(n): s = s0 + (s1 - s0) * k / n; out.append(at(s, ease(h0, h1, (s - s0) / (s1 - s0))))
    out.append(at(*ctrl[-1])); return out
def bez(p0, t0, p3, t3, k=0.38, n=40):
    p0, p3 = np.asarray(p0, float), np.asarray(p3, float); L = np.linalg.norm(p3 - p0)
    c1, c2 = p0 + np.asarray(t0) * L * k, p3 - np.asarray(t3) * L * k
    u = np.linspace(0, 1, n)[:, None]
    return list((1 - u) ** 3 * p0 + 3 * (1 - u) ** 2 * u * c1 + 3 * (1 - u) * u ** 2 * c2 + u ** 3 * p3)
def unit(v): v = np.asarray(v, float); return v / np.linalg.norm(v)

# ---------------------------------------------------------------- B/D route south of Straight (Ben, 2026-10-12)
# B/D run at grade (under the deck's north lobe) to Camp Washington, then in a dug tunnel along the KMZ trunk to Straight, then
# bored to Union Terminal. The at-grade and dug parts keep the KMZ line; the bore takes the best line. The KMZ bend from
# Camp Washington's heading into Straight (about 450 m radius) is kept as one curve that ends on a straight through the Straight
# station point and tangent to the box curve, which bends left R_BD onto the box axis BD_ON m west of the station centre. That
# drops the old line's reverse curves south of Straight (the freight-yard trace past Western and the S-bend into the approach).
R_C, R_BD, BD_ON = 450.0, 250.0, -330.0
def _dir(h): return np.array([np.cos(h), np.sin(h)])
def _arc(p, h, R, ang, step=2.0):
    n = max(2, int(R * abs(ang) / step)); out = []
    for k in range(n): h += ang / n; p = p + _dir(h) * R * abs(ang) / n; out.append(p.copy())
    return out, h
def bd_route(l1_pt, l1_h, s_pt):
    """l1_pt, l1_h: the KMZ trunk's straight south-east of Camp Washington; s_pt: Straight station point (KMZ)."""
    l1_pt, s_pt = np.asarray(l1_pt, float), np.asarray(s_pt, float); hU = np.arctan2(U[1], U[0])
    Cf = at(BD_ON, R_BD); v = Cf - s_pt
    th = np.arctan2(v[1], v[0]) - np.arcsin(R_BD / np.linalg.norm(v))     # straight through Straight, box curve on its left
    T2 = Cf + R_BD * np.array([np.sin(th), -np.cos(th)])
    # intersection of the trunk straight and the new straight, then one curve R_C tangent to both
    A_ = np.c_[_dir(l1_h), -_dir(th)]; t, u = np.linalg.solve(A_, s_pt - l1_pt); I = l1_pt + t * _dir(l1_h)
    dl = (th - l1_h + np.pi) % (2 * np.pi) - np.pi; Tn = R_C * np.tan(abs(dl) / 2)
    A1 = I - Tn * _dir(l1_h); A2 = I + Tn * _dir(th)
    pts = [A1.copy()]; arc, h = _arc(A1, l1_h, R_C, dl); pts += arc; pts[-1] = A2
    L = np.linalg.norm(T2 - A2); n = max(2, int(L / 2.0))
    pts += [A2 + (T2 - A2) * k / n for k in range(1, n + 1)]
    arc, h = _arc(T2, th, R_BD, hU - th); pts += arc; pts[-1] = at(BD_ON, 0.0)
    pts += [at(s_, 0.0) for s_ in np.arange(BD_ON + 10, -300.0 + 0.1, 10)]
    u_end = float((A2 - s_pt) @ _dir(th))
    return [tuple(q) for q in pts], dict(
        curve_radius_m=R_C, curve_deg=round(float(np.degrees(abs(dl))), 1), curve_from=[round(float(q), 1) for q in A1],
        straight_heading_deg=round(float(np.degrees(th)), 2), straight_m=round(float(L)), curve_ends_past_straight_station_m=round(u_end, 1),
        box_bend_deg=round(float(np.degrees(hU - th)), 1), box_radius_m=R_BD, on_axis_s=BD_ON)

def zone():
    """Where the line tracks are replaced: a band along the box axis plus the B/D curve into it."""
    return Polygon([at(-620, 60), at(S_E + 140, 45), at(S_E + 140, -75), at(-620, -75)])   # wide on the south so the trunk's bend is inside

def build(TRK, PLT, r1):
    """Replace the automatic A/B/D tracks and platforms in the zone with the box. Returns crossing marks."""
    Z = zone()
    keep, ends = [], []
    for i, t in enumerate(TRK):
        if t['sys'] != 'rer' or not set(t['line'].split()) & {'A', 'B', 'D'} or t['line'] == 'B D':   # the B/D approach ends where the box starts
            keep.append(t); continue
        g = LineString(t['c'])
        if not g.intersects(Z): keep.append(t); continue
        rest = g.difference(Z)
        for part in getattr(rest, 'geoms', [rest]):
            if part.geom_type != 'LineString' or part.length < 20: continue
            c = [list(q) for q in part.coords]; keep.append(dict(t, c=[r1(q) for q in c]))
            for e, q in ((0, c[0]), (-1, c[-1])):          # ends that touch the zone are the hand-over points
                if Z.buffer(1).contains(Point(q)):
                    inn = np.array(c[1] if e == 0 else c[-2]); p = np.array(q)
                    ends.append(dict(line=t['line'], p=p, t_in=unit(p - inn), pair=i // 2))   # t_in points into the zone; pair = the piece
    TRK[:] = keep
    PLT[:] = [p for p in PLT if not (p['sys'] == 'rer' and set(p['line'].split()) & {'A', 'B', 'D'} and Polygon(p['c']).intersects(Z))]
    def hand(near, line_has, side, east):
        """The line track end at the zone edge near 'near': side +1 westbound (left of the eastbound direction), -1 eastbound."""
        cand = [e for e in ends if set(e['line'].split()) >= set(line_has) and np.linalg.norm(e['p'] - np.asarray(near)) < 70]
        cand.sort(key=lambda e: np.linalg.norm(e['p'] - np.asarray(near)))
        pair = [e for e in cand if e['pair'] == cand[0]['pair']][:2]
        mid = (pair[0]['p'] + pair[1]['p']) / 2
        De = -pair[0]['t_in'] if east else pair[0]['t_in']; L_ = np.array([-De[1], De[0]])
        return max(pair, key=lambda e: side * ((e['p'] - mid) @ L_))
    new = []
    def add(name, pts, line): new.append(dict(sys='rer', line=line, name=name, c=[r1(q) for q in pts]))
    # ------------------------------------------------ west: A pair from Evans; B/D pair from Western on the axis from BD_ON
    # A's tracks open round the B/D pair (A westbound 4.5 m north of it, A eastbound south), A westbound is crossed where B/D
    # bend north, A eastbound stays south and rejoins A's line once B/D are clear.
    aw_pts = {}
    a_near = (712580.0, 4331928.0)
    for nm, s_rej, h_out in (('A wb', -420.0, 6.75), ('A eb', -470.0, -6.75)):
        e = hand(a_near, ['A'], 1 if nm == 'A wb' else -1, False)
        con = bez(e['p'], e['t_in'], at(s_rej, h_out), U, k=0.40)
        aw_pts[nm] = con[:-1] + track([(s_rej, h_out), (-300.0, h_out), (-S_BOX, OFF[nm]), (S_BOX, OFF[nm])])
    # B takes the B/D line track into the box; D leaves it at a turnout where B has opened out to D's offset
    for b_nm, d_nm, side in (('B wb', 'D wb', 1), ('B eb', 'D eb', -1)):
        ctrl = [(-300.0, 2.25 * side), (-S_BOX, OFF[b_nm]), (S_BOX, OFF[b_nm])]
        aw_pts[b_nm] = track(ctrl)
        s_t = -215.0; h_t = ease(ctrl[0][1], ctrl[1][1], (s_t - ctrl[0][0]) / (ctrl[1][0] - ctrl[0][0]))
        aw_pts[d_nm] = track([(s_t, h_t), (-S_BOX, OFF[d_nm]), (S_BOX, OFF[d_nm])])
    # ------------------------------------------------ east: B straight on north of the trunk; A and D merge onto the A/D trunk
    # The A/D trunk and the B line share one KMZ line for the first 250 m east of the box; the A/D pair runs south of B
    # until the trunk bends away. Every crossing is B against A/D and all of them lie 250-330 m out, so the B pair can
    # change level once, clear of the platforms.
    TRUNK = LineString([(713024, 4331860), (713405, 4331835), (713490, 4331828), (713576, 4331812), (713658, 4331790), (713741, 4331760)])
    BLINE = LineString([(713144, 4331855), (714062, 4331794)])
    def h_of(line, s_):
        x = line.intersection(LineString([at(s_, -80), at(s_, 80)]))
        return float((np.array([x.x, x.y]) - C0) @ N_)
    ht, hb = h_of(TRUNK, S_E), h_of(BLINE, S_E)
    AD_WB, AD_EB, B_WB, B_EB = ht + 2.25, ht - 2.25, hb + 2.25, hb - 2.25
    east = {
        'B wb': [(S_BOX, OFF['B wb']), (S_E, B_WB)],
        'B eb': [(S_BOX, OFF['B eb']), (300.0, OFF['B eb']), (440.0, B_EB), (S_E, B_EB)],      # north across D eastbound
        'D wb': [(S_BOX, OFF['D wb']), (330.0, OFF['D wb']), (S_E, AD_WB)],                     # south across B eastbound
        'D eb': [(S_BOX, OFF['D eb']), (360.0, OFF['D eb']), (S_E, AD_EB)],
    }
    full = {nm: aw_pts[nm] + track(ctrl)[1:] for nm, ctrl in east.items()}
    # A westbound comes in across B westbound to D westbound's straight (turnout at 330 m); A eastbound runs into D eastbound
    full['A wb'] = aw_pts['A wb'] + track([(S_BOX, OFF['A wb']), (180.0, OFF['A wb']), (330.0, OFF['D wb'])])[1:]
    c = east['D eb']; hDe = lambda s_: ease(c[1][1], c[2][1], (s_ - c[1][0]) / (c[2][0] - c[1][0]))
    full['A eb'] = aw_pts['A eb'] + track([(S_BOX, OFF['A eb']), (330.0, OFF['A eb']), (470.0, hDe(470.0))])[1:]
    # hand-over to the line tracks east of the zone
    for nm, line_has, near in (('B wb', ['B'], at(S_E + 140, h_of(BLINE, S_E + 140))), ('B eb', ['B'], at(S_E + 140, h_of(BLINE, S_E + 140))),
                               ('D wb', ['A', 'D'], (713790.0, 4331740.0)), ('D eb', ['A', 'D'], (713790.0, 4331740.0))):
        e = hand(near, line_has, 1 if 'wb' in nm else -1, True)
        full[nm] = full[nm] + bez(full[nm][-1], U, e['p'], -e['t_in'])[1:]
    labels = {'A wb': ('A', 'RER A westbound (Evans)'), 'A eb': ('A', 'RER A eastbound (City Hall)'),
              'D wb': ('D', 'RER D westbound (Western, Norwood)'), 'D eb': ('D', 'RER D eastbound (City Hall, Newport)'),
              'B wb': ('B', 'RER B westbound (Western, Dayton)'), 'B eb': ('B', 'RER B eastbound (Music Hall, Falmouth)')}
    for nm, pts in full.items(): add(labels[nm][1], pts, labels[nm][0])
    TRK.extend(new)
    # ------------------------------------------------ islands
    for nm, h in ISLANDS.items():
        a, b = -PL / 2, PL / 2
        ring = [at(a, h + ISL / 2), at(b, h + ISL / 2), at(b, h - ISL / 2), at(a, h - ISL / 2), at(a, h + ISL / 2)]
        PLT.append(dict(sys='rer', line='A B' if 'A/B' in nm or 'B/A' in nm else 'D', name=f'Union Terminal, {nm} island', c=[r1(q) for q in ring]))
    # ------------------------------------------------ grade-separated crossings
    G = {nm: LineString(p) for nm, p in full.items()}
    for k_, t in enumerate([t for t in TRK if t['line'] == 'B D']): G[f'BD approach {k_}'] = LineString(t['c'])
    marks = []
    def cross(a_list, b_list, label, where, anchor):
        pts = []
        for a in a_list:
            for b in b_list:
                x = G[a].intersection(G[b])
                for q in getattr(x, 'geoms', [x]):
                    if q.geom_type == 'Point' and (where(q)): pts.append(np.array([q.x, q.y]))
        if pts:
            m = np.mean(pts, axis=0); marks.append(dict(p=r1(m), label=label, n=len(pts), anchor=anchor, s=round(float((m - C0) @ U), 1)))
    sx = lambda q: (np.array([q.x, q.y]) - C0) @ U
    cross([k for k in G if k.startswith('BD approach')] + ['B wb', 'B eb'], ['A wb'], 'A westbound crosses B/D, separate levels', lambda q: sx(q) < -S_BOX, 'left')
    cross(['B eb'], ['D eb'], 'B eastbound crosses D eastbound', lambda q: sx(q) > S_BOX, 'right')
    cross(['A wb'], ['B wb'], 'A westbound crosses B westbound', lambda q: sx(q) > S_BOX, 'right')
    cross(['D wb'], ['B eb'], 'A/D westbound crosses B eastbound', lambda q: sx(q) > S_BOX, 'right')
    for m in marks: m['kind'] = 'cross'
    # direction labels on the platform tracks (zoomed in)
    for nm, txt in (('A wb', '\u2190 A Evans'), ('B wb', '\u2190 B Western, Dayton'), ('D wb', '\u2190 D Western, Norwood'),
                    ('D eb', 'D City Hall, Newport \u2192'), ('B eb', 'B Music Hall, Falmouth \u2192'), ('A eb', 'A City Hall \u2192')):
        s_lab = {'A wb': -60, 'B wb': -80, 'D wb': -40, 'D eb': 40, 'B eb': 80, 'A eb': 60}[nm]    # staggered: B and D run 4.5 m apart
        marks.append(dict(kind='dir', p=r1(at(s_lab, OFF[nm])), label=txt))
    return marks, dict(offsets={k: round(v, 2) for k, v in OFF.items()}, islands={k: round(v, 2) for k, v in ISLANDS.items()},
                       platform_m=PL, island_m=ISL, span_m=round(OFF['A wb'] - OFF['A eb'], 2), heading_deg=round(float(np.degrees(np.arctan2(U[1], U[0]))), 2))
