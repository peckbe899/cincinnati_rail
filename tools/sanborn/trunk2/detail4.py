try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Rotated true-scale strips of the north viaduct (trunk running left to right, north to the right), for reading track by track.
import sys, numpy as np, matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MPoly
from shapely.geometry import LineString, Point, box, shape, Polygon
SP = _ws.DATA
sys.path.insert(0, _ws.CODE + 'trunk2')
import draw4 as D
Q, L, G = D.Q, D.L, D.G
TAG = {'ORR/TV west 1': 'W1 (X2 + R5 SB)', 'ORR/TV west 2': 'W2 (X2 + R5 NB)', 'RER B SB': 'B SB', 'RER B NB': 'B NB', 'RER D SB': 'D SB', 'RER D NB': 'D NB',
       'APEx Indy 1': 'Indy 1', 'APEx Indy 2': 'Indy 2', 'APEx Dayton 1': 'Dayton 1', 'APEx Dayton 2': 'Dayton 2', 'APEx Norwood 1': 'Norwood 1', 'APEx Norwood 2': 'Norwood 2',
       'ORR/TV east 1': 'E1', 'ORR/TV east 2': 'E2', 'R5 1': 'R5 SB', 'R5 2': 'R5 NB'}
def strip(ax, s0, s1, ylo, yhi, title, notes):
    a, b = D.P(s0), D.P(s1); u = (b - a) / np.hypot(*(b - a)); n = np.array([-u[1], u[0]])
    Rf = lambda xy: np.c_[(np.asarray(xy) - a) @ u, (np.asarray(xy) - a) @ n]
    Lx = np.hypot(*(b - a)); Bx = Polygon([a + n * ylo, b + n * ylo, b + n * yhi, a + n * yhi]).buffer(60)
    def fillg(g, **kw):
        for qq in getattr(g, 'geoms', [g]):
            if not qq.is_empty and qq.geom_type == 'Polygon' and qq.intersects(Bx): ax.add_patch(MPoly(Rf(np.asarray(qq.exterior.coords)), closed=True, **kw))
    for f in D.BJ['features']:
        p = f['properties']; g = shape(f['geometry'])
        if not g.intersects(Bx): continue
        if p.get('layer') == 'block': fillg(g, fc='#f0f0f0', ec='none')
        if p.get('layer') == 'street' and g.geom_type == 'LineString': fillg(g.buffer(p.get('width_m', 12) / 2, cap_style=2), fc='#e0e0e0', ec='none')
    for f in D.H['features']:
        if f['properties'].get('layer') == 'hw_piece':
            g = shape(f['geometry'])
            if g.intersects(Bx): fillg(g.buffer(f['properties']['w'] / 2, cap_style=2), fc='#f6d5e4', ec='none')
    fillg(D.WAT, fc='#9ecae1', ec='none')
    fillg(D.LOW, fc='#cfd8dc', ec='#607d8b', lw=0.7); fillg(D.FILL, fc='#e3e3c9', ec='#8d8d5a', lw=0.7)
    fillg(D.BOX, fc='none', ec='#ef6c00', lw=0.8, ls=(0, (3, 2))); fillg(D.UP, fc='#ffcdd2', ec='#d50000', lw=0.9, alpha=0.5)
    ob = Rf(D.OLD_BD); ax.plot(ob[:, 0], ob[:, 1], color='#ffa726', lw=5, alpha=0.25)
    fillg(Polygon(D.WEST), fc='#ffcc80', ec='#ef6c00', lw=0.8)
    for nm, pl in D.PLAT.items(): fillg(Polygon(pl), fc='#ffe0b2' if nm.startswith('Straight') else '#ffcc80', ec='#ef6c00', lw=0.8)
    fillg(Polygon(D.ALT_AR), fc='none', ec='#2e7d32', lw=1.1, ls=(0, (2, 2))); fillg(D.DECK_OVER_AR, fc='#d50000', ec='none', alpha=0.35)
    for k, v in L.items():
        c = Rf(v['c']); col = D.COL[v['kind']]
        if v['kind'] == 'rer':
            m = v['s'] < G.S_SEP; a_ = c.copy(); a_[~m] = np.nan; b_ = c.copy(); b_[m] = np.nan
            ax.plot(a_[:, 0], a_[:, 1], color=col, lw=1.3, ls=(0, (2, 1.5))); ax.plot(b_[:, 0], b_[:, 1], color=col, lw=1.5)
        else: ax.plot(c[:, 0], c[:, 1], color=col, lw=1.6 if v['kind'] in ('rerd', 'indy') else 1.2, ls=(0, (5, 2)) if v['kind'] == 'r5' else '-')
        inside = np.where((c[:, 0] > 8) & (c[:, 0] < Lx - 8) & (c[:, 1] > ylo + 4) & (c[:, 1] < yhi - 4))[0]
        if len(inside):
            j = inside[0]; ax.text(c[j, 0] + 3, c[j, 1], TAG[k], fontsize=6.5, va='center', color=col, bbox=dict(fc='white', ec='none', pad=0.3, alpha=0.8))
    for i, (sv, ov, t) in enumerate(notes):
        xy = Rf(D.P(sv, ov)[None])[0]; ax.plot(*xy, 'o', ms=12, mfc='white', mec='k', mew=0.8, zorder=9); ax.text(*xy, str(i + 1), ha='center', va='center', fontsize=7.5, zorder=10)
    ax.text(0.003, 0.97, title + '\n' + '\n'.join(f'{i + 1}  {t}' for i, (_, _, t) in enumerate(notes)), transform=ax.transAxes, va='top', fontsize=8.5, bbox=dict(fc='white', ec='0.6', lw=0.5, pad=4), zorder=11)
    for sv in np.arange(np.ceil(s0 / 100) * 100, s1, 100):
        xy = Rf(D.P(sv, ylo + 6)[None])[0]; ax.text(xy[0], xy[1], f's {sv:,.0f}', fontsize=6.5, ha='center', color='0.4')
    ax.plot([Lx - 140, Lx - 40], [ylo + 8, ylo + 8], 'k-', lw=2); ax.text(Lx - 90, ylo + 11, '100 m', ha='center', fontsize=7)
    nu = np.array([0, 1.0]) @ np.c_[u, n]; ax.annotate('', xy=(30 + 18 * nu[0], ylo + 30 + 18 * nu[1]), xytext=(30, ylo + 30), arrowprops=dict(arrowstyle='->', lw=1.2)); ax.text(30 + 24 * nu[0], ylo + 30 + 24 * nu[1], 'N', fontsize=8, ha='center', va='center')
    ax.set_xlim(0, Lx); ax.set_ylim(ylo, yhi); ax.set_aspect('equal'); ax.set_xticks([]); ax.set_yticks([])
if __name__ == '__main__':
    fig, axs = plt.subplots(4, 1, figsize=(22, 25))
    strip(axs[0], 1330, 2480, -95, 45, 'A. Western to Straight (west is up)',
          [(1440, -72, 'Western: the twin bores carry on the Western straight'), (1950, -40, 'one curve per bore, R about 4,550 m, s 1,750-2,150'),
           (1850, -14, 'W pair steps out 18.9 m over the bores, s 1,600-2,100 (R about 1,300 m)'), (2300, -23, 'Straight island, in the box under the west side')])
    strip(axs[1], 2420, 3560, -70, 45, 'B. Ramp, Camp Washington, D junction',
          [(2556, -23, 'box ends, open ramp at 3.3%'), (3066, -23, 'Camp Washington island'), (3310, -23, 'D peels off each B track into the middle (no crossing), then climbs 2.5%')])
    strip(axs[2], 3540, 4420, -170, 40, 'C. The west viaduct leaves; R5 drops under it; Arlington',
          [(3780, -23, 'D straight between the B tracks, climbing'), (3904, -8, 'Indy and D deck curve starts, R 780 m; Indy crosses over B NB at 7.9 m'),
           (3995, -38, 'R5 leaves the west pair (R 600 m); NB crosses W1 here'), (4146, -23, 'Arlington at the KMZ point: deck over its south 60 m'),
           (4206, -23, 'option: Arlington 60 m north (green)')])
    strip(axs[3], 4380, 5720, -60, 45, 'D. B and W close up; Ludlow; Northside / Spring Grove',
          [(4620, -24, 'B and W move in, s 4,300-4,950'), (5369, 12, 'Ludlow'), (5468, -14, 'Northside island: W and B SB step out 9.9 m (S of 400 m each side)'), (5570, 12, 'viaduct ends, fill north')])
    plt.subplots_adjust(hspace=0.06)
    plt.savefig(SP + 'trunk2/viaduct_detail4.png', dpi=85, bbox_inches='tight'); print('ok')
