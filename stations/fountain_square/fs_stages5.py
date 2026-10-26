"""Fountain Square built piece by piece, version 5 (2026-10-05): the version 4 history drawn straight from fs_model.py, so the
stages, the level plans (fs_levels4.py) and the 3D view (fs_3d.py) show the same complex. Changes from version 4 come from
laying out the levels: crossunders under Vine, the TRI hall's north arm, an east hall, the B halls and Walnut passage, and 20
entrances instead of 31."""
import sys, os, textwrap
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.patches import Rectangle, Polygon as MPoly
from fs_model import *
from fs_geom import put_badge, COLS, HERE, TOWER

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'fs_stages.png')
U0, U1, V0, V1 = -200, 182, -145, 240
halo = [pe.withStroke(linewidth=2.6, foreground='white')]
ERA = {'1905': 0, '1907': 0, '1913': 1, '1927': 2, '1931': 2, '1936': 3, '1958': 4, '1985': 5, 'B': 6, '1999': 7, 'today': 8}
LINE_ERA = {'1': 0, '2': 0, '7': 1}
NEW_M, NEW_T, OLD, OLD_E, NEW_E = '#f3d57a', '#f8d9a8', '#f0e8cf', '#b8ab84', '#8a6a00'
STAGES = [
    ('1905–07', 'Lines 1 and 2, one complex', "Planned and built together under the Cincinnati Plan; Line 1 opens November 1905, Line 2 in 1907; "
     "Fountain Square enlarged. Only what opening day needed: Line 1's ticket hall and two crossunders, a ticket hall over Line 2's south end, "
     "a stair from the square's Vine end down to Line 2 northbound, a link from Line 2 northbound east along 5th's south side to Line 1's hall "
     "(jogging round a sewer chamber), and a crossunder for Line 2 southbound."),
    ('1913', 'Line 7 (Queen City Line)', "Built in a hurry for the Exposition. Two narrow passages down Vine, one each side of Line 2's tunnel, "
     "to the north ends of Line 2's platforms, reached from both Line 7 platforms by crossunders under its tracks. Line 1 to Line 7 means "
     "walking the length of Line 2's northbound platform."),
    ('1927–31', 'First add-ons', "1927: the city cuts a passage under the square from the west end of Line 1's westbound platform to the landing "
     "of the 1907 stair, stepping north round the fountain's footings. 1931: a department store on 5th's south side tunnels its basement into "
     "the 1907 link."),
    ('1936', 'Vine mezzanine (federal relief works)', "A mezzanine over Line 2's box north of Line 1's tunnel, built while trains ran below; "
     "stairs to both platforms. The 1907 stair and the 1927 passage now land on it, and Line 2's 1907 crossunder is closed."),
    ('1958', 'Sixth Street link', "The Vine frontage north of the square is rebuilt, and the developer runs a corridor through the new basement "
     "from the mezzanine's north end to Line 7's eastbound platform, doglegging round the columns and the loading-dock ramp. Line 1 to Line 7 "
     "is level at last."),
    ('1985', 'TRI A and D (Basin Crossover Tunnel)', "Mined caverns, 28 m. The gated TRI hall under the square, door into Line 2 northbound, "
     "with an arm north under the 1958 building to the westbound island and a stair up to the 1958 corridor; a sunken court cut into the square "
     "beside the 1927 passage, like Hallidie Plaza. A west hall on the Vine-Race block (Line 2 southbound, the 1913 west passage) and an east "
     "hall reaching to the Walnut frontage, with its own entrance."),
    ('after 1985', 'TRI B (year open)', "Under Walnut, 42 m, from just north of the A/D tunnels to 7th. A hall under Line 1, stairs down from both Line 1 platforms, and a "
     "passage up Walnut past the A/D east hall to a south-end hall, where escalators start down beyond the A/D tunnels; north hall at 6th, "
     "reached from Line 7's east end by a passage under its tunnel; a third hall between 6th and 7th. Entrances in the rebuilt corner buildings."),
    ('1999', 'Pan Am Tower', "Rebuilds the Vine-Race block: the 1985 west hall becomes its lowest basement, with lobbies on 5th and 6th opening "
     "into it. The shaft stands on the block's north half, clear of the A/D caverns, with only the podium over them."),
    ('today', 'Entrances', "20 entrances, numbered for the station map, and elevators added through the complex. Each passage tagged with the "
     "year it was cut."),
]
TAGS = [((42, -77), '1905'), ((-10, -75), '1907'), ((-80, -109), '1907'), ((-2, -96), '1931'), ((-74, 45), '1913'), ((-24, -51), '1927'),
        ((-54.5, -20), '1936'), ((-20, 42), '1958'), ((22, -26), '1985'), ((-92, 24), '1985 / 1999'), ((64, 25), '1985'),
        ((53, 92), 'after 1985'), ((100, -40), 'after 1985'), ((100, 23), 'after 1985'), ((70, 170), 'after 1985')]
EK = {'pavilion': '#7a5d00', 'court': '#3b7d3b', 'tower': '#4f6d8f', 'building': '#1e1e1e', 'sidewalk': 'white'}


def R_(ax, u0, u1, v0, v1, fc, ec, zo, lw=0.9, ls='-', alpha=1.0):
    ax.add_patch(Rectangle((u0, v0), u1 - u0, v1 - v0, facecolor=fc, edgecolor=ec, lw=lw, ls=ls, alpha=alpha, zorder=zo))


def poly(ax, g, fc, ec, zo, lw=0.9, ls='-', alpha=1.0, hatch=None):
    for q in (list(g.geoms) if hasattr(g, 'geoms') else [g]):
        ax.add_patch(MPoly(np.asarray(q.exterior.coords), closed=True, facecolor=fc, edgecolor=ec, lw=lw, ls=ls, zorder=zo, alpha=alpha, hatch=hatch))


def T(ax, xy, s, fs=6.6, **kw):
    kw.setdefault('ha', 'center'); kw.setdefault('va', 'center')
    ax.text(*xy, s, fontsize=fs, zorder=kw.pop('zorder', 12), path_effects=halo, **kw)


def streets(ax):
    ax.add_patch(Rectangle((U0, V0), U1 - U0, V1 - V0, facecolor='#e3e1da', edgecolor='none', zorder=0))
    for a, b in ((-64.5, -44.5), (77.5, 96.5)):
        R_(ax, a, b, V0, V1, 'white', 'none', 0.1)
    R_(ax, U0, U1, 76.5, 92.0, 'white', 'none', 0.1)
    R_(ax, U0, -44.5, -68.0, -47.0, 'white', 'none', 0.1)
    R_(ax, -44.5, 77.5, -92.0, -55.0, 'white', 'none', 0.1)
    R_(ax, 77.5, U1, -85.0, -45.0, 'white', 'none', 0.1)
    R_(ax, -44.5, 33.0, -55.0, 0.0, '#dfe9d3', '#8aa476', 0.2, lw=0.7)
    R_(ax, 105.0, U1, -78.0, -55.0, '#dfe9d3', '#8aa476', 0.2, lw=0.7)
    T(ax, (14, -6), 'Fountain Square', fs=5.8, color='#4d6b3a', style='italic')
    T(ax, (128, -73), 'Government Sq', fs=5.6, color='#4d6b3a', style='italic')
    for nm, x, y, rot in (('Vine', -54.5, V1 - 14, 90), ('Walnut', 87, -128, 90), ('6th', U0 + 9, 84.25, 0), ('5th', U0 + 9, -57.5, 0)):
        T(ax, (x, y), nm, fs=6.2, color='#777777', style='italic', rotation=rot)


def line_box(ax, nm, new, zo):
    L = LINES[nm]
    if L['axis'] == 'u':
        box_ = (L['a'], L['b'], L['c'] - B2, L['c'] + B2); run = [(U0, L['a'], L['c'] - 4.5, L['c'] + 4.5), (L['b'], U1, L['c'] - 4.5, L['c'] + 4.5)]
    else:
        box_ = (L['c'] - B2, L['c'] + B2, L['a'], L['b']); run = [(L['c'] - 4.5, L['c'] + 4.5, V0, L['a']), (L['c'] - 4.5, L['c'] + 4.5, L['b'], V1)]
    for r in run:
        R_(ax, *r, 'white' if new else '#ececec', '#555555' if new else '#9a9a9a', zo - 0.2, lw=0.6)
    R_(ax, *box_, 'white' if new else '#ececec', '#222222' if new else '#9a9a9a', zo, lw=1.0)
    for p in PARTS:
        if p['kind'] == 'plat' and p.get('line') == nm:
            poly(ax, p['geom'], COLS[nm] if new else '#d6d6d6', '#222222' if new else '#9a9a9a', zo + 0.1, lw=0.5)


def tri_level(ax, lv, new, zo):
    for c in CAVERNS:
        if c['level'] == lv:
            poly(ax, c['geom'], 'white' if new else '#ececec', ('#7a1010' if lv == -3 else COLS['B']) if new else '#9a9a9a', zo, lw=1.0)
    for p in PARTS:
        if p['level'] == lv and p['kind'] == 'island':
            poly(ax, p['geom'], ('#f6c9cd' if lv == -3 else '#c9daf0') if new else '#dddddd', '#222222' if new else '#9a9a9a', zo + 0.05, lw=0.5)
    if lv == -3:                                           # running tunnels beyond the caverns
        for v in (1.4, 28.4):
            R_(ax, U0, AD_U[0], v - 3.5, v + 3.5, '#fbe3e5' if new else '#f0f0f0', '#7a1010' if new else '#9a9a9a', zo - 0.1, lw=0.6)
            R_(ax, AD_U[1], U1, v - 3.5, v + 3.5, '#fbe3e5' if new else '#f0f0f0', '#7a1010' if new else '#9a9a9a', zo - 0.1, lw=0.6)
    else:
        R_(ax, B_ISL[0] - 2, B_ISL[1] + 2, V0, B_V[0], '#e3edf8' if new else '#f0f0f0', COLS['B'] if new else '#9a9a9a', zo - 0.1, lw=0.6)


def piece(ax, p, new, zo):
    tri = p['op'] == 'tri'
    if p['kind'] == 'court':
        poly(ax, p['geom'], '#cfe6c4' if new else '#e6eee0', '#3b7d3b' if new else '#9fb593', zo, lw=1.0, hatch='....'); return
    fc = (NEW_T if tri else NEW_M) if new else OLD
    ec = NEW_E if new else OLD_E
    if p['kind'] == 'mezz':                                # over Line 2's box: see-through, so the platforms read
        poly(ax, p['geom'], fc, 'none', zo, lw=0, alpha=0.5); poly(ax, p['geom'], 'none', ec, zo + 0.01, lw=1.1)
    elif p['kind'] == 'xunder':
        poly(ax, p['geom'], fc, ec, zo, lw=0.9, ls=(0, (3, 2)))
    else:
        poly(ax, p['geom'], fc, ec, zo, lw=0.9)


FW = 22.0; PW_IN = 7.15; PH_IN = PW_IN * (V1 - V0) / (U1 - U0)
FH = 0.95 + 3 * (PH_IN + 1.05) + 1.55
W = PW_IN / FW; H = PH_IN / FH; pitch = (PH_IN + 1.05) / FH
y1 = 1 - 0.95 / FH - H
pos = [(0.008 + i * 0.331, y1 - r * pitch) for r in range(3) for i in range(3)]
LAST = len(STAGES) - 1
fig = plt.figure(figsize=(FW, FH))
for st, ((yr, name, note), (x, y)) in enumerate(zip(STAGES, pos)):
    ax = fig.add_axes([x, y, W, H]); ax.set_xlim(U0, U1); ax.set_ylim(V0, V1); ax.set_aspect(1); ax.set_xticks([]); ax.set_yticks([])
    for s_ in ax.spines.values():
        s_.set_color('#999999')
    ax.set_title('%s  %s' % (yr, name), fontsize=11, loc='left', weight='bold')
    ax.text(0.0, -0.01, '\n'.join(textwrap.wrap(note, 128)), transform=ax.transAxes, fontsize=7.3, va='top', color='#333333')
    streets(ax)
    new = lambda era: ERA[era] == st and st != LAST
    built = lambda era: ERA[era] <= st
    if st >= ERA['B']:
        tri_level(ax, -4, new('B'), 1.8)
    if st >= ERA['1985']:
        tri_level(ax, -3, new('1985'), 2.0)
    for p in PARTS:                                        # level -2 pieces (TRI halls under the Metro)
        if p['level'] == -2 and p['kind'] != 'plat' and built(p['era']):
            piece(ax, p, new(p['era']), 2.6 if p['op'] == 'tri' else 3.5)
    line_box(ax, '2', new('1907'), 3.0)
    if st < ERA['1936']:                                   # Line 2's own crossunder, 1907, closed 1936
        R_(ax, -64.0, -45.0, -100.0, -95.0, NEW_M if new('1907') else OLD, NEW_E if new('1907') else OLD_E, 3.4, ls=(0, (3, 2)))
    else:
        R_(ax, -64.0, -45.0, -100.0, -95.0, 'none', '#b04040' if st == ERA['1936'] else '#c9a0a0', 3.4, lw=0.8, ls=(0, (1, 1.5)))
    line_box(ax, '1', new('1905'), 4.0)
    if st >= ERA['1913']:
        line_box(ax, '7', new('1913'), 4.0)
    for p in PARTS:
        if p['level'] == -1.5 and built(p['era']):
            piece(ax, p, new(p['era']), 4.35)
    for p in PARTS:
        if p['level'] == -1 and p['kind'] != 'plat' and built(p['era']) and p['era'] != 'today':
            piece(ax, p, new(p['era']), 4.5 if p['kind'] != 'court' else 4.6)
    if st == ERA['1958']:
        R_(ax, -44.5, -8.0, 0.0, 76.5, 'none', '#444444', 4.7, lw=1.0, ls=(0, (5, 3)))
        T(ax, (-26, 8), 'rebuilt\n1958', fs=5.8, color='#444444', style='italic')
    if st >= ERA['1999']:
        R_(ax, -187.5, -64.5, -47.0, 76.5, 'none', '#444444', 4.8, lw=1.0, ls=(0, (5, 3)))
        R_(ax, *TOWER, '#cfd8e3' if new('1999') else '#e4e8ee', '#333333', 4.9, lw=1.2, alpha=0.9)
        T(ax, (-126, 47), 'Pan Am\nTower', fs=6.0, weight='bold')
    if st == LAST:
        for p in PARTS:
            if p['era'] == 'today':
                piece(ax, p, False, 4.5)
    lab = dict(fs=5.9, weight='bold', color='#5c4500')
    if st == 0:
        T(ax, (42, -76.5), 'ticket hall', **lab); T(ax, (-70, -127), 'ticket\nhall', ha='right', **lab)
        T(ax, (-8, -74), 'link to Line 1', **lab); T(ax, (-24, -33), 'stair to\nLine 2 NB', ha='left', **lab)
        T(ax, (-70, -97.5), 'crossunder', ha='right', fs=5.6, color='#5c4500')
        put_badge(ax, 'Metro_1', (118, -112), size=12); T(ax, (128, -112), 'level -1, 5.4 m', fs=6.2, color='#555555', ha='left')
        put_badge(ax, 'Metro_2', (-25, -140), size=12); T(ax, (-15, -140), 'level -2, 12 m (opens 1907)', fs=6.2, color='#555555', ha='left')
    if st == 1:
        T(ax, (-70, 48), 'Vine W\nto 2 SB', ha='right', **lab); T(ax, (-40, 48), 'Vine E\nto 2 NB', ha='left', **lab)
        put_badge(ax, 'Metro_7', (-120, 108), size=12); T(ax, (-110, 108), 'level -1', fs=6.2, color='#555555', ha='left')
    if st == 2:
        T(ax, (-14, -57), '1927 passage', **lab); T(ax, (-2, -112), '1931 store link', ha='left', **lab)
    if st == 3:
        T(ax, (-70, -10), 'mezzanine', ha='right', **lab); T(ax, (-70, -97.5), 'closed', ha='right', fs=5.8, color='#b04040', weight='bold')
    if st == 4:
        T(ax, (-22, 42), 'basement\ncorridor', ha='left', **lab)
    if st == 5:
        T(ax, (-7.5, -24), 'sunken\ncourt', fs=6.0, weight='bold', color='#2d5e2d'); T(ax, (10, -40), 'TRI hall', fs=6.0, weight='bold', color='#7a3b00')
        T(ax, (-96, 17), 'west\nhall', fs=6.0, weight='bold', color='#7a3b00'); T(ax, (40, 28), 'east\nhall', fs=6.0, weight='bold', color='#7a3b00')
        put_badge(ax, 'TRI_A', (-185, 48), size=12); put_badge(ax, 'TRI_D', (-172, 48), size=12)
        T(ax, (-163, 48), 'level -3, 28 m', fs=6.2, color='#555555', ha='left')
    if st == 6:
        T(ax, (100, -57.5), 'Walnut hall', fs=6.0, weight='bold', color='#0b3d78', ha='left'); T(ax, (100, 23), 'B south end hall', fs=6.0, weight='bold', color='#0b3d78', ha='left')
        T(ax, (100, 70), 'B north hall', fs=6.0, weight='bold', color='#0b3d78', ha='left')
        T(ax, (53, 97), 'to Line 7', **lab)
        put_badge(ax, 'TRI_B', (125, 180), size=12); T(ax, (135, 180), 'level -4, 42 m', fs=6.2, color='#555555', ha='left')
    if st == 7:
        T(ax, (-87, 17), 'tower\nbasement', fs=6.0, weight='bold', color='#7a3b00')
    if st == LAST:
        tag = dict(fs=5.6, color='#6b5a2a', style='italic', weight='bold')
        for (u, v), s_ in TAGS:
            T(ax, (u, v), s_, **tag)
        for e in ENT:
            u, v = e['xy']; rnd = e['kind'] in ('building', 'sidewalk')
            ax.plot([u], [v], marker='o' if rnd else 's', ms=11.5 if rnd else 10.5, mfc=EK[e['kind']],
                    mec='#1e1e1e' if e['kind'] == 'sidewalk' else 'white', mew=1.0 if e['kind'] == 'sidewalk' else 0.8, zorder=13.5)
            ax.text(u, v, str(e['n']), fontsize=6.3, color='#1e1e1e' if e['kind'] == 'sidewalk' else 'white', weight='bold', ha='center', va='center', zorder=14)

lx = fig.add_axes([0.008, 0.004, 0.984, pos[-1][1] - 0.035]); lx.axis('off'); lx.set_xlim(0, 1); lx.set_ylim(0, 1)
lx.text(0.0, 0.99, 'Entrances (today panel)', fontsize=8.5, weight='bold', va='top')
for k, e in enumerate(ENT):
    col, row = k // 5, k % 5
    lx.text(0.0 + col * 0.25, 0.80 - row * 0.17, '%d  %s (%s)' % (e['n'], e['name'], {'B': 'after 1985'}.get(e['era'], e['era']) if e['era'] != 'today' else 'later'),
            fontsize=8.0, va='top', color=EK[e['kind']] if e['kind'] not in ('building', 'sidewalk') else '#1e1e1e')
fig.text(0.008, 1 - 0.15 / FH, 'Fountain Square, built piece by piece', fontsize=18, weight='bold', va='top')
fig.text(0.008, 1 - 0.5 / FH, '\n'.join(textwrap.wrap('Each panel: what that stage built in colour (Metro yellow, TRI orange), earlier works grey. Passages added as the need '
         'arose and as blocks were rebuilt, under streets, the square, or the basements of buildings being rebuilt. Depths are drawing values. '
         'Entrances: black circle, inside a building; white circle, sidewalk stair; square, pavilion (gold), sunken court (green), Pan Am Tower (blue-grey).', 230)),
         fontsize=8.2, color='#555555', va='top')
fig.savefig(OUT, dpi=125)
print(OUT)
