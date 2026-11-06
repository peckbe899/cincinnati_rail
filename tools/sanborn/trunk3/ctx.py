try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, sys, numpy as np, matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from shapely.geometry import LineString, Point, Polygon, box, shape
SP = _ws.DATA
sys.path.insert(0, _ws.CODE + 'trunk2')
from creek_up import WAT_UP as WAT
import geo4 as Q
BJ = json.load(open(SP + 'deckpage/basin.json')); H = json.load(open(SP + 'deckpage/hwy.json'))
T = json.load(open(SP + 'deckpage/tracks.json')); C = json.load(open(SP + 'deckpage/context.json')); NW = json.load(open(SP + 'deckpage/norwood.json'))
def draw(x0, x1, y0, y1, fn, w=16):
    Bx = box(x0, y0, x1, y1); fig, ax = plt.subplots(figsize=(w, w * (y1 - y0) / (x1 - x0)))
    for f in BJ['features']:
        p = f['properties']; g = shape(f['geometry'])
        if not g.intersects(Bx): continue
        if p.get('layer') == 'block' and g.geom_type == 'Polygon': ax.fill(*g.exterior.xy, color='#eeeeee', lw=0)
        if p.get('layer') == 'street' and g.geom_type == 'LineString':
            gg = g.buffer(p.get('width_m', 12) / 2, cap_style=2)
            for qq in getattr(gg, 'geoms', [gg]): ax.fill(*qq.exterior.xy, color='#d0d0d0', lw=0)
    for f in H['features']:
        if f['properties'].get('layer') == 'hw_piece':
            g = shape(f['geometry'])
            if g.intersects(Bx):
                gg = g.buffer(f['properties']['w'] / 2, cap_style=2)
                for qq in getattr(gg, 'geoms', [gg]): ax.fill(*qq.exterior.xy, color='#f6d5e4', lw=0)
    for qq in getattr(WAT, 'geoms', [WAT]):
        if qq.intersects(Bx): ax.fill(*qq.exterior.xy, color='#9ecae1', lw=0)
    for f in T['features']:
        g = f['geometry']; p = f['properties']
        if g['type'] != 'LineString': continue
        c = np.array(g['coordinates'])[:, :2]
        if not LineString(c).intersects(Bx): continue
        col = {'apex': 'k', 'lower': '#c2185b'}.get(p.get('layer'), '#888')
        ax.plot(c[:, 0], c[:, 1], color=col, lw=0.6)
    for t in C['tracks']:
        c = np.array(t['c'])
        if LineString(c).intersects(Bx): ax.plot(c[:, 0], c[:, 1], color='#ef6c00' if t.get('sys', 'rer') != 'metro' else '#2e7d32', lw=0.5)
    for f in NW['features']:
        g = f['geometry']
        if g['type'] == 'LineString': c = np.array(g['coordinates']); ax.plot(c[:, 0], c[:, 1], color='#1565c0', lw=0.6)
    for s in C['rer_stations'] + C['stations']:
        p = s['p']
        if Bx.contains(Point(p)): ax.plot(*p, 'o', ms=3, color='#ef6c00' if s in C['rer_stations'] else 'g'); ax.text(p[0] + 8, p[1] + 8, s['name'], fontsize=6)
    for s in np.arange(7000, 8601, 100):
        p = Q.TR.at(s)[0]
        if Bx.contains(Point(p)): ax.text(p[0], p[1], str(int(s)), fontsize=5, color='r')
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect('equal'); ax.grid(lw=0.2)
    fig.savefig(fn, dpi=130, bbox_inches='tight'); plt.close(fig)
if __name__ == '__main__':
    draw(714500, 720500, 4337500, 4340500, SP + 'trunk3/ctx_wide.png', 18)
    draw(715000, 716900, 4338100, 4339800, SP + 'trunk3/ctx_split.png', 14)
