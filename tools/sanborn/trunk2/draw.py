try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Plan drawings of the proposed north viaduct (true scale, north up), for Ben to check before anything is built into the page.
import json, sys, numpy as np, matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MPoly
from matplotlib.lines import Line2D
from shapely.geometry import LineString, Point, Polygon, box, shape
from shapely.ops import unary_union
SP = _ws.DATA
sys.path.insert(0, _ws.CODE + 'trunk2'); import geo2 as Q
G = Q.G
L = Q.build()
# R5: off the west pair's inner track onto the middle of the west viaduct (lower level), tangent both ends
mid = Q.dep_left(17.0); midL = LineString(mid)
w_in = L['ORR/TV west 2']['c']; wL = LineString(w_in)
x = wL.intersection(midL); x = x if x.geom_type == 'Point' else list(x.geoms)[0]
sx = wL.project(x); a = np.array(wL.interpolate(sx - 320).coords[0]); ta = np.array(wL.interpolate(sx - 310).coords[0]) - a; ta /= np.hypot(*ta)
mx = midL.project(x); b = np.array(midL.interpolate(mx + 260).coords[0]); tb = np.array(midL.interpolate(mx + 270).coords[0]) - b; tb /= np.hypot(*tb)
D = np.hypot(*(b - a)); u = np.linspace(0, 1, 200)[:, None]; q1, q2 = a + ta * D * 0.42, b - tb * D * 0.42
r5c = (1 - u) ** 3 * a + 3 * (1 - u) ** 2 * u * q1 + 3 * (1 - u) * u ** 2 * q2 + u ** 3 * b
rest = np.array([midL.interpolate(d).coords[0] for d in np.arange(mx + 262, midL.length, 4)]); rest = rest[rest[:, 0] > 711740]
L['R5'] = dict(c=np.vstack([r5c, rest]), kind='r5', lvl='lower level under the west viaduct')
# platforms (islands between the B tracks)
def isl(s0, s1, lo, hi):
    ss = np.arange(s0, s1 + 1e-6, 2.0); A = Q.TR.at(ss, np.full(ss.shape, lo)); B = Q.TR.at(ss, np.full(ss.shape, hi)); return np.vstack([A, B[::-1]])
PLAT = {'Camp Washington': isl(Q.S_CW0, Q.S_CW1, -30.75, -19.75), 'Arlington': isl(Q.S_AR0, Q.S_AR1, -30.75, -19.75), 'Northside / Spring Grove': isl(Q.S_NS0, Q.S_NS1, -21.75, -10.75)}
# footprints: viaduct level (everything on the trunk at band / fill), upper level (Indy and D once up)
EDGE = 4.2
def buf(c, s0=None, s1=None):
    c = np.asarray(c)
    if s0 is not None:
        sel = np.array([s0 <= Q.TR.proj(p) <= s1 for p in c]); c = c[sel]
    return LineString(c).buffer(EDGE, cap_style=2, join_style=2) if len(c) > 1 else Polygon()
S_END = 6270.0                                  # fill back at ground
lowb = []
for k, v in L.items():
    if v['kind'] in ('orr', 'apex'): lowb.append(buf(v['c'], 1100, Q.S_NS1))
    if v['kind'] == 'rer': lowb.append(buf(v['c'], 2758, Q.S_NS1))
    if v['kind'] == 'indy': lowb.append(buf(v['c'][:np.searchsorted(np.cumsum(np.r_[0, np.hypot(*np.diff(v['c'], axis=0).T)]), 2600)]))
lowb += [Polygon(p).buffer(1.0) for p in PLAT.values()]
LOW = unary_union(lowb).buffer(3, join_style=2).buffer(-3, join_style=2)
fillb = [buf(v['c'], Q.S_NS1, S_END) for v in L.values() if v['kind'] in ('orr', 'apex', 'rer')]
FILL = unary_union(fillb).buffer(3, join_style=2).buffer(-3, join_style=2)
upb = [buf(v['c'][[Q.TR.proj(p) > 3640 or LineString(Q.TR.P).distance(Point(p)) > 30 for p in v['c']]]) for v in L.values() if v['kind'] in ('indy', 'rerd')]
UP = unary_union(upb).buffer(3, join_style=2).buffer(-3, join_style=2)
BJ = json.load(open(SP + 'deckpage/basin.json')); H = json.load(open(SP + 'deckpage/hwy.json')); C = json.load(open(SP + 'deckpage/context_v124.json'))
COL = {'orr': '#c2185b', 'apex': '#111111', 'indy': '#777777', 'rer': '#ef6c00', 'rerd': '#d50000', 'r5': '#c2185b'}
def panel(ax, x0, y0, x1, y1, title, notes=(), xsec=''):
    Bx = box(x0, y0, x1, y1)
    for f in BJ['features']:
        p = f['properties']; g = shape(f['geometry'])
        if not g.intersects(Bx): continue
        if p.get('layer') == 'block': ax.fill(*g.exterior.xy, color='#ececec', lw=0) if g.geom_type == 'Polygon' else None
        if p.get('layer') == 'street' and g.geom_type == 'LineString':
            gg = g.buffer(p.get('width_m', 12) / 2, cap_style=2)
            for qq in getattr(gg, 'geoms', [gg]): ax.fill(*qq.exterior.xy, color='#d9d9d9', lw=0)
    for f in H['features']:
        if f['properties'].get('layer') == 'hw_piece':
            g = shape(f['geometry'])
            if g.intersects(Bx):
                gg = g.buffer(f['properties']['w'] / 2, cap_style=2)
                for qq in getattr(gg, 'geoms', [gg]): ax.fill(*qq.exterior.xy, color='#f8d7e6', lw=0)
    for t in C['tracks']:
        if t['sys'] == 'rer' and t.get('line') == 'A':
            g = LineString(t['c'])
            if g.intersects(Bx): ax.plot(*g.xy, color='#ffb74d', lw=0.8, alpha=0.8)
    for g, fc, ec, hatch in ((LOW, '#cfd8dc', '#607d8b', None), (FILL, '#e0e0c8', '#8d8d5a', None), (UP, 'none', '#d50000', '////')):
        for qq in getattr(g, 'geoms', [g]):
            if qq.is_empty or not qq.intersects(Bx): continue
            ax.add_patch(MPoly(np.asarray(qq.exterior.coords), closed=True, fc=fc, ec=ec, lw=0.8, hatch=hatch, alpha=0.9 if fc != 'none' else 0.6))
    for nm, p in PLAT.items():
        ax.add_patch(MPoly(p, closed=True, fc='#ffcc80', ec='#ef6c00', lw=0.8))
        c = p.mean(axis=0)
        if x0 < c[0] < x1 and y0 < c[1] < y1: ax.text(c[0] - 30, c[1], nm, fontsize=7, ha='right', color='#bf360c')
    for k, v in L.items():
        c = np.asarray(v['c']); col = COL[v['kind']]; ls = '-'
        if v['kind'] == 'rer':
            sel = np.array([Q.TR.proj(p) < 2758 for p in c]); a_ = c.copy(); a_[~sel] = np.nan; b_ = c.copy(); b_[sel] = np.nan
            ax.plot(a_[:, 0], a_[:, 1], color=col, lw=1.2, ls=':'); ax.plot(b_[:, 0], b_[:, 1], color=col, lw=1.4); continue
        if v['kind'] == 'r5': ls = (0, (4, 2))
        ax.plot(c[:, 0], c[:, 1], color=col, lw=1.4 if v['kind'] in ('rerd', 'indy') else 1.1, ls=ls)
    txt = []
    for i, (xy, t) in enumerate(notes):
        ax.plot(*xy, 'o', ms=11, mfc='white', mec='k', mew=0.8, zorder=9); ax.text(*xy, str(i + 1), ha='center', va='center', fontsize=7, zorder=10)
        txt.append(f'{i + 1}  {t}')
    if txt: ax.text(0.015, 0.985, '\n'.join(txt), transform=ax.transAxes, va='top', fontsize=8, bbox=dict(fc='white', ec='0.6', lw=0.5, pad=4), zorder=11)
    if xsec: ax.text(0.015, 0.015, xsec, transform=ax.transAxes, va='bottom', fontsize=7.5, family='monospace', bbox=dict(fc='#fffde7', ec='0.6', lw=0.5, pad=4), zorder=11)
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect('equal'); ax.set_xticks([]); ax.set_yticks([])
    ax.plot([x1 - 130, x1 - 30], [y0 + 25, y0 + 25], 'k-', lw=2); ax.text(x1 - 80, y0 + 35, '100 m', ha='center', fontsize=7)
    ax.set_title(title, fontsize=9)
def P(s, o): return Q.TR.at(s, o)[0]
leg = [Line2D([], [], color=COL['orr'], lw=1.4), Line2D([], [], color=COL['indy'], lw=1.4), Line2D([], [], color=COL['apex'], lw=1.4), Line2D([], [], color=COL['rer'], lw=1.4),
       Line2D([], [], color=COL['rer'], lw=1.2, ls=':'), Line2D([], [], color=COL['rerd'], lw=1.4), Line2D([], [], color=COL['r5'], lw=1.4, ls=(0, (4, 2))),
       plt.Rectangle((0, 0), 1, 1, fc='#cfd8dc', ec='#607d8b'), plt.Rectangle((0, 0), 1, 1, fc='none', ec='#d50000', hatch='////'), plt.Rectangle((0, 0), 1, 1, fc='#e0e0c8', ec='#8d8d5a'), plt.Rectangle((0, 0), 1, 1, fc='#ffcc80', ec='#ef6c00')]
legt = ['ORR/TV pairs', 'APEx Indy', 'APEx Dayton, Norwood', 'RER B/D', 'RER B/D in the box (below the viaduct)', 'RER D', 'R5 (lower level under the west viaduct)',
        'North viaduct (one level)', 'West viaduct, upper level (Indy + D)', 'Fill north of Northside / Spring Grove', 'RER island platforms']
if __name__ == '__main__':
    W2E = 'west to east: '
    fig, axs = plt.subplots(2, 3, figsize=(24, 17))
    panel(axs[0, 0], 712330, 4334250, 712830, 4334750, '1. B/D comes up from the box in its own place, west of APEx Indy',
          [(P(2550, -28), 'ORR/TV west pair already out (moved s 2,100-2,500)'), (P(2560, 2), 'B/D in the box, below the viaduct, heading west'), (P(2758, -22), 'B/D 6.8 m under the viaduct: open ramp up from here'), (P(2964, -25), 'Camp Washington island starts (s 2,964)')],
          W2E + 'ORR/TV 2 | B/D 2 | Indy 2 | Dayton 2 | Norwood 2 | ORR/TV 2\n(at s 2,900: 7 m gaps between groups, 4.5 m within)')
    panel(axs[0, 1], 712150, 4334720, 712600, 4335170, '2. Camp Washington and the B/D junction (straight B tracks, D into the middle)',
          [(P(3066, -25), 'Camp Washington island'), (P(3200, -25), 'junction: both D tracks turn in between the B tracks'), (P(3480, -25), 'D 7 m up (2.5% from s 3,200)')],
          W2E + 'ORR/TV 2 | B SB | D SB | D NB | B NB | Indy 2 | Dayton 2 | Norwood 2 | ORR/TV 2')
    panel(axs[0, 2], 711980, 4335520, 712480, 4336020, '3. Indy and D turn west together on one 780 m curve; Arlington under it',
          [(P(3644, -9), 'Indy starts up 2.5% (s 3,644)'), (P(3909, -18), 'curve starts (s 3,909)'), (P(4146, -25), 'Arlington island (KMZ point): the deck crosses over it, s 3,990-4,190')],
          'upper: Indy 2 + D 2 (one deck)  |  lower: R5\ntrunk: ORR/TV 2 | B 2 | Dayton 2 | Norwood 2 | ORR/TV 2')
    panel(axs[1, 0], 711550, 4335600, 712350, 4336400, '4. The west viaduct over the Millvale grid', [], 'upper deck: D 2 (south side) + Indy 2;  lower, under it: R5')
    panel(axs[1, 1], 712300, 4336300, 712800, 4336800, '5. Brashears to Ludlow: B and the west pair move in 9 m together (s 4,300-4,900)',
          [(P(4600, -26), 'single gentle S (about 8 km radius)')], W2E + 'ORR/TV 2 | B 2 | Dayton 2 | Norwood 2 | ORR/TV 2')
    panel(axs[1, 2], 712580, 4336830, 713230, 4337480, '6. Ludlow and Northside / Spring Grove: viaduct ends at the platform end, fill to ground',
          [(P(5369, 0), 'Ludlow underbridge'), (P(5468, -16), 'Northside / Spring Grove island'), (P(5570, 0), 'viaduct ends (s 5,570); fill from here'), (P(6200, 0), 'ground again about s 6,270')],
          'corridor 7 m west of today at the parkway; bend about 650 m radius\n(the KMZ bend, smoothed; OH-75 limits it)')
    fig.legend(leg, legt, loc='lower center', ncol=6, fontsize=9, frameon=False)
    plt.subplots_adjust(wspace=0.03, hspace=0.08, bottom=0.06)
    plt.savefig(SP + 'trunk2/viaduct_plan.png', dpi=80, bbox_inches='tight')
    print('ok')
