try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# CVG Express terminal alignment options (discussion only). Straights joined by circular arcs; stations 150 m.
import json, math, numpy as np
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from shapely.geometry import LineString, Point, Polygon
S = _ws.DATA
A = json.load(open(S + 'deckpage/airport.json'))['features']
T = json.load(open(S + 'deckpage/tracks.json')); C = json.load(open(S + 'deckpage/context.json'))
K = json.load(open(S + 'ludlow/kmz_south.json'))['TRIMET_Lines.kmz']; OLD = np.array([r for r in K if r['name'] == 'CVG Express 3D'][0]['c'], float)
W = [f['geometry']['coordinates'] for f in T['features'] if f['properties'].get('kind') == 'cvg' and 'west track' in f['properties'].get('name', '') and f['geometry']['type'] == 'LineString']
cur = []
for c in W:
    for q in c:
        if not cur or math.dist(cur[-1], q) > 0.5:
            if cur and len(cur) > 2 and math.dist(cur[-2], q) < math.dist(cur[-2], cur[-1]): continue
            cur.append(tuple(q))
CUR = LineString(cur)
J = (707194.0, 4323703.0); sJ = CUR.project(Point(J)); Jp = CUR.interpolate(sJ).coords[0]
hJ = np.subtract(CUR.interpolate(sJ + 20).coords[0], CUR.interpolate(sJ - 20).coords[0]); hJ /= np.linalg.norm(hJ)
s_end = CUR.length
def fillet(V, R):
    """V: vertices; R: radius at each interior vertex. Returns dense polyline and list of (radius, turn deg)."""
    V = [np.array(v, float) for v in V]; out = [V[0]]; info = []
    for i in range(1, len(V) - 1):
        a, b, c = V[i - 1], V[i], V[i + 1]; u = (a - b) / np.linalg.norm(a - b); w = (c - b) / np.linalg.norm(c - b)
        th = math.acos(np.clip(np.dot(u, w), -1, 1)); turn = math.pi - th; t = R[i - 1] * math.tan(turn / 2)
        p1, p2 = b + u * t, b + w * t; bis = (u + w) / np.linalg.norm(u + w); cen = b + bis * (R[i - 1] / math.sin(th / 2))
        a1, a2 = math.atan2(*(p1 - cen)[::-1]), math.atan2(*(p2 - cen)[::-1]); d = (a2 - a1 + math.pi) % (2 * math.pi) - math.pi
        out += [cen + R[i - 1] * np.array([math.cos(a1 + d * k / 40), math.sin(a1 + d * k / 40)]) for k in range(41)]
        info.append((R[i - 1], round(math.degrees(turn)), round(t)))
    out.append(V[-1]); return LineString(out), info
Y_TAIL = 4326070.0                                    # the T1B and T1A nodes (the bumps on their piers) are both at about this northing
X1, X2 = 702818.0, 703155.0                           # T3's node; T4's east pier
Jfar = tuple(np.array(Jp) + hJ * 250)                 # leave the RER corridor tangentially just past J
opts = {
 '1: centre spine (E 702,820)': dict(V=[Jp, Jfar, (X1, 4324500), (X1, Y_TAIL), (701150, Y_TAIL)], R=[1500, 400, 400],
     st=[('T3', (X1, 4324985)), ('T2', (X1, 4325310)), ('T4', (X1, 4325560)), ('T1B', (702050, Y_TAIL)), ('T1A', (701400, Y_TAIL))]),
 '1b: centre spine, T2 and T4 one stop': dict(V=[Jp, Jfar, (X1, 4324500), (X1, Y_TAIL), (701150, Y_TAIL)], R=[1500, 400, 400],
     st=[('T3', (X1, 4324985)), ('T2/T4', (X1, 4325431)), ('T1B', (702050, Y_TAIL)), ('T1A', (701400, Y_TAIL))]),
 '2: east spine (under T4\'s east pier)': dict(V=[Jp, Jfar, (X2, 4324540), (X2, Y_TAIL), (701150, Y_TAIL)], R=[1500, 400, 300],
     st=[('T3', (X2, 4324985)), ('T2', (X2, 4325310)), ('T4', (X2, 4325690)), ('T1B', (702050, Y_TAIL)), ('T1A', (701400, Y_TAIL))]),
}
bld = {f['properties']['name']: Polygon(f['geometry']['coordinates'][0]) for f in A if f['properties']['layer'] == 'cvg_building'}
key = {'T1A': 'Terminal 1A', 'T1B': 'Terminal 1B', 'T2': 'Terminal 2', 'T3': 'Terminal 3', 'T4': 'Terminal 4'}
def farwalk(stop, P):                                  # straight-line distance from the stop to the farthest point of that building (a floor for walking)
    return max(math.dist(P, q) for q in bld[key[stop]].exterior.coords)
def runtime(d, a=0.8, vmax=22.2):                      # stop to stop, accelerate and brake at a, capped at vmax (80 km/h)
    if d <= vmax ** 2 / a: return 2 * math.sqrt(d / a)
    return 2 * vmax / a + (d - vmax ** 2 / a) / vmax
res = {}
fig, axs = plt.subplots(3, 1, figsize=(13, 19.5))
for ax, (nm, o) in zip(axs, opts.items()):
    g, info = fillet(o['V'], o['R'])
    sts = [(lab, g.project(Point(p))) for lab, p in o['st']]
    sp = [round(sts[i + 1][1] - sts[i][1]) for i in range(len(sts) - 1)]
    walks = {}
    for lab, p in o['st']:
        for t in lab.split('/'): walks[t] = round(farwalk(t, p))
    tin = sum(runtime(d) for d in sp) + 30 * (len(sp))  # running between stops plus a 30 s dwell at each intermediate stop and at the last
    res[nm] = dict(J_to_first=round(sts[0][1]), J_to_T1A=round(sts[-1][1]), cut_to_first_km=round((sJ + sts[0][1] - 0) / 1000, 1), spacing=sp, curves=info,
                   first_to_last_min=round(tin / 60, 1), far_gate_m=walks, kmz_to_end_from_J=round(s_end - sJ))
    for f in A:
        p = f['properties']; L = p['layer']
        if f['geometry']['type'] != 'Polygon': continue
        xs, ys = zip(*f['geometry']['coordinates'][0])
        if L == 'cvg_runway': ax.fill(xs, ys, color='#a9b7ba', zorder=1)
        elif L == 'cvg_building': ax.fill(xs, ys, color='#8a5aa8', alpha=0.85, zorder=2)
        else: ax.fill(xs, ys, color='#e4e4e4', alpha=0.6, zorder=0)
    for lab, nmb in key.items():
        c = bld[nmb].representative_point(); ax.text(*{'T1A': (700900, 4325800), 'T1B': (701700, 4325600), 'T2': (702200, 4325200), 'T3': (702050, 4324770), 'T4': (703250, 4325900)}[lab], lab, fontsize=9, color='#5a2d7a', zorder=6)
    for r in C['rer']:
        c = np.array([q[:2] for q in r['c']])
        ax.plot(c[:, 0], c[:, 1], color='#d07a1c', lw=1.6, zorder=3)
    ax.plot(OLD[:, 0], OLD[:, 1], color='#7a7a7a', lw=1.2, ls=(0, (4, 3)), zorder=3)
    ax.plot(*np.array(cur).T, color='#1f78b4', lw=1, alpha=0.6, zorder=4)
    P = np.array(g.coords); ax.plot(P[:, 0], P[:, 1], color='#1f78b4', lw=2.8, zorder=5)
    for lab, s in sts:
        q = np.array(g.interpolate(s).coords[0]); d = np.subtract(g.interpolate(s + 1).coords[0], q); d /= np.linalg.norm(d)
        a, b = q - d * 75, q + d * 75; ax.plot([a[0], b[0]], [a[1], b[1]], color='k', lw=7, solid_capstyle='butt', zorder=7)
        ax.text(q[0] + (40 if abs(d[1]) > 0.5 else -30), q[1] + (0 if abs(d[1]) > 0.5 else 55), lab, fontsize=10, weight='bold', zorder=8, va='center')
    ax.set_title(f"Option {nm}:  J to T1A {sts[-1][1]/1000:.1f} km; stops {', '.join(map(str, sp))} m apart", fontsize=10)
    ax.set_xlim(700700, 707400); ax.set_ylim(4323450, 4326600); ax.set_aspect('equal'); ax.tick_params(labelsize=7)
    ax.plot(*J, 'o', color='#1f78b4', zorder=9); ax.text(J[0], J[1] - 120, 'J: leaves the RER', fontsize=8, ha='center')
fig.suptitle('Blue: CVG Express (thick: option; thin: now, beside the RER to the end of the KMZ line). Orange: RER (landside). Grey dashes: the 1969 CVG Express (TRIMET), ending under the south side of the T1B-T4 U. Black: 150 m stations.\nRunways in grey (150 ft). Stations at the T1A and T1B pier nodes, T3\'s node and mid-T2.', fontsize=10, y=0.995)
fig.tight_layout(rect=(0, 0, 1, 0.985))
fig.savefig(S + 'cvg/cvg_express_terminal_options.png', dpi=105, bbox_inches='tight')
print(json.dumps(res, indent=1)); print('sJ', round(sJ), 'cur len', round(CUR.length))
