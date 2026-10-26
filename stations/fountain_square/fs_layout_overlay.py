"""Overlay: the model's platforms (grey) against Ben's FS Layout.kmz (2026-10-05), in the drawing frame."""
import json, numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from shapely.geometry import box
from fs_model import PARTS, CAVERNS, LINES
K = {k: np.array(v) for k, v in json.load(open('fs_kmz_layout.json')).items()}
NS = {'Vine': (-64.5, -44.5), 'Walnut': (77.5, 96.5)}
EW = {'5th': (-68.0, -47.0), '6th': (76.5, 92.0)}
COL = {'1': '#ffce00', '2': '#5bb8d4', '7': '#00a88f', 'A': '#e3051c', 'B': '#0064b0'}
U0, U1, V0, V1 = -170, 200, -150, 200
fig = plt.figure(figsize=(13, 13.6)); ax = fig.add_axes([0.03, 0.12, 0.94, 0.80]); ax.set_aspect(1)
ax.set_xlim(U0, U1); ax.set_ylim(V0, V1); ax.axis('off')
ax.add_patch(Rectangle((U0, V0), U1 - U0, V1 - V0, fc='#ebe7e0', ec='#999999', lw=0.8, zorder=0))
for nm, (a, b) in NS.items():
    ax.add_patch(Rectangle((a, V0), b - a, V1 - V0, fc='white', ec='none', zorder=1)); ax.text((a + b) / 2, V1 - 6, nm, rotation=90, ha='center', va='top', fontsize=10, style='italic', color='#777777', zorder=2)
for nm, (a, b) in EW.items():
    ax.add_patch(Rectangle((U0, a), U1 - U0, b - a, fc='white', ec='none', zorder=1)); ax.text(U0 + 3, (a + b) / 2, nm, ha='left', va='center', fontsize=10, style='italic', color='#777777', zorder=2)
ax.add_patch(Rectangle((-44.5, -47.0), 77.5, 47.0, fc='#dfeccf', ec='none', zorder=1.5)); ax.text(-5.75, -23.5, 'Fountain Square', ha='center', va='center', fontsize=9, color='#6a8a50', style='italic', zorder=2)
# model now: platforms and caverns, grey dashed
for p in PARTS:
    if p['kind'] in ('plat', 'island'):
        x0, y0, x1, y1 = p['geom'].bounds
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc='#9a9a9a', ec='#6b6b6b', lw=0.8, alpha=0.55, zorder=3))
for c in CAVERNS:
    x0, y0, x1, y1 = c['geom'].bounds
    ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc='none', ec='#6b6b6b', lw=1.0, ls=(0, (4, 3)), zorder=3))
# Ben's layout: boxes drawn on his centrelines (Metro station box 18.9 m, A/D cavern 19 m, B cavern 21 m)
def band(p, w, col, z=5, ls='-', alpha=0.45, lw=2.0):
    a, b = p[0], p[-1]; d = (b - a) / np.hypot(*(b - a)); n = np.array([-d[1], d[0]])
    poly = np.array([a - n * w / 2, b - n * w / 2, b + n * w / 2, a + n * w / 2])
    ax.fill(poly[:, 0], poly[:, 1], fc=col, ec=col, alpha=alpha, zorder=z, lw=0)
    ax.plot(*np.r_[poly, poly[:1]].T, color=col, lw=lw, ls=ls, zorder=z + 0.1)
    ax.plot(*p.T, color='black', lw=1.0, zorder=z + 0.2)
band(K['Line 1 Platform'], 18.9, COL['1']); band(K['Line 2 Platform'], 18.9, COL['2']); band(K['Line 7 Platform'], 18.9, COL['7'])
band(K['RER A-D Platform'], 19.0, COL['A'])
ad2 = K['RER A-D Platform'] - np.array([0, 27.0])                      # second island, 27 m south as the twin caverns now
band(ad2, 19.0, COL['A'], ls=(0, (5, 3)), alpha=0.22)
ax.plot(*K['RER A/D Platform 2'].T, color=COL['A'], lw=1.2, ls=':', zorder=5)
band(K['RER B Platform'], 21.0, COL['B'], z=4, alpha=0.35)
# the crossing
xb = box(75.4, -44.8, 96.4, 160.1).intersection(box(-73.2, -24.3, 131.2, 21.7))
x0, y0, x1, y1 = xb.bounds
ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc='none', ec='black', hatch='///', lw=1.5, zorder=6))
ax.annotate('B passes under both A/D caverns here:\nabout 2 to 3 m of rock between A/D\'s floor\nand B\'s roof at the drawing depths',
            xy=(x1, (y0 + y1) / 2), xytext=(108, -100), fontsize=9.5, ha='left', va='center', zorder=8,
            arrowprops=dict(arrowstyle='-', color='black', lw=0.8))
lab = [('Line 1: 16.6 m west', K['Line 1 Platform'], (0, -15)), ('Line 2: 20.9 m north', K['Line 2 Platform'], (-60, 0)),
       ('Line 7: 6.2 m west', K['Line 7 Platform'], (0, 15)), ('A/D (westbound island): 66.2 m east', K['RER A-D Platform'], (0, 15)),
       ('B: 24.4 m south', K['RER B Platform'], (34, 40))]
for t, p, (dx, dy) in lab:
    m = p.mean(0); ax.text(m[0] + dx, m[1] + dy, t, fontsize=10, weight='bold', ha='center', va='center', zorder=9,
                           bbox=dict(fc='white', ec='none', alpha=0.85, pad=1.5))
ax.text(ad2.mean(0)[0] + 10, ad2.mean(0)[1] - 15, 'A/D eastbound island: proposed 27 m south (twin caverns, as now)', fontsize=9, ha='center', zorder=9,
        bbox=dict(fc='white', ec='none', alpha=0.85, pad=1.5))
fig.text(0.03, 0.965, 'Fountain Square: your layout against the model', fontsize=19, weight='bold', va='top')
fig.text(0.03, 0.935, 'Grey: platforms and caverns in the model now. Colour: your FS Layout.kmz centrelines (black) with the station box or cavern around them '
         '(Metro 18.9 m, A/D 19 m, B 21 m).\nDotted red: your "Platform 2" marker. Frame turned with the street grid; true north is 11° clockwise of up.',
         fontsize=10, color='#555555', va='top')
ax.annotate('', xy=(U1 - 12 + 12 * np.sin(np.radians(11)), V0 + 12 + 12 * np.cos(np.radians(11))), xytext=(U1 - 12, V0 + 12),
            arrowprops=dict(arrowstyle='-|>', color='black', lw=1.8), zorder=9)
ax.text(U1 - 16, V0 + 12, 'N', fontsize=11, weight='bold', ha='right', va='bottom', zorder=9)
fig.savefig('fs_layout_overlay.png', dpi=130); print('fs_layout_overlay.png')
