try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Ben: the diamond park, and the boulevard's 150 ft (the culvert) stays inside the park and its roads: the two one-way sides run outside the
# 150 ft band (blocks never reach it), forking between M2 and M3 and rejoining between M6 and M7, with Follett meeting them at the west (M3)
# and east (M6) corners; nothing crosses between M3 and M6.
import json, sys, numpy as np, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from shapely.geometry import LineString, Polygon, Point
from shapely.ops import substring, unary_union, polygonize
SP=_ws.DATA
exec(open(_ws.CODE+'millvale/m3m6_options.py').read().split("fig,axs=plt.subplots")[0])
CW = bw / 2; HALF = bw / 2                               # each arm is half the boulevard (75 ft: 3 lanes, a parking/loading lane, sidewalk and trees, as on the boulevard itself); 22.86 m
S_F, S_R = 1150.0, 1510.0                                 # fork and rejoin (along the boulevard line)
D0 = HALF - CW / 2                                        # 15.9 m: a side's centre where it sits in the boulevard's own outer lanes
sW, oW = B.project(pF3), pF3.distance(B.interpolate(B.project(pF3)))
sE, oE = B.project(pF6), pF6.distance(B.interpolate(B.project(pF6)))
def frame(s):
    p = np.array(B.interpolate(s).coords[0]); q = np.array(B.interpolate(s + 1).coords[0]); t = (q - p) / np.linalg.norm(q - p); return p, np.array([-t[1], t[0]])
def side(sign, knots):
    ss = np.linspace(S_F, S_R, 300); ks, ko = zip(*knots); off = np.interp(ss, ks, ko)
    off = np.convolve(np.r_[[off[0]] * 6, off, [off[-1]] * 6], np.ones(13) / 13, 'valid')     # round the corners a little
    pts = [frame(s)[0] + sign * frame(s)[1] * o for s, o in zip(ss, off)]
    return LineString(pts), ss, off
west, ssw, offw = side(-1, [(S_F, D0), (sW, oW), (S_R, D0)])          # left of travel is south-east, so west is -1
east, sse, offe = side(+1, [(S_F, D0), (sE, oE), (S_R, D0)])
# snap the corners exactly onto Follett's ends
west = LineString([c if Point(c).distance(pF3) > 6 else pF3.coords[0] for c in west.coords]); east = LineString([c if Point(c).distance(pF6) > 6 else pF6.coords[0] for c in east.coords])
cap = lambda s: LineString([frame(s)[0] - frame(s)[1] * D0, frame(s)[0] + frame(s)[1] * D0])
face = Polygon(list(west.coords) + list(east.coords)[::-1]).buffer(0)
park = face.difference(unary_union([west.buffer(CW / 2), east.buffer(CW / 2)]))
SD = []
for n, g, w in ST:
    if n == 'Millvale Boulevard':
        for q in (substring(g, 0, S_F), substring(g, S_R, g.length)): SD.append((n, q, w))
        continue
    if n in ('Follett Avenue (carried south)', 'New street M3', 'New street M4', 'New street M5', 'New street M6'): g = g.difference(face)      # run to the arm's centre line: a square T
    for q in getattr(g, 'geoms', [g]):
        if q.geom_type == 'LineString' and q.length > 3: SD.append((n, q, w))
SD += [('Millvale Boulevard (south-west-bound)', west, CW), ('Millvale Boulevard (north-east-bound)', east, CW)]
bD, bandsD = blocks(SD, extra=face.buffer(0.1))
band = B.buffer(HALF, cap_style=2)
over = sum(b.intersection(band).area for b in bD)
print('park ha %.2f, tip to tip %d m, max width %.0f m, blocks over the 150 ft band %.1f m2, sides min offset %.1f m' % (park.area / 1e4, S_R - S_F, (offw + offe).max(), over, min(offw.min(), offe.min())))
if '--plot' in sys.argv:
    fig, ax = plt.subplots(figsize=(9.5, 9.5))
    x, y = band.intersection(W).exterior.xy if band.intersection(W).geom_type == 'Polygon' else ([], [])
    draw(ax, SD, bD, bandsD, 'Diamond park: the 150 ft boulevard band stays in the park and its roads', park=park,
         signals=[pF3.coords[0], pF6.coords[0]] + [B.intersection(G[f'New street M{k}'][0]).coords[0] for k in (2, 7)],
         notes=['Fork between M2 and M3, rejoin between M6 and M7; park %.2f ha, %d m tip to tip, up to %.0f m wide' % (park.area / 1e4, S_R - S_F, (offw + offe).max() - CW),
                'South-west-bound on the west side, north-east-bound on the east; Follett meets them at the M3 and M6 corners',
                'No block touches the 150 ft band (black dotted); M3 to M6 end at the park roads'])
    ax.plot(x, y, 'k:', lw=1.2)
    for line, a, b in ((west, 0.55, 0.62), (east, 0.55, 0.48)):
        p, q = line.interpolate(a, normalized=True), line.interpolate(b, normalized=True)
        ax.annotate('', xy=(q.x, q.y), xytext=(p.x, p.y), arrowprops=dict(arrowstyle='-|>', color='k', lw=1.3))
    h=[plt.Line2D([],[],color='#2a6fd6',ls=(0,(4,3)),label='culverts'),plt.Line2D([],[],color='k',ls=':',label='150 ft boulevard band (culvert)'),plt.Rectangle((0,0),1,1,fc='none',ec='#c0392b',hatch='////',label='viaducts (no blocks under)'),
       plt.Line2D([],[],marker='o',ls='',mfc='#f1c40f',mec='k',label='signalled junction'),plt.Rectangle((0,0),1,1,fc='#7fc27f',ec='#2f7d2f',label='park')]
    ax.legend(handles=h, loc='upper right', fontsize=7)
    plt.tight_layout(); plt.savefig(SP + 'millvale/m3m6_diamond2.png', dpi=100)
