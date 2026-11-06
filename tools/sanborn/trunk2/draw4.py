try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# True-scale plan panels and cross-sections of the compact north viaduct proposal (geo4). For Ben to check; nothing installed.
import json, sys, numpy as np, matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MPoly, Rectangle, Circle
from matplotlib.lines import Line2D
from shapely.geometry import LineString, Point, Polygon, box, shape
from shapely.ops import unary_union
SP = _ws.DATA
sys.path.insert(0, _ws.CODE + 'trunk2')
exec(open(_ws.CODE + 'trunk2/lud6.py').read().split('def pt(s)')[0])        # PK (OH-75 parkway)
from creek_up import WAT_UP as WAT                                      # Mill Creek, open only north-east of Albone (decked and underground south-west of it)
import geo4 as Q
L = Q.build()
S_ARN = 60.0                                                            # Arlington moved north to clear the deck (option)
def P(s, o=0.0): return Q.TR.at(s, o)[0]
def strip(s0, s1, lo, hi):
    ss = np.arange(s0, s1 + 1e-6, 2.0)
    lo = lo(ss) if callable(lo) else np.full(ss.shape, lo); hi = hi(ss) if callable(hi) else np.full(ss.shape, hi)
    return np.vstack([Q.TR.at(ss, lo), Q.TR.at(ss, hi)[::-1]])
E_ = 1.7                                                                # track centre to island edge
bS, bN = Q.o_b(0), Q.o_b(1)
PLAT = {'Straight (in the box)': strip(Q.S_ST0, Q.S_ST1, Q.B_SB + E_, Q.B_NB - E_),
        'Camp Washington': strip(Q.S_CW0, Q.S_CW1, Q.B_SB + E_, Q.B_NB - E_),
        'Arlington (KMZ point)': strip(Q.S_AR0, Q.S_AR1, Q.B_SB + E_, Q.B_NB - E_),
        'Northside / Spring Grove': strip(Q.S_NS0, Q.S_NS1, lambda s: bS(s) + E_, lambda s: bN(s) - E_),
        'Mitchell': strip(Q.S_MI0, Q.S_MI1, lambda s: bS(s) + E_, lambda s: bN(s) - E_)}
ALT_AR = strip(Q.S_AR0 + S_ARN, Q.S_AR1 + S_ARN, Q.B_SB + E_, Q.B_NB - E_)
WEST = np.array([[712691.7, 4333280.0], [712675.6, 4333078.6], [712664.7, 4333079.5], [712680.7, 4333280.9]])
EDGE = 4.2
def proj_all(c): return np.array([Q.TR.proj(p) for p in c])
def buf(c, keep=None):
    c = np.asarray(c)
    if keep is not None: c = c[keep]
    return LineString(c).buffer(EDGE, cap_style=2, join_style=2) if len(c) > 1 else Polygon()
S_GROUND = 6265.0
low, fill, up, boxp = [], [], [], []
for k, v in L.items():
    c = v['c']; s = proj_all(c); v['s'] = s
    on = np.array([LineString(Q.TR.P).distance(Point(p)) < 60 for p in c])
    if v['kind'] in ('orr', 'apex'):
        low.append(buf(c, (s >= 1100) & (s <= Q.S_NS1) & on)); fill.append(buf(c, (s >= Q.S_NS1) & (s <= S_GROUND)))
    if v['kind'] == 'rer':
        low.append(buf(c, (s >= G.S_SEP) & (s <= Q.S_NS1))); fill.append(buf(c, (s >= Q.S_NS1) & (s <= S_GROUND)))
        boxp.append(buf(c, (s >= Q.S_ST0 - 20) & (s <= G.S_SEP)))
    if v['kind'] == 'indy':
        low.append(buf(c, (s <= Q.S_TC) & on)); up.append(buf(c, (s >= G.S_A) | ~on))
    if v['kind'] == 'rerd':
        low.append(buf(c, (s <= 3500) & on)); up.append(buf(c, (s >= 3500) | ~on))
    if v['kind'] == 'r5': low.append(buf(c))
low += [Polygon(p).buffer(1.0) for n, p in PLAT.items() if not n.startswith('Straight')]
def U(g): return unary_union([x for x in g if not x.is_empty]).buffer(2, join_style=2).buffer(-2, join_style=2)
LOW, FILL, UP, BOX = U(low), U(fill), U(up), U(boxp).buffer(3, join_style=2)
DECK_OVER_AR = Polygon(PLAT['Arlington (KMZ point)']).intersection(UP)
BJ = json.load(open(SP + 'deckpage/basin.json')); H = json.load(open(SP + 'deckpage/hwy.json'))
OLD_BD = np.array(json.load(open(SP + 'trunk/db_restore.json'))['transit']['R-BD-712316-4334957']['c'][:11])
OLD_TRUNK = np.array([G.C.interpolate(s).coords[0] for s in np.arange(4900, 7700, 4.0)])
COL = {'orr': '#c2185b', 'apex': '#111111', 'indy': '#6d6d6d', 'rer': '#ef6c00', 'rerd': '#d50000', 'r5': '#c2185b'}
def walls(ax, Bx):
    for f in BJ['features']:
        p = f['properties']; g = shape(f['geometry'])
        if not g.intersects(Bx): continue
        if p.get('layer') == 'block' and g.geom_type == 'Polygon': ax.fill(*g.exterior.xy, color='#eeeeee', lw=0)
        if p.get('layer') == 'street' and g.geom_type == 'LineString':
            gg = g.buffer(p.get('width_m', 12) / 2, cap_style=2)
            for qq in getattr(gg, 'geoms', [gg]): ax.fill(*qq.exterior.xy, color='#dcdcdc', lw=0)
    for f in H['features']:
        if f['properties'].get('layer') == 'hw_piece':
            g = shape(f['geometry'])
            if g.intersects(Bx):
                gg = g.buffer(f['properties']['w'] / 2, cap_style=2)
                for qq in getattr(gg, 'geoms', [gg]): ax.fill(*qq.exterior.xy, color='#f6d5e4', lw=0)
    for qq in getattr(WAT, 'geoms', [WAT]):
        if qq.intersects(Bx): ax.fill(*qq.exterior.xy, color='#9ecae1', lw=0)
def polys(ax, g, Bx, **kw):
    for qq in getattr(g, 'geoms', [g]):
        if not qq.is_empty and qq.intersects(Bx): ax.add_patch(MPoly(np.asarray(qq.exterior.coords), closed=True, **kw))
ASP = 0.82                                                              # panel width / height
def win(pts, pad=45.0):
    pts = np.asarray(pts); x0, y0 = pts.min(axis=0) - pad; x1, y1 = pts.max(axis=0) + pad
    w, h = x1 - x0, y1 - y0
    if w / h < ASP: x0, x1 = (x0 + x1) / 2 - h * ASP / 2, (x0 + x1) / 2 + h * ASP / 2
    else: y0, y1 = (y0 + y1) / 2 - w / ASP / 2, (y0 + y1) / 2 + w / ASP / 2
    return x0, x1, y0, y1
def sw(s0, s1, o0, o1):
    ss = np.arange(s0, s1, 10.0); return np.vstack([Q.TR.at(ss, o0), Q.TR.at(ss, o1)])
TAG = {'ORR/TV west 1': 'W1', 'ORR/TV west 2': 'W2', 'RER B SB': 'B SB', 'RER B NB': 'B NB', 'RER D SB': 'D SB', 'RER D NB': 'D NB', 'APEx Indy 1': 'In1', 'APEx Indy 2': 'In2',
       'APEx Dayton 1': 'Dy1', 'APEx Dayton 2': 'Dy2', 'APEx Norwood 1': 'Nw1', 'APEx Norwood 2': 'Nw2', 'ORR/TV east 1': 'E1', 'ORR/TV east 2': 'E2', 'R5 1': 'R5 SB', 'R5 2': 'R5 NB'}
def panel(ax, W, title, notes=(), xsec='', tags=None):
    x0, x1, y0, y1 = W; Bx = box(x0, y0, x1, y1); w = x1 - x0
    walls(ax, Bx)
    polys(ax, LOW, Bx, fc='#cfd8dc', ec='#607d8b', lw=0.7)
    polys(ax, FILL, Bx, fc='#e3e3c9', ec='#8d8d5a', lw=0.7)
    polys(ax, BOX, Bx, fc='none', ec='#ef6c00', lw=0.8, ls=(0, (3, 2)))
    polys(ax, UP, Bx, fc='#ffebee', ec='#d50000', lw=0.9, alpha=0.35, hatch='///')
    ax.plot(OLD_BD[:, 0], OLD_BD[:, 1], color='#ffa726', lw=4, alpha=0.25, solid_capstyle='butt')
    ax.plot(OLD_TRUNK[:, 0], OLD_TRUNK[:, 1], color='#1565c0', lw=0.8, ls=(0, (6, 3)), alpha=0.8)
    ax.add_patch(MPoly(WEST, closed=True, fc='#ffcc80', ec='#ef6c00', lw=0.8))
    for nm, p in PLAT.items():
        ax.add_patch(MPoly(p, closed=True, fc='#ffe0b2' if nm.startswith('Straight') else '#ffcc80', ec='#ef6c00', lw=0.8, ls='--' if nm.startswith('Straight') else '-'))
    polys(ax, DECK_OVER_AR, Bx, fc='#d50000', ec='none', alpha=0.35)
    for k, v in L.items():
        c = np.asarray(v['c']); col = COL[v['kind']]
        if v['kind'] == 'rer':
            m = v['s'] < G.S_SEP; a_ = c.copy(); a_[~m] = np.nan; b_ = c.copy(); b_[m] = np.nan
            ax.plot(a_[:, 0], a_[:, 1], color=col, lw=1.2, ls=(0, (2, 1.5))); ax.plot(b_[:, 0], b_[:, 1], color=col, lw=1.4); continue
        ax.plot(c[:, 0], c[:, 1], color=col, lw=1.5 if v['kind'] in ('rerd', 'indy') else 1.1, ls=(0, (5, 2)) if v['kind'] == 'r5' else '-', zorder=6)
    if tags is not None:
        order = ['ORR/TV west 1', 'ORR/TV west 2', 'R5 1', 'R5 2', 'RER B SB', 'RER D SB', 'RER D NB', 'RER B NB', 'APEx Indy 1', 'APEx Indy 2', 'APEx Dayton 1', 'APEx Dayton 2', 'APEx Norwood 1', 'APEx Norwood 2', 'ORR/TV east 1', 'ORR/TV east 2']
        for k, v in L.items():
            if k not in TAG: continue
            sv = tags + (order.index(k) % 4) * 26.0
            m = np.where(np.abs(v['s'] - sv) < 1.5)[0]
            c = np.asarray(v['c'])
            if not len(m): continue
            q = c[m[0]]
            if x0 < q[0] < x1 and y0 < q[1] < y1:
                ax.text(q[0], q[1], TAG[k], fontsize=6.3, ha='center', va='center', rotation=0, color=COL[v['kind']], fontweight='bold',
                        bbox=dict(fc='white', ec='none', pad=0.15, alpha=0.85), zorder=8, clip_on=True)
    txt = []
    for i, (xy, t) in enumerate(notes):
        ax.plot(*xy, 'o', ms=12, mfc='white', mec='k', mew=0.8, zorder=9, clip_on=True); ax.text(*xy, str(i + 1), ha='center', va='center', fontsize=7.5, zorder=10, clip_on=True)
        txt.append(f'{i + 1}  {t}')
    if txt: ax.text(0.012, 0.988, '\n'.join(txt), transform=ax.transAxes, va='top', fontsize=8.3, bbox=dict(fc='white', ec='0.6', lw=0.5, pad=4), zorder=11)
    if xsec: ax.text(0.012, 0.012, xsec, transform=ax.transAxes, va='bottom', fontsize=7.8, family='monospace', bbox=dict(fc='#fffde7', ec='0.6', lw=0.5, pad=4), zorder=11)
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect('equal'); ax.set_xticks([]); ax.set_yticks([])
    sb = 100 if w < 900 else 200
    for xy, _ in notes: assert x0 < xy[0] < x1 and y0 < xy[1] < y1, (title, xy)
    ax.plot([x1 - sb - 25, x1 - 25], [y0 + 22, y0 + 22], 'k-', lw=2); ax.text(x1 - sb / 2 - 25, y0 + 30, f'{sb} m', ha='center', fontsize=7.5)
    ax.set_title(title, fontsize=10)
leg = [Line2D([], [], color=COL['orr'], lw=1.4), Line2D([], [], color=COL['r5'], lw=1.4, ls=(0, (5, 2))), Line2D([], [], color=COL['apex'], lw=1.4), Line2D([], [], color=COL['indy'], lw=1.5),
       Line2D([], [], color=COL['rer'], lw=1.4), Line2D([], [], color=COL['rer'], lw=1.2, ls=(0, (2, 1.5))), Line2D([], [], color=COL['rerd'], lw=1.5),
       Rectangle((0, 0), 1, 1, fc='#cfd8dc', ec='#607d8b'), Rectangle((0, 0), 1, 1, fc='#ffebee', ec='#d50000', hatch='////'), Rectangle((0, 0), 1, 1, fc='#e3e3c9', ec='#8d8d5a'),
       Rectangle((0, 0), 1, 1, fc='#ffcc80', ec='#ef6c00'), Line2D([], [], color='#ffa726', lw=4, alpha=0.3),
       Line2D([], [], color='#1565c0', lw=0.9, ls=(0, (6, 3))), Rectangle((0, 0), 1, 1, fc='#9ecae1', ec='none'), Rectangle((0, 0), 1, 1, fc='#f6d5e4', ec='none')]
legt = ['ORR/TV (X2 west pair, east pair)', 'R5 (lower level under the west viaduct)', 'APEx Dayton, Norwood', 'APEx Indy', 'RER B', 'RER B in bored tunnel / box', 'RER D',
        'North viaduct (one level)', 'West viaduct upper level (Indy + D)', 'Fill north of Northside', 'RER platforms', "Today's B/D line (Ben's edit)",
        "Today's trunk line (Ludlow)", 'Mill Creek', 'OH-75']

def ground(s):
    g_tip = G.deck(G.C.interpolate(G.S_TIP).y)
    if s <= G.S_TIP: return G.deck(P(s)[1])
    if s <= G.S_LUD: return g_tip + (155.4 - g_tip) * (s - G.S_TIP) / (G.S_LUD - G.S_TIP)
    return max(152.1, 155.4 - (155.4 - 152.1) * (s - G.S_LUD) / (6265 - G.S_LUD))
def section_sheet(fn, cuts):
    names = {k: v for k, v in L.items()}
    nr = (len(cuts) + 1) // 2; fig, axs = plt.subplots(nr, 2, figsize=(22, 2.75 * nr)); axs = axs.T.ravel()
    for ax in axs[len(cuts):]: ax.axis('off')
    for ax, (s, title) in zip(axs, cuts):
        p = P(s); e = P(s, 1.0) - p; cut = LineString([p - e * 120, p + e * 120]); gz = ground(s)
        rows = []
        for k, v in names.items():
            X = LineString(v['c']).intersection(cut)
            for q in getattr(X, 'geoms', [X]):
                if X.is_empty or q.geom_type != 'Point': continue
                o = float((np.array(q.coords[0]) - p) @ e); dist = LineString(Q.TR.P).distance(q); deck = (s > Q.S_TC - 5 and dist > 2.5) and v['kind'] in ('indy', 'rerd')
                kd = v['kind']
                if kd in ('orr', 'apex', 'r5'): z = G.band(s); lvl = 'low'
                elif kd == 'rer': z = G.band(s) if s >= G.S_CW0 else max(G.Z_STR, G.band(G.S_CW0) - G.G_DIVE * (G.S_CW0 - s)); lvl = 'low' if s >= G.S_SEP else 'under'
                else: z = G.Z_TOP if deck else (G.sh_z(s) if kd == 'indy' else min(G.Z_TOP, G.band(3250) + 0.025 * max(0, s - 3250))); lvl = 'up' if z - G.band(s) > 3 else 'low'
                if s < 2100 and kd == 'rer': z = gz - 14; lvl = 'under'
                short = k.replace('ORR/TV west ', 'W').replace('ORR/TV east ', 'E').replace('APEx Dayton ', 'Dy').replace('APEx Norwood ', 'Nw').replace('APEx Indy ', 'In').replace('RER B ', 'B ').replace('RER D ', 'D ').replace('R5 ', 'R5-')
                rows.append((o, z, lvl, kd, short))
        rows.sort()
        ax.axhline(gz, color='#8d6e63', lw=1.0); ax.fill_between([-120, 120], gz - 30, gz, color='#efebe9', zorder=0)
        for lv, fc in (('low', '#b0bec5'), ('up', '#ef9a9a')):
            rr = [r for r in rows if r[2] == lv]
            groups = []
            for r in rr:
                if groups and abs(r[0] - groups[-1][-1][0]) < 9.5 and abs(r[1] - groups[-1][-1][1]) < 2: groups[-1].append(r)
                else: groups.append([r])
            for g in groups:
                a, b = g[0][0] - EDGE, g[-1][0] + EDGE; zz = np.mean([r[1] for r in g])
                ax.add_patch(Rectangle((a, zz - 1.6), b - a, 1.6, fc=fc, ec='0.35', lw=0.6, zorder=2))
                if lv == 'up' or zz - gz > 3:
                    for xp in np.arange(a + 2, b - 1, 8.0): ax.plot([xp, xp], [gz, zz - 1.6], color='0.6', lw=0.6, zorder=1)
        for o, z, lv, kd, nm in rows:
            if lv == 'under':
                ax.add_patch(Circle((o, z + 2.5), 3.3, fc='none', ec=COL['rer'], lw=0.9) if s < 2190 else Rectangle((o - 3.5, z - 0.8), 7, 7.3, fc='none', ec=COL['rer'], lw=0.9))
            ax.add_patch(Rectangle((o - 1.3, z), 2.6, 0.5, fc=COL[kd], ec='none', zorder=3))
            ax.text(o, z + 1.0 + (2.6 if nm.startswith('R5') else 0), nm, rotation=90, fontsize=6.4, ha='center', va='bottom', zorder=4)
            ax.text(o, gz - 1.0 - (5 if nm.startswith('R5') else 0), f'{o:.1f}', rotation=90, fontsize=5.6, ha='center', va='top', color='0.35')
        isl = [(n, pl) for n, pl in PLAT.items() if Polygon(pl).intersects(cut)]
        for n, pl in isl:
            X = Polygon(pl).intersection(cut); xs = [float((np.array(c) - p) @ e) for c in X.coords]
            zz = [r[1] for r in rows if r[3] == 'rer'][0]
            ax.add_patch(Rectangle((min(xs), zz), max(xs) - min(xs), 1.0, fc='#ffcc80', ec='#ef6c00', lw=0.6, zorder=3))
        XL = (-68, 28) if not (4000 < s < 4300) else (-68, 28)
        ax.set_xlim(*XL); ax.set_ylim(gz - 13, max(gz + 17, G.Z_TOP + 8)); ax.set_aspect('equal')
        ax.set_yticks([gz, gz + 6.5, G.Z_TOP]); ax.set_yticklabels(['ground', '+6.5', 'upper %.1f' % G.Z_TOP], fontsize=6)
        ax.set_xticks(range(-60, 29, 10)); ax.tick_params(labelsize=6.5)
        ax.text(XL[0] + 1, max(gz + 17, G.Z_TOP + 8) - 1, f's {s:,.0f}   {title}', fontsize=8.5, va='top', fontweight='bold')
        ax.text(XL[1] - 1, max(gz + 17, G.Z_TOP + 8) - 1, 'west  <  looking north  >  east', fontsize=7, va='top', ha='right', color='0.4')
    plt.subplots_adjust(hspace=0.35)
    plt.savefig(fn, dpi=120, bbox_inches='tight'); plt.close(fig)

if __name__ == '__main__':
    W2E = 'west to east: '
    fig, axs = plt.subplots(2, 3, figsize=(25, 19))
    panel(axs[0, 0], win(sw(1330, 2420, -80, 25)), '1. B/D twin bores off the Western straight; W pair tight above',
          [(P(1450, -70), 'Western north platform end; the bores carry on the same straight'), (P(1820, -52), 'one curve each bore, R about 4,550 m, s 1,750-2,150'),
           (P(1700, -10), 'ORR/TV west pair stays tight against Indy over the bores'), (P(2300, -45), 'Straight station in the box, now under the west side')],
          'viaduct: W 2 | Indy 2 | Dayton 2 | Norwood 2 | E 2, all 4.5 m apart\nbelow it: B in the bores, then the Straight box')
    panel(axs[0, 1], win(sw(2450, 3480, -45, 25)), '2. W pair out on one curve; B ramps up; D turns in between B',
          [(P(2600, -55), 'W pair out on one 620 m curve, s 2,235-2,550'), (P(3066, -55), 'Camp Washington island'),
           (P(3330, -55), 'D peels off each B track into the middle: no crossing')],
          W2E + 'W 2 | B SB | D SB | D NB | B NB | Indy 2 | Dayton 2 | Norwood 2 | E 2')
    panel(axs[0, 2], win(sw(3600, 4360, -125, 25)), '3. Indy and D leave on the upper level; R5 drops under them',
          [(P(3700, 15), 'Indy up 2.5% from s 3,644; D up from s 3,250'), (P(3904, 15), 'deck curve starts (s 3,904), R 780 m'),
           (P(3980, -60), 'R5 leaves the west pair (s 3,991), R 600 m; NB crosses W1 on the level'), (P(4120, 15), 'Arlington: deck over its south 60 m (red)')],
          'upper: D 2 (south) + Indy 2, one deck from s ~4,210\nlower: R5 2 under it from s ~4,300')
    dp = np.vstack([Q.dep_path(13.5)[0], Q.dep_path(13.5)[1][:150]])
    panel(axs[1, 0], win(np.vstack([dp, P(4150, 0)[None]]), 30), '4. The west viaduct over Millvale (one 780 m curve)',
          [(dp[len(dp) // 3] + np.array([0, -60]), 'D joins the Indy curve on R 700 m (no reverse curve)'), (dp[len(dp) // 2] + np.array([40, 40]), 'R5 under the deck, lower level')],
          'upper deck: D 2 | Indy 2    lower, under it: R5 2')
    panel(axs[1, 1], win(sw(4250, 5700, -40, 30)), '5. North of Arlington: straight, one curve, straight; W and B move east on the curve',
          [(P(4500, -50), 'trunk curve 1 R 1,310 m (s 4,260-4,928); W and B one curve each, 1,200-1,223 m'), (P(5468, -45), 'Northside / Spring Grove island, inside the same width'),
           (P(5150, 40), 'straight s 4,928-5,354 through Ludlow'), (P(5570, 40), 'viaduct ends (s 5,570); trunk curve 2 R 800 m from s 5,354')],
          W2E + 'W 2 | B SB | (island spacing) | B NB | Dayton 2 | Norwood 2 | E 2\nconstant 58.8 m deck, s 4,880-5,570')
    panel(axs[1, 2], win(sw(5250, 7450, -70, 70), 20), '6. Ludlow to the Mill Creek bridge: curve 2, 43 m straight, curve 3, straight',
          [(P(5450, 40), 'OH-75 (east) and the culvert (west) hold the straight here'), (P(6050, -75), 'curve 3 (left, R 1,250 m): forced by the open creek bend and the bridge line'),
           (P(6700, 45), "straight on today's line from s 6,248"), (P(7330, 45), "today's creek bridge kept (s ~7,350)")],
          'trunk: curve 1 R 1,310 | straight | curve 2 R 800 | 43 m straight | curve 3 R 1,250 | straight\nclear of the culvert south-west of Albone; blue dashes: today\'s line')
    fig.legend(leg, legt, loc='lower center', ncol=8, fontsize=9, frameon=False)
    plt.subplots_adjust(wspace=0.03, hspace=0.07, bottom=0.06)
    plt.savefig(SP + 'trunk2/viaduct_plan4.png', dpi=110, bbox_inches='tight'); plt.close(fig)
    fig, axs = plt.subplots(2, 3, figsize=(25, 19))
    panel(axs[0, 0], win(sw(1380, 1960, -80, 25), 25), 'Z1. Western: the twin bores leave on the Western straight',
          [(P(1440, -55), 'Western north platform end'), (P(1800, -60), 'bores start their single curve at s ~1,750 (R ~4,550 m)'), (P(1700, 10), 'W pair tight against Indy, directly over the bores')], tags=1560)
    panel(axs[0, 1], win(sw(1950, 2480, -50, 25), 25), 'Z2. Straight: bores parallel from s 2,150; island in the box',
          [(P(2120, -55), 'bores parallel to the trunk from s 2,150'), (P(2300, -55), 'Straight island (box, below the viaduct)'), (P(2050, 10), 'W pair tight against Indy to s 2,235, then one 620 m curve out')], tags=2440)
    panel(axs[0, 2], win(sw(2480, 3020, -45, 25), 25), 'Z3. W pair out on one 620 m curve (s 2,235-2,550), clear long before B comes up',
          [(P(2556, -50), 'W pair out at s 2,550 (B 12.9 m below in the box)'), (P(2758, -50), 'open ramp from here (B 6.8 m below the viaduct)'), (P(2990, -50), 'Camp Washington island starts')], tags=2700)
    panel(axs[1, 0], win(sw(3080, 3650, -45, 25), 25), 'Z4. The D junction: D turns in between the B tracks',
          [(P(3166, -50), 'Camp Washington island ends'), (P(3300, -50), 'turnouts: D SB off B SB, D NB off B NB, both inward (no crossing)'), (P(3500, -50), 'D climbs 2.5% from s 3,250')], tags=3600)
    panel(axs[1, 1], win(sw(3700, 4330, -95, 25), 20), 'Z5. Deck departure, R5, Arlington',
          [(P(3850, 15), 'Indy climbing; deck curve starts s 3,904'), (P(3960, -60), 'R5 leaves the west pair; R5 NB crosses W1 on the level'),
           (P(4075, 15), 'deck over Arlington\'s south 60 m (red)')], tags=3760)
    panel(axs[1, 2], win(sw(5250, 5780, -45, 30), 25), 'Z6. Northside / Spring Grove: island inside the constant width',
          [(P(5300, -50), 'same width since s 4,880: no step-out'), (P(5468, 30), 'Northside island; curve 2 (R 800 m) starts s 5,354'), (P(5570, 30), 'viaduct ends; W and B SB in on one curve (~730 m)')], tags=5700)
    fig.legend(leg, legt, loc='lower center', ncol=8, fontsize=9, frameon=False)
    plt.subplots_adjust(wspace=0.03, hspace=0.07, bottom=0.06)
    plt.savefig(SP + 'trunk2/viaduct_zoom4.png', dpi=150, bbox_inches='tight'); plt.close(fig)
    section_sheet(SP + 'trunk2/viaduct_sections4.png', [
        (1900, 'bores deep under the tight west pair'), (2300, 'Straight: island in the box, west pair right above it'), (2600, 'west pair stepping out over the box'),
        (2850, 'B on the open ramp, west pair beside it'), (3066, 'Camp Washington island'), (3500, 'D between the B tracks, climbing'),
        (3980, 'Indy and D up; Indy crosses over B NB'), (4146, 'Arlington, deck crossing (KMZ position)'), (4600, 'W and B on their one curve east'),
        (5100, 'constant width, island spacing held to Northside'), (5468, 'Northside / Spring Grove island'), (6100, 'compact again on the fill')])
    print('ok')
