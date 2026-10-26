"""Fountain Square, a plan of each level (-1 to -4) with every stair, escalator and elevator, from fs_model.py (2026-10-05,
Ben: "let's try laying out the levels, with the 4 levels mapped with stairs/escalators/elevators"). Stairs and escalators
coloured by the way they go from the floor shown (orange up, blue down), as on the Republic plans."""
import sys, os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.patches import Rectangle, Polygon as MPoly, PathPatch
from matplotlib.path import Path
from shapely.geometry import Point, LineString
from fs_model import *
from fs_geom import put_badge, COLS, NS, EW, HERE

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'fs_levels4.png')
U0, U1, V0, V1 = -200, 180, -145, 240
UP, DN = '#e07b2f', '#3d6fb6'
ESC = '#a3988a'
LIFT = '#2e7d4b'
GATE = '#a3121c'
halo = [pe.withStroke(linewidth=2.4, foreground='white')]
TINT = {'1': '#ffe680', '7': '#8fd8c8', '2': '#c6e8f1'}
EDGEC = {'1': '#8a6d00', '7': '#00624f', '2': '#2f7f93'}
TERM = {('1', 'EB'): 'to Southgate', ('1', 'WB'): 'to Finneytown', ('7', 'EB'): 'to Roselawn', ('7', 'WB'): 'to Visitation',
        ('2', 'NB'): 'to Anthony Wayne', ('2', 'SB'): 'to Winston Park', ('A', 'EB'): 'to Walnut Hills', ('A', 'WB'): 'to Union Terminal',
        ('D', 'EB'): 'to Newport', ('D', 'WB'): 'to Norwood', ('B', 'NB'): 'to Dayton', ('B', 'SB'): 'to Falmouth'}
TCOL = {'1': COLS['1'], '7': COLS['7'], '2': '#5bb8cf', 'A': COLS['A'], 'D': COLS['D'], 'B': COLS['B']}
SHORT = {'Line 1 westbound platform': '1 WB', 'Line 1 eastbound platform': '1 EB', 'Line 7 westbound platform': '7 WB',
         'Line 7 eastbound platform': '7 EB', 'Line 2 southbound platform': '2 SB', 'Line 2 northbound platform': '2 NB',
         'Line 2 south hall': 'hall', '1907 link': 'link', 'Vine mezzanine': 'mezz', 'Sixth Street link': 'corridor',
         'Sunken court': 'court', 'TRI hall': 'TRI hall', 'TRI hall north arm': 'TRI hall', 'West hall': 'W hall', 'East hall': 'E hall',
         'Walnut hall': 'Walnut hall', 'B south end hall': 'B hall', 'B north hall': 'B hall', 'Line 7 east hall': 'hall', 'A/D eastbound island': 'A/D EB',
         'A/D westbound island': 'A/D WB', 'B island': 'B', 'Vine west passage': 'Vine W', 'Vine east passage': 'Vine E',
         'B north end hall': 'B hall', '5th & Vine SW vestibule': 'exit 5', 'Line 1 crossunder': 'x-under', 'Line 1 east crossunder': 'x-under',
         'Line 7 crossunder, Vine E': 'x-under', 'Line 7 crossunder, Vine W': 'x-under'}
LEVELS = [(-1, 'Level -1  ·  5 m', 'Lines 1 and 7, the passages, crossunders (dashed, 9 m)'),
          (-2, 'Level -2  ·  12 m', 'Line 2, the TRI halls'),
          (-3, 'Level -3  ·  28 m', 'TRI A and D'),
          (-4, 'Level -4  ·  42 m', 'TRI B')]


def poly(ax, g, fc, ec, zo, lw=0.8, ls='-', hatch=None, alpha=1.0):
    for q in (list(g.geoms) if hasattr(g, 'geoms') else [g]):
        ax.add_patch(MPoly(np.asarray(q.exterior.coords), closed=True, facecolor=fc, edgecolor=ec, lw=lw, ls=ls, zorder=zo,
                           hatch=hatch, alpha=alpha))


def T(ax, xy, s, fs=6.4, **kw):
    kw.setdefault('ha', 'center'); kw.setdefault('va', 'center')
    ax.text(*xy, s, fontsize=fs, zorder=kw.pop('zorder', 12), path_effects=halo, **kw)


def part_at(level, xy):
    p = Point(xy)
    best = None
    for q in PARTS:
        if q['level'] == level and q['geom'].buffer(0.4).contains(p):
            if best is None or q['geom'].area < best['geom'].area:
                best = q
    return best


def base(ax):
    ax.set_aspect(1); ax.set_xlim(U0, U1); ax.set_ylim(V0, V1); ax.set_xticks([]); ax.set_yticks([])
    for s_ in ax.spines.values():
        s_.set_color('#999999')
    ax.add_patch(Rectangle((U0, V0), U1 - U0, V1 - V0, facecolor='#ebe8e1', edgecolor='none', zorder=0))
    for nm, (a, b) in NS.items():
        ax.add_patch(Rectangle((a, V0), b - a, V1 - V0, facecolor='white', edgecolor='none', zorder=0.1))
        if U0 < a < U1:
            ax.text((a + b) / 2, V1 - 3, nm, rotation=90, ha='center', va='top', fontsize=8.5, style='italic', color='#9a9a9a', zorder=0.3)
    for nm, (a, b) in EW.items():
        if b > V0 and a < V1:
            ax.add_patch(Rectangle((U0, a), U1 - U0, b - a, facecolor='white', edgecolor='none', zorder=0.1))
            ax.text(U0 + 3, (a + b) / 2, nm, ha='left', va='center', fontsize=8.5, style='italic', color='#9a9a9a', zorder=0.3)
    ax.add_patch(Rectangle((-64.5, -92.0), 142.0, 45.0, facecolor='white', edgecolor='none', zorder=0.1))     # 5th, Vine to Walnut
    ax.add_patch(Rectangle((-44.5, -55.0), 77.5, 55.0, facecolor='#e2ecd8', edgecolor='none', zorder=0.15))   # Fountain Square
    ax.add_patch(Rectangle((105.0, -78.0), U1 - 105.0, 23.0, facecolor='#e2ecd8', edgecolor='none', zorder=0.15))  # Government Sq
    ax.text(-6, -3, 'Fountain Square', fontsize=6.5, style='italic', color='#7d9a6b', ha='center', va='top', zorder=0.3)


def ghosts(ax, lv):
    for p in PARTS:
        if p['level'] != lv and not (lv == -1 and p['level'] == -1.5):
            poly(ax, p['geom'], 'none', '#c9c4ba', 0.5, lw=0.5)
    for c in CAVERNS:
        if c['level'] != lv:
            poly(ax, c['geom'], 'none', '#d4b9b9' if c['level'] == -3 else '#b9c6d8', 0.45, lw=0.5, ls=(0, (4, 3)))


def fillc(p):
    if p['kind'] == 'plat':
        return TINT[p['line']], EDGEC[p['line']]
    if p['kind'] == 'island':
        return ('#f6c9cd', '#7a1010') if p['level'] == -3 else ('#c9daf0', '#0b3d78')
    if p['kind'] == 'court':
        return '#d5ebc8', '#3b7d3b'
    if p['op'] == 'tri':
        return '#f9dde0', '#9c2a33'
    return '#f6e7b8', '#8a6a00'


def tracks(ax, lv):
    for t in TRACKS:
        if t['level'] != lv:
            continue
        b, f = np.array(t['back']), np.array(t['front']); d = (f - b) / np.hypot(*(f - b))
        b2, f2 = b - d * 14, f + d * 14
        ax.plot([b2[0], f2[0]], [b2[1], f2[1]], color=TCOL[t['line']], lw=2.6, solid_capstyle='butt', zorder=3)
        ax.annotate('', xy=f2 + d * 7, xytext=f2 - d * 1, arrowprops=dict(arrowstyle='-|>,head_width=0.45,head_length=0.8',
                                                                         color=TCOL[t['line']], lw=2.6), zorder=3)
        tip = f2 + d * 9
        # keep the label inside the frame
        tip = np.array([min(max(tip[0], U0 + 6), U1 - 6), min(max(tip[1], V0 + 6), V1 - 6)])
        hz = abs(d[0]) > 0.5
        if hz:
            ha = 'left' if d[0] > 0 else 'right'
            if (d[0] > 0 and tip[0] > U1 - 40) or (d[0] < 0 and tip[0] < U0 + 40):
                ha = 'right' if d[0] > 0 else 'left'; tip = tip + np.array([0, 5.5 if t['dir'] in ('WB',) else -5.5])
            T(ax, tip, TERM[(t['line'], t['dir'])], fs=6.6, ha=ha, color='#333333')
        else:
            q = tip + np.array([2.5, 0])
            q[1] = min(max(q[1], V0 + 30), V1 - 30)
            T(ax, q, TERM[(t['line'], t['dir'])], fs=6.6, rotation=90, color='#333333', ha='left', va='center')


def chevrons(ax, f, way, zo, col='white'):
    """small chevrons along a flight, pointing the way you go from the floor shown (way = +1 downhill, -1 uphill)."""
    s, e = np.array(f['start']), np.array(f['end']); d = np.array(f['d']) * way; n = np.array([-d[1], d[0]])
    L = np.hypot(*(e - s)); m = (s + e) / 2
    k = 1.4 if L > 12 else 1.0
    for o in ((-0.22, 0.22) if L > 20 else (0.0,)):
        c = m + np.array(f['d']) * o * L
        pts = [c - d * k + n * k * 0.9, c + d * k * 0.6, c - d * k - n * k * 0.9]
        ax.plot([p[0] for p in pts], [p[1] for p in pts], color=col, lw=1.0, solid_capstyle='round', zorder=zo + 0.05)


PLACED = []


def flights(ax, lv):
    PLACED.clear()
    for f in FLIGHTS:
        here_top = f['top'] == lv or (lv == -1 and f['top'] == -1.5)
        here_bot = f['bot'] == lv or (lv == -1 and f['bot'] == -1.5 and f['top'] == -1)
        if lv == -1 and f['top'] == -1 and f['bot'] == -1.5:
            here_top, here_bot = True, False
        if not (here_top or here_bot):
            continue
        down = here_top and not (f['bot'] == lv)
        f0 = f
        col = DN if down else UP
        dash = (lv == -1 and (f['top'] == -1.5))
        g = f['geom']; s0, e0 = np.array(f['start']), np.array(f['end']); dv = np.array(f['d']); L = np.hypot(*(e0 - s0))
        n = np.array([-dv[1], dv[0]]); w = f['w']
        if L > 15:                       # long flight: only the half nearest this floor drawn solid, the rest dashed
            poly(ax, g, 'none', col, 4.9, lw=0.8, ls=(0, (3, 2)))
            a, b = (s0, s0 + dv * L / 2) if down else (e0 - dv * L / 2, e0)
            from shapely.geometry import Polygon as SP
            g = SP([a - n * w / 2, b - n * w / 2, b + n * w / 2, a + n * w / 2])
        else:
            a, b = s0, e0
        if f['kind'] == 'stair':
            poly(ax, g, col, 'white', 5, lw=0.4, alpha=0.75 if dash else 1.0)
            Lh = np.hypot(*(b - a))
            for t in np.arange(0.9, Lh - 0.3, 1.1):
                c = a + dv * t
                ax.plot([c[0] - n[0] * w / 2, c[0] + n[0] * w / 2], [c[1] - n[1] * w / 2, c[1] + n[1] * w / 2], color='white', lw=0.35, zorder=5.02)
        else:
            poly(ax, g, ESC, col, 5, lw=1.3)
            for k in range(1, f['units']):
                o = -w / 2 + k * w / f['units']
                ax.plot([a[0] + n[0] * o, b[0] + n[0] * o], [a[1] + n[1] * o, b[1] + n[1] * o], color='white', lw=0.5, zorder=5.02)
        f = dict(f, start=tuple(a), end=tuple(b))
        chevrons(ax, f, 1 if down else -1, 5.1)
        f = f0
        # where it goes: entrance number for street flights, else the floor at the other end
        if f['ent'] is not None and not down:
            continue
        other = f['bot'] if down else f['top']
        if other == 0:
            continue
        o_xy = f['end'] if down else f['start']
        q = part_at(other, (np.array(o_xy) + np.array(f['d']) * (0.8 if down else -0.8)))
        lab = SHORT.get(q['name'], '') if q else ''
        if not lab or lab == 'x-under':
            continue
        mouth = np.array(f['start'] if down else f['end'])
        dd = np.array(f['d']) * (-1 if down else 1)                      # out of the flight, onto this floor
        pos = mouth + dd * 4.5
        txt = ('▼ ' if down else '▲ ') + lab
        if any(t_ == txt and np.hypot(*(pos - p_)) < 12 for t_, p_ in PLACED):
            continue
        PLACED.append((txt, pos))
        T(ax, pos, ('▼ ' if down else '▲ ') + lab, fs=6.0, color=col, weight='bold', zorder=13,
          ha='center' if abs(dd[1]) > 0.5 else ('left' if dd[0] > 0 else 'right'))


def lifts(ax, lv):
    for l in LIFTS:
        if lv in l['levels'] or (lv == -1 and -1.5 in l['levels']):
            x, y = l['xy']
            ax.add_patch(Rectangle((x - 1.8, y - 1.8), 3.6, 3.6, facecolor=LIFT, edgecolor='white', lw=0.5, zorder=7))
            ax.text(x, y, 'E', fontsize=4.6, color='white', weight='bold', ha='center', va='center', zorder=7.1)


def gates(ax, lv):
    for g in GATES:
        if g['level'] == lv:
            xy = np.asarray(g['geom'].coords)
            ax.plot(xy[:, 0], xy[:, 1], color=GATE, lw=1.3, zorder=8,
                    path_effects=[pe.withTickedStroke(spacing=4, length=0.7, angle=90, linewidth=0.9)])


EK = {'pavilion': '#7a5d00', 'court': '#3b7d3b', 'tower': '#4f6d8f', 'building': '#1e1e1e', 'sidewalk': 'white'}


def entrances(ax, lv):
    for e in ENT:
        if e['level'] != lv:
            continue
        rnd = e['kind'] in ('building', 'sidewalk')
        x, y = e['xy']
        ax.plot([x], [y], marker='o' if rnd else 's', ms=13 if rnd else 12, mfc=EK[e['kind']],
                mec='#1e1e1e' if e['kind'] == 'sidewalk' else 'white', mew=0.9, zorder=13.5)
        ax.text(x, y, str(e['n']), fontsize=7.4, color='#1e1e1e' if e['kind'] == 'sidewalk' else 'white', weight='bold',
                ha='center', va='center', zorder=14)


NAMES = {-1: [((-80, -109), 'Line 2\nsouth hall', 'right'), ((42, -76.5), 'Line 1 ticket hall', 'center'), ((-25, -53), '1927 passage', 'center'),
              ((-72, -15), 'Vine\nmezzanine', 'right'), ((-20, 40), 'Sixth Street\nlink (1958)', 'left'), ((-14, -31), 'sunken court', 'center'),
              ((-14, -92), '1907 link', 'center'), ((150, -40), '', 'center')],
         -2: [((-27, -38), 'TRI hall', 'center'), ((-96, 31), 'west hall\n(Pan Am\nbasement)', 'center'), ((40, 28), 'east\nhall', 'center'),
              ((100, -57.5), 'Walnut\nhall', 'left'), ((100, 23), 'B south\nend hall', 'left'), ((100, 70), 'B north\nhall', 'left'), ((14, 100), 'Line 7\neast hall', 'center'),
              ((53, 95), 'Sixth Street passage', 'center'), ((-72, 50), 'Vine W\n(1913)', 'right'), ((-40, 55), 'Vine E\n(1913)', 'left'),
              ((-17, 28), 'north\narm', 'left'), ((70, 150), 'B north\nend hall', 'right'), ((92, -28), 'Walnut\npassage', 'left')],
         -3: [((-83, 0.6), 'A/D', 'center')], -4: []}
BADGE = {-1: [('Metro_1', (120, -42)), ('Metro_7', (-150, 100))], -2: [('Metro_2', (-30, -104))],
         -3: [('TRI_A', (-160, 0.6)), ('TRI_D', (-145, 0.6))], -4: [('TRI_B', (115, 140))]}

FH = 33.5
fig = plt.figure(figsize=(26, FH))
PW = 0.488; PH = PW * 26 / FH * (V1 - V0) / (U1 - U0)
Y1 = 0.958 - PH; Y2 = Y1 - PH - 0.025
pos = {-1: (0.008, Y1), -2: (0.504, Y1), -3: (0.008, Y2), -4: (0.504, Y2)}
for lv, title, sub in LEVELS:
    ax = fig.add_axes([*pos[lv], PW, PH])
    base(ax)
    ghosts(ax, lv)
    for c in CAVERNS:
        if c['level'] == lv:
            poly(ax, c['geom'], '#f4f1ec', '#7a1010' if lv == -3 else '#0b3d78', 1.0, lw=1.0)
    for nm, L in LINES.items():
        if L['level'] == lv:
            g = R(L['a'], L['b'], L['c'] - B2, L['c'] + B2) if L['axis'] == 'u' else R(L['c'] - B2, L['c'] + B2, L['a'], L['b'])
            poly(ax, g, '#f4f1ec', '#555555', 1.0, lw=0.9)
    tracks(ax, lv)
    for p in PARTS:
        if p['level'] == lv:
            fc, ec = fillc(p)
            poly(ax, p['geom'], fc, ec, 4 if p['kind'] != 'plat' else 3.5, lw=0.8, hatch='....' if p['kind'] == 'court' else None)
        elif lv == -1 and p['level'] == -1.5:
            poly(ax, p['geom'], '#fbf3dc', '#8a6a00', 3.8, lw=0.8, ls=(0, (3, 2)))
    flights(ax, lv)
    lifts(ax, lv)
    gates(ax, lv)
    entrances(ax, lv)
    for xy, s, ha in NAMES[lv]:
        if s:
            T(ax, xy, s, fs=8.0, weight='bold', color='#5a4a1a', ha=ha)
    for nm, xy in BADGE[lv]:
        put_badge(ax, nm, xy, size=19)
    ax.set_title('%s   %s' % (title, sub), fontsize=13, loc='left', weight='bold')

# key
kx = fig.add_axes([0.008, 0.004, 0.984, Y2 - 0.03]); kx.axis('off'); kx.set_xlim(0, 100); kx.set_ylim(0, 10)
items = [(UP, 'stair up from this floor'), (DN, 'stair down from this floor')]
x = 0.5
def sw(x, y, fc, ec='white', w=2.2, h=1.2, lw=0.5):
    kx.add_patch(Rectangle((x, y), w, h, facecolor=fc, edgecolor=ec, lw=lw))
sw(x, 7.6, UP); kx.text(x + 3, 8.2, 'stair up from the floor shown', va='center', fontsize=10)
sw(x, 5.9, DN); kx.text(x + 3, 6.5, 'stair down from the floor shown', va='center', fontsize=10)
sw(x, 4.2, ESC, UP, lw=1.6); kx.text(x + 3, 4.8, 'escalators up (orange edge) or down (blue edge); chevrons point the way', va='center', fontsize=10)
kx.add_patch(Rectangle((x + 0.6, 2.5), 1.0, 1.0, facecolor=LIFT)); kx.text(x + 3, 3.0, 'elevator', va='center', fontsize=10)
kx.plot([x, x + 2.2], [1.3, 1.3], color=GATE, lw=1.6, path_effects=[pe.withTickedStroke(spacing=5, length=0.8, angle=90)])
kx.text(x + 3, 1.3, 'TRI fare line (Metro fare control at entrances and Metro-TRI doors not shown)', va='center', fontsize=10)
x2 = 36
for k, (fc, ec, s) in enumerate([('#f6e7b8', '#8a6a00', 'Metro halls and passages'), ('#f9dde0', '#9c2a33', 'TRI halls and passages'),
                                  ('#d5ebc8', '#3b7d3b', 'sunken court, open to the sky'), ('#fbf3dc', '#8a6a00', 'crossunder below the tracks (9 m), dashed')]):
    sw(x2, 7.6 - k * 1.7, fc, ec, lw=0.9 if k < 3 else 0.9); kx.text(x2 + 3, 8.2 - k * 1.7, s, va='center', fontsize=10)
kx.text(x2, 0.9, 'Grey outlines: the other levels. ▲/▼ labels: where a stair or escalator leads.', fontsize=10, color='#555555', va='center')
x3 = 66
kx.text(x3, 9.2, 'Entrances', fontsize=10.5, weight='bold', va='center')
for k, e in enumerate(ENT):
    col, row = k // 10, k % 10
    kx.text(x3 + col * 17, 8.3 - row * 0.85, '%d  %s' % (e['n'], e['name']), fontsize=8.6, va='center',
            color=EK[e['kind']] if e['kind'] not in ('building', 'sidewalk') else '#1e1e1e')
fig.text(0.008, 0.993, 'Fountain Square, level by level', fontsize=22, weight='bold', va='top')
fig.text(0.008, 0.975, 'Plans of the four levels below the street with every stair, escalator and elevator. Depths are drawing values. '
         'Frame turned 11° from north (Vine runs up the page).', fontsize=10.5, color='#555555', va='top')
fig.savefig(OUT, dpi=110)
print(OUT)
