try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Ben's sketch on option B: the boulevard forks before M3 and rejoins after M6 with two gentle curves; diamond-shaped park between;
# nothing crosses between M3 and M6 (M4, M5 end at the park roads); Follett meets the park at its west (M3) and east (M6) corners.
import json, sys, numpy as np, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from shapely.geometry import LineString, Polygon, Point
from shapely.ops import substring, unary_union, polygonize
SP=_ws.DATA
exec(open(_ws.CODE+'millvale/m3m6_options.py').read().split("fig,axs=plt.subplots")[0])
CW = 14.0; L = 95.0
s3 = B.project(pB3); s6 = B.project(pB6)
def tan(s): p = np.array(B.interpolate(s).coords[0]); q = np.array(B.interpolate(s + 1).coords[0]); return (q - p) / np.linalg.norm(q - p)
def bez(p0, t0, p1, t1, k=0.4):
    p0, p1 = np.array(p0), np.array(p1); d = np.linalg.norm(p1 - p0); c0 = p0 + t0 * d * k; c1 = p1 - t1 * d * k
    u = np.linspace(0, 1, 40)[:, None]; return LineString((1 - u) ** 3 * p0 + 3 * (1 - u) ** 2 * u * c0 + 3 * (1 - u) * u ** 2 * c1 + u ** 3 * p1)
W3, NE, SE, SW = np.array(pF3.coords[0]), np.array(pB3.coords[0]), np.array(pF6.coords[0]), np.array(pB6.coords[0])
dW = (SW - W3) / np.linalg.norm(SW - W3); dE = (SE - NE) / np.linalg.norm(SE - NE)
Nf = np.array(B.interpolate(s3 - L).coords[0]); Sm = np.array(B.interpolate(s6 + L).coords[0])
link1 = bez(Nf, tan(s3 - L), W3, dW)
link2 = bez(SE, dE, Sm, tan(s6 + L))
west = LineString(list(link1.coords) + [tuple(SW)] + list(substring(B, s6, s6 + L).coords)[1:])
east = LineString(list(substring(B, s3 - L, s3).coords) + [tuple(SE)] + list(link2.coords)[1:])
park_face = [q for q in polygonize(unary_union([west, east])) if q.contains(hull.centroid)][0]
park = park_face.difference(unary_union([west.buffer(CW / 2), east.buffer(CW / 2)]))
SD = []
for n, g, w in ST:
    if n == 'Millvale Boulevard':
        for q in (substring(g, 0, s3 - L), substring(g, s6 + L, g.length)): SD.append((n, q, w)); 
        continue
    if n == 'Follett Avenue (carried south)':
        g = g.difference(park_face.buffer(-0.5))
    if n in ('New street M3', 'New street M4', 'New street M5', 'New street M6'):
        g = g.difference(park_face.buffer(CW / 2))          # nothing crosses between M3 and M6 (Ben)
    for q in getattr(g, 'geoms', [g]):
        if q.geom_type == 'LineString' and q.length > 3: SD.append((n, q, w))
SD += [('Millvale Boulevard (south-west-bound)', west, CW), ('Millvale Boulevard (north-east-bound)', east, CW)]
bD, bandsD = blocks(SD, extra=park_face)
if '--plot' in sys.argv:
    fig, ax = plt.subplots(figsize=(9.5, 9.5))
    draw(ax, SD, bD, bandsD, "Your sketch: the boulevard forks round a diamond park", park=park,
         signals=[tuple(W3), tuple(SE)] + [B.intersection(G[f'New street M{k}'][0]).coords[0] for k in (2, 7)],
         notes=['Fork before M3, rejoin after M6, one gentle curve each way, no signals between M2 and M7 except Follett; park %.2f ha, %d m long' % (park.area / 1e4, round(Point(Nf).distance(Point(Sm)))),
                'South-west-bound on the west side (Follett north joins at the M3 corner), north-east-bound on the east (Follett south joins at M6)',
                'M3 to M6 end at the park roads (right in, right out); through Follett traffic goes round by M2 or M7, one block'])
    for line, a, b in ((west, 0.55, 0.62), (east, 0.55, 0.48)):
        p, q = line.interpolate(a, normalized=True), line.interpolate(b, normalized=True)
        ax.annotate('', xy=(q.x, q.y), xytext=(p.x, p.y), arrowprops=dict(arrowstyle='-|>', color='k', lw=1.3))
    for nm, pt in (('fork', Nf), ('rejoin', Sm)): ax.text(pt[0] + 8, pt[1], nm, fontsize=8)
    h=[plt.Line2D([],[],color='#2a6fd6',ls=(0,(4,3)),label='culverts'),plt.Rectangle((0,0),1,1,fc='none',ec='#c0392b',hatch='////',label='viaducts (no blocks under)'),
       plt.Line2D([],[],marker='o',ls='',mfc='#f1c40f',mec='k',label='signalled junction'),plt.Rectangle((0,0),1,1,fc='#7fc27f',ec='#2f7d2f',label='park')]
    ax.legend(handles=h, loc='upper right', fontsize=7)
    plt.tight_layout(); plt.savefig(SP + 'millvale/m3m6_diamond.png', dpi=100)
    print('park ha', round(park.area / 1e4, 2))
