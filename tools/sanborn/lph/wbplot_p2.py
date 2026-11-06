try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, sys, numpy as np, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from shapely.geometry import shape, LineString, Point, box
SP = _ws.DATA
D = json.load(open(SP + 'deckpage/deck.json'))['features']; B = json.load(open(SP + 'deckpage/basin.json'))['features']
O = json.load(open(SP + 'lph/osm_north.geojson'))['features']; C = json.load(open(SP + 'deckpage/context.json')); T = json.load(open(SP + 'deckpage/tracks.json'))['features']
picks = json.load(open(SP + 'lph/wb_picks.json'))
def draw(ax, g, **kw):
    for q in getattr(g, 'geoms', [g]):
        if q.geom_type == 'Polygon': ax.fill(*q.exterior.xy, **kw)
        elif q.geom_type == 'LineString': ax.plot(*q.xy, **kw)
def go(x0, y0, x1, y1, fn):
    fig, ax = plt.subplots(figsize=(11, 11 * (y1 - y0) / (x1 - x0))); W = box(x0, y0, x1, y1)
    for f in D:
        p = f['properties']; g = shape(f['geometry'])
        if not g.intersects(W): continue
        if p['layer'] == 'deck': draw(ax, g, color='#f3e2c7', zorder=0)
        elif p['layer'] == 'block': draw(ax, g, color={'park': '#9bc58a', 'square': '#bcd9a9'}.get(p['type'], '#d9b48c'), zorder=1, lw=0)
        elif p['layer'] in ('boulevard', 'roundabout', 'palace', 'forecourt', 'cut_square', 'cut_park', 'cut_headhouse', 'cut_precinct'): draw(ax, g, color='#e8e0d0' if p['layer'] == 'boulevard' else '#c9a3d6', zorder=1, lw=0)
        elif p['layer'] == 'street': draw(ax, g, color='#2b4f8a' if p['kind'] in ('T', 'NS') else '#b8332a', lw=1.6, zorder=3)
    for f in B:
        p = f['properties']; g = shape(f['geometry'])
        if not g.intersects(W): continue
        if p['layer'] == 'street': draw(ax, g, color='#555', lw=0.8, zorder=2)
        elif p['layer'] == 'block': draw(ax, g, color='#e6cfb0', zorder=1, lw=0)
    for f in O:
        nm = f['properties'].get('name') or ''; g = shape(f['geometry'])
        if g.geom_type != 'LineString' or not g.intersects(W): continue
        if nm in ('State Avenue', 'Beekman Street'): draw(ax, g, color='#d1006f', lw=2.2, zorder=4)
        else: draw(ax, g, color='#999', lw=0.4, ls=':', zorder=2)
    for f in T:
        g = shape(f['geometry'])
        if g.geom_type == 'LineString' and g.intersects(W): draw(ax, g, color='#666', lw=0.3, zorder=2)
    for k, col in (('metro', '#5b4ea8'), ('rer', '#e07b00')):
        for m in C[k]:
            g = LineString(m['c'])
            if g.intersects(W): draw(ax, g, color=col, lw=1.0, ls='--', zorder=5); 
    for k in ('stations', 'rer_stations'):
        for s in C[k]:
            if W.contains(Point(s['p'])): ax.plot(*s['p'], 'o', ms=4, color='k', zorder=6); ax.text(s['p'][0] + 15, s['p'][1], s['name'] + ' (' + str(s.get('line', s.get('lines'))) + ')', fontsize=6, zorder=6)
    for s, a, b, e, n, side, d in picks:
        if side == 'E' and W.contains(Point(e, n)): ax.plot(e, n, 'x', color='green', ms=5, zorder=6); ax.text(e + 8, n - 12, f'{a}/{b}', fontsize=5, color='green')
    for f in O:
        nm = f['properties'].get('name') or ''; g = shape(f['geometry'])
        if nm and g.geom_type == 'LineString' and g.intersects(W) and g.length > 150:
            c = g.interpolate(0.5, normalized=True); ax.text(c.x, c.y, nm, fontsize=4.5, color='#888')
    PR = json.load(open(SP + 'lph/wb_proposal.json'))
    for p in PR:
        c = np.array(p['coords']); col = {'new': '#00a651', 'reconnect': '#ff7f00', '1904': '#7a3e00', 'option': '#00a651'}[p['kind']]
        ax.plot(c[:, 0], c[:, 1], color=col, lw=2.4, ls='--' if p['kind'] == 'option' else '-', zorder=7, alpha=0.9)
        m = c[len(c) // 2] if len(c) > 2 else c.mean(0)
        if W.contains(Point(m)): ax.text(m[0], m[1] + 6, p['name'], fontsize=5.5, color=col, zorder=8, weight='bold')
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect('equal'); ax.grid(alpha=0.3); ax.tick_params(labelsize=6)
    fig.savefig(fn, dpi=130, bbox_inches='tight'); plt.close(fig)
go(711800, 4333550, 712900, 4335000, SP + 'lph/wbp_m2.png')
