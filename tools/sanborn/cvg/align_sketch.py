try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Sketch alignments for the CVG Express through the terminals (discussion only, nothing published).
import json, math, numpy as np
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from shapely.geometry import LineString, Polygon, Point, box
S = _ws.DATA
A = json.load(open(S + 'deckpage/airport.json'))['features']
T = json.load(open(S + 'deckpage/tracks.json'))
C = json.load(open(S + 'deckpage/context.json'))
def chaikin(P, it=6):
    P = np.asarray(P, float)
    for _ in range(it):
        Q = [P[0]]
        for a, b in zip(P[:-1], P[1:]): Q += [0.75 * a + 0.25 * b, 0.25 * a + 0.75 * b]
        Q.append(P[-1]); P = np.asarray(Q)
    return P
def minrad(P, k=6):
    r = 1e9; P = np.asarray(LineString(P).segmentize(5).coords)
    for i in range(k, len(P) - k):
        a, b, c = P[i - k], P[i], P[i + k]; ab, bc, ac = np.linalg.norm(b - a), np.linalg.norm(c - b), np.linalg.norm(c - a)
        cr = abs((b - a)[0] * (c - a)[1] - (b - a)[1] * (c - a)[0])
        if cr > 1e-6: r = min(r, ab * bc * ac / (2 * cr))
    return r
END = (705253.0, 4325600.0)
# Concept 1: south entry, spine at mid-length of T2/T3 (x 702650): T3, T2, T4 (in the U, by its south leg), then west: T1B, T1A
c1 = [END, (704700, 4325350), (704000, 4324800), (703300, 4324700), (702800, 4324700), (702650, 4324780), (702650, 4325000), (702650, 4325400),
      (702650, 4325700), (702600, 4325900), (702400, 4325980), (702050, 4325980), (701800, 4325980), (701400, 4325980), (701150, 4325980)]
st1 = [('T3', (702650, 4324938), 90), ('T2', (702650, 4325310), 90), ('T4', (702650, 4325700), 90), ('T1B', (702040, 4325980), 0), ('T1A', (701410, 4325980), 0)]
# Concept 2: south entry, spine at the east third (x 703050): T3, T2, T4 (beside its east leg), then west across the north of the U: T1B, T1A
c2 = [END, (704600, 4325200), (703900, 4324760), (703300, 4324700), (703120, 4324760), (703050, 4324900), (703050, 4325300), (703050, 4325700),
      (703050, 4325950), (702950, 4326120), (702700, 4326150), (702040, 4326150), (701400, 4326150), (701150, 4326150)]
st2 = [('T3', (703050, 4324938), 90), ('T2', (703050, 4325310), 90), ('T4', (703050, 4325760), 90), ('T1B', (702040, 4326150), 0), ('T1A', (701410, 4326150), 0)]
fig, axs = plt.subplots(1, 2, figsize=(16, 8.5))
out = {}
for ax, (nm, ctrl, sts) in zip(axs, (('Concept 1: spine at mid-concourse (x 702,650)', c1, st1), ('Concept 2: spine at the east end (x 703,050)', c2, st2))):
    P = chaikin(ctrl, 6); g = LineString(P)
    for f in A:
        p = f['properties']; L = p['layer']
        if f['geometry']['type'] != 'Polygon': continue
        xs, ys = zip(*f['geometry']['coordinates'][0])
        if L == 'cvg_runway': ax.fill(xs, ys, color='#9fb0b3', zorder=1)
        elif L == 'cvg_building': ax.fill(xs, ys, color='#8a5aa8', alpha=0.85, zorder=2); ax.text(np.mean(xs), np.mean(ys) + 70, p['name'].replace('Terminal ', 'T'), fontsize=8, ha='center', zorder=6)
        else: ax.fill(xs, ys, color='#ddd', alpha=0.5, zorder=0)
    for r in C['rer']:
        c = np.array([q[:2] for q in r['c']]); 
        if c[:, 0].min() < 706000 and c[:, 1].min() < 4327500: ax.plot(c[:, 0], c[:, 1], color='#d07a1c', lw=1.5, zorder=3)
    for f in T['features']:
        if f['properties'].get('kind') == 'cvg' and f['geometry']['type'] == 'LineString':
            c = np.array(f['geometry']['coordinates']); ax.plot(c[:, 0], c[:, 1], color='#1f78b4', lw=1, zorder=4)
    ax.plot(P[:, 0], P[:, 1], color='#1f78b4', lw=2.5, zorder=5)
    sp = []
    for lab, (x, y), ang in sts:
        s = g.project(Point(x, y)); q = g.interpolate(s); q2 = g.interpolate(min(g.length, s + 1)); d = np.subtract(q2.coords[0], q.coords[0]); d /= np.linalg.norm(d)
        a, b = np.array(q.coords[0]) - d * 75, np.array(q.coords[0]) + d * 75
        ax.plot([a[0], b[0]], [a[1], b[1]], color='k', lw=7, solid_capstyle='butt', zorder=7); ax.text(b[0] + 25, b[1] + 25, lab, fontsize=10, weight='bold', zorder=8)
        sp.append((lab, s))
    gaps = [(sp[i][0] + '-' + sp[i + 1][0], round(sp[i + 1][1] - sp[i][1])) for i in range(len(sp) - 1)]
    out[nm] = dict(length_to_T1A=round(sp[-1][1]), first_stop=round(sp[0][1]), gaps=gaps, r_min=round(minrad(P)))
    ax.set_title(nm + f"\n{sp[-1][1]/1000:.1f} km from the KMZ end to T1A; tightest curve about {out[nm]['r_min']:.0f} m", fontsize=10)
    ax.set_xlim(700500, 705600); ax.set_ylim(4324300, 4326700); ax.set_aspect('equal'); ax.tick_params(labelsize=7)
    ax.text(705253, 4325640, 'end of the KMZ line', fontsize=8, ha='right')
fig.text(0.5, 0.02, 'Black bars: 150 m stations. Orange: RER (landside). Thin blue: CVG Express as drawn now. Grey: runways (150 ft).', ha='center', fontsize=9)
fig.savefig(S + 'cvg/cvg_align_concepts.png', dpi=110, bbox_inches='tight')
print(json.dumps(out, indent=1))
