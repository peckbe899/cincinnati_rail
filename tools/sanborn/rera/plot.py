try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, numpy as np, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from shapely.geometry import shape, LineString, Point, box
SP = _ws.DATA
R = json.load(open(SP + 'rera/rera.json'))
D = json.load(open(SP + 'deckpage/deck.json'))['features']; B = json.load(open(SP + 'deckpage/basin.json'))['features']
O = json.load(open(SP + 'lph/osm_north.geojson'))['features']; C = json.load(open(SP + 'deckpage/context.json'))
fig = plt.figure(figsize=(16, 13)); ax = fig.add_axes([0.03, 0.30, 0.55, 0.68]); x0, y0, x1, y1 = 711850, 4332150, 712750, 4335050; W = box(x0, y0, x1, y1)
def dr(g, **k):
    for q in getattr(g, 'geoms', [g]):
        if q.geom_type == 'Polygon': ax.fill(*q.exterior.xy, **k)
        elif q.geom_type == 'LineString': ax.plot(*q.xy, **k)
for f in D:
    p = f['properties']; g = shape(f['geometry'])
    if not g.intersects(W): continue
    if p['layer'] == 'deck': dr(g, color='#f1e1c6', zorder=0, lw=0)
    elif p['layer'] in ('boulevard', 'roundabout'): dr(g, color='#e6dccb', zorder=1, lw=0)
    elif p['layer'] in ('palace', 'forecourt'): dr(g, color='#c9a3d6', zorder=1, lw=0)
    elif p['layer'] == 'block' and p['type'] == 'park': dr(g, color='#b9d6a6', zorder=1, lw=0)
    elif p['layer'] == 'street': dr(g, color='#6a7fa8', lw=1.2, zorder=2)
for f in B:
    p = f['properties']; g = shape(f['geometry'])
    if p['layer'] == 'street' and g.intersects(W): dr(g, color='#999', lw=0.6, zorder=2)
for f in O:
    nm = f['properties'].get('name'); g = shape(f['geometry'])
    if nm in ('State Avenue', 'Harrison Avenue', 'Queen City Avenue', 'Beekman Street') and g.geom_type == 'LineString' and g.intersects(W): dr(g, color='#d1006f', lw=1.6, zorder=3)
# RER A coloured by structure
def seg_color(z, gz, dk, under):
    if under: return '#555555'
    if gz is None: return '#e07b00'
    d = z - gz
    return '#1f77b4' if d >= 6.8 else ('#2ca02c' if abs(d) < 6.8 else '#7f3c8d')
for key, prof, coords in (('north', R['profiles']['north'], R['lines']['trunk_north']), ('westwood', R['profiles']['westwood'], R['lines']['westwood'])):
    L = LineString(coords)
    for i in range(len(prof) - 1):
        s0, s1 = prof[i][0], prof[i + 1][0]
        if s1 > L.length: break
        a, b = L.interpolate(s0), L.interpolate(s1)
        under = prof[i][4] if key == 'north' else False
        col = seg_color(prof[i][1], prof[i][2], None, under)
        ax.plot([a.x, b.x], [a.y, b.y], color=col, lw=4.5, solid_capstyle='butt', zorder=5)
for s in C['rer_stations']:
    if W.contains(Point(s['p'])) and 'A' in s.get('lines', []): ax.plot(*s['p'], 'o', ms=7, mfc='white', mec='k', zorder=7); ax.text(s['p'][0] + 12, s['p'][1] + 8, s['name'] + ' (A)', fontsize=8, weight='bold', zorder=7)
for c in R['crossings']:
    if c['result'] == 'under the deck': continue
    col = {'CUT': 'red', 'street under': 'green', 'line under': 'purple'}[c['result']]
    ax.plot(c['x'], c['y'], 'x' if c['result'] == 'CUT' else 'o', color=col, ms=7 if c['result'] == 'CUT' else 4, mew=2, zorder=8)
    if c['result'] == 'CUT' or 'State' in c['street'] or 'Hopple' in c['street'] or 'Harrison' in c['street'] or 'Queen' in c['street']:
        ax.text(c['x'] - 8, c['y'] + 6, f"{c['street'].replace(' (sketch)', '').replace(' (deck)', '')}: {c['diff']:+.1f} m", fontsize=6.5, color=col, ha='right', zorder=8)
ax.plot(*R['fork'], 's', color='k', ms=6, zorder=8); ax.text(R['fork'][0] + 10, R['fork'][1] - 25, f"fork, rail {R['z_fork']} m", fontsize=7)
ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect('equal'); ax.tick_params(labelsize=6); ax.grid(alpha=0.25)
ax.set_title('RER A: Evans to Westwood and Hopple (proposal)', fontsize=11, loc='left')
for lab, col in (('under the deck', '#555555'), ('ramp / at grade (streets stop)', '#2ca02c'), ('viaduct (streets pass under)', '#1f77b4'), ('below ground', '#7f3c8d')):
    ax.plot([], [], color=col, lw=4, label=lab)
ax.plot([], [], 'x', color='red', mew=2, label='street cut'); ax.plot([], [], 'o', color='green', label='street passes under')
ax.legend(loc='lower right', fontsize=7)
# long sections
for k, (key, title, pos) in enumerate((('north', 'Trunk and Northside branch, from CUT (m along the line)', [0.62, 0.55, 0.36, 0.40]), ('westwood', 'Westwood branch, from the fork', [0.62, 0.30, 0.36, 0.20]))):
    a2 = fig.add_axes(pos); P = np.array([[r[0], r[1], r[2] if r[2] is not None else np.nan] for r in R['profiles'][key]])
    a2.plot(P[:, 0], P[:, 2], color='#8c6d46', lw=1, label='ground (map 3)'); a2.plot(P[:, 0], P[:, 1], color='#1f77b4', lw=2, label='rail')
    if key == 'north':
        DKL = np.array([[r[0], r[3] if r[4] else np.nan] for r in R['profiles'][key]]); a2.plot(DKL[:, 0], DKL[:, 1], color='#d9a441', lw=1.2, ls='--', label='deck surface')
        for s, t in ((800, 'Evans'), (R['s_edge'], 'deck edge'), (R['s_fork'], 'fork'), (R['s_hopple'], 'Hopple')): a2.axvline(s, color='#aaa', lw=0.6); a2.text(s, 170.5, t, fontsize=6, rotation=90, va='bottom')
        a2.set_xlim(0, 4300); a2.set_ylim(132, 178)
    else:
        a2.set_ylim(150, 178)
    a2.set_title(title, fontsize=8, loc='left'); a2.tick_params(labelsize=6); a2.grid(alpha=0.3); a2.legend(fontsize=6, loc='upper left')
# crossing table
rows = [c for c in R['crossings'] if c['result'] != 'under the deck']
txt = '\n'.join(f"{c['line'][:9]:9s} {c['street'].replace(' (sketch)','').replace(' (deck)',''):34s} rail {c['rail']:6.1f}  street {c['street_z']:6.1f}  {c['diff']:+5.1f}  {c['result']}" for c in rows[:30])
fig.text(0.03, 0.01, txt, fontsize=6.2, family='monospace', va='bottom')
fig.text(0.62, 0.22, f"Ramp {R['grade']*100:.1f}% from the deck edge (rail {R['z_edge']} m); Westwood branch {R['westwood_grade']*100:.2f}%,\ncurve {R['westwood_curve_deg']} deg at {R['radius']:.0f} m radius; Westwood platform {R['westwood_platform']} m at ground.\nEvans at yard level 147.5 m under W Liberty; 135.9 m under CUT's lower level.\nNorthside {R['option']}: over the Hopple viaduct at {R['hopple_level']+6.8:.1f} m (Hopple {R['hopple_level']} m).", fontsize=8, va='top')
fig.savefig(SP + 'rera/rera_sketch.png', dpi=120); print('ok')
