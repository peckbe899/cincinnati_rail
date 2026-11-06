"""North trunk v4: long section and cross sections for the linked B/D climb (Camp Washington to the Indianapolis/D crossover)."""
try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, io, contextlib, importlib.util, numpy as np, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
SP = _ws.DATA
spec = importlib.util.spec_from_file_location('v4', _ws.CODE + 'nv/v4.py')
with contextlib.redirect_stdout(io.StringIO()):
    v = importlib.util.module_from_spec(spec); spec.loader.exec_module(v)
C, band, B, D, INDY, gz, deck = v.C, v.band, v.B, v.D, v.INDY, v.gz, v.deck
COL = dict(tv='#3c8d5a', apex='#16252a', indy='#6b2fa0', orr='#b0207a', bd='#2a7ab0', d='#1d5f8f', rera='#d07a1c')
fig = plt.figure(figsize=(20, 13))
ax = fig.add_axes([0.05, 0.56, 0.93, 0.40]); ax3 = fig.add_axes([0.02, 0.02, 0.96, 0.48])
ss = np.arange(2800, 5600, 5)
ax.plot(ss, [gz(*C.interpolate(s).coords[0]) for s in ss], color='#8a6a3a', lw=1, label='ground / deck surface (map 3)')
ax.plot(ss, [band(s) for s in ss], color=COL['apex'], lw=2.2, label='APEx Dayton/Norwood, ORR E, Transvalley/R5: deck + 6.5 m, then %.2f%% to Ludlow' % (100 * v.G_BAND))
si = ss[(ss >= 3600) & (ss <= v.s_end)]
ax.plot(si, [INDY(s) for s in si], color=COL['indy'], lw=1.8, label='APEx Indianapolis: 0.75% from s 3,800')
sb = ss[ss >= 2964]
ax.plot(sb, [B(s) for s in sb], color=COL['bd'], lw=2.0, label='TRI B (B/D to s %.0f): 0.40%% under the deck, %.1f%% from Monmouth, Arlington %.1f m, then to Ludlow' % (v.S_ST0, 100 * v.G2, v.Z_STN))
sd = ss[(ss >= v.S_ST0) & (ss <= v.s_end)]
ax.plot(sd, [D(s) for s in sd], color=COL['d'], lw=1.8, ls='--', label='TRI D: %.1f%% on from the station\'s south end to 174.3 m' % (100 * v.G2))
ax.add_patch(Rectangle((2964, 150.3), 204, 1.1, color=COL['bd'], alpha=0.5)); ax.text(3066, 149.6, 'Camp Washington (B, D)', fontsize=7, ha='center', va='top', color=COL['bd'])
ax.add_patch(Rectangle((v.S_ST0, v.Z_STN - 1.1), 204, 1.1, color=COL['bd'], alpha=0.5)); ax.text((v.S_ST0 + v.S_ST1) / 2, v.Z_STN + 0.6, 'Arlington (B)', fontsize=7, ha='center', color=COL['bd'])
ax.axvspan(v.S_C0, v.s_end, color=COL['indy'], alpha=0.08)
for r in v.out['streets']:
    c = '#c0392b' if 'lower' in r['result'] else '#1f4f7a'
    ax.plot(r['s'], r['z'], 'v', ms=4, color=c); ax.text(r['s'], r['z'] - 0.8, r['street'].split(' (')[0], rotation=90, fontsize=6, ha='center', va='top', color=c)
for s, t in ((3181, 'Hopple'), (v.S_TIP, 'deck tip'), (4146, 'KMZ Arlington'), (v.S_C0, 'Indianapolis + D turn west'), (v.s_end, 'clear of Transvalley/R5'), (5300, 'Ludlow')):
    ax.axvline(s, color='#999', lw=0.5); ax.text(s, 177.5, t, rotation=90, fontsize=7, va='top', ha='right')
ax.annotate('Sassafras lowered 2.4 m', (4061, 151.7), (4120, 146.0), fontsize=7, color='#c0392b', arrowprops=dict(arrowstyle='-', lw=0.5, color='#c0392b'))
ax.annotate('box under Monmouth, 5.2 m cover', (3903, 154.3), (3620, 147.5), fontsize=7, color=COL['bd'], arrowprops=dict(arrowstyle='-', lw=0.5, color=COL['bd']))
ax.set_xlim(2800, 5600); ax.set_ylim(140, 178); ax.grid(lw=0.2); ax.tick_params(labelsize=7); ax.legend(fontsize=7, loc='lower right')
ax.set_xlabel('m along the APEx line from CUT', fontsize=7)
ax.set_title('North trunk v4: B/D climb linked from Camp Washington to the Indianapolis/D crossover (levels in m)', fontsize=10, loc='left')
def at(s, o):
    p = C.interpolate(s); q = C.interpolate(s + 3); d = np.array([q.x - p.x, q.y - p.y]); d /= np.linalg.norm(d)
    return p.x + d[1] * o, p.y - d[0] * o
def trk(o, z, c): ax3.plot([o - 0.75, o + 0.75], [z, z], color=c, lw=3, solid_capstyle='butt')
def deckbar(o0, o1, z, c='#ccc'): ax3.add_patch(Rectangle((o0, z - 1.4), o1 - o0, 1.2, fc=c, ec='k', lw=0.5))
panels = [(3500, 'A  s 3,500, lobe: 10 tracks on the arch viaduct, 45.0 m, deck 54.5 m; B/D boxed under the deck (152.7 m)'),
          (4145, 'B  s 4,145, Arlington (B): Transvalley/R5, APEx 4, Indianapolis, D climbing, B island, ORR E: 77.5 m, about 87 m'),
          (4470, 'C  s 4,470: Indianapolis and D crossing west together over APEx Dayton/Norwood'),
          (5150, 'D  s 5,150: Transvalley/R5, APEx 4, B, ORR E: 47.25 m, 56.75 m')]
H = 40
for k, (s, title) in enumerate(panels):
    yb = -k * H; Y = lambda z, yb=yb: yb + (z - 140)
    ax3.text(-46, yb + 37, title, fontsize=8)
    g = [(o, gz(*at(s, o))) for o in range(-46, 70, 2)]
    ax3.plot([a for a, b in g], [Y(b) for a, b in g], color='#8a6a3a', lw=1)
    z = band(s)
    if k == 0:
        deckbar(-46, 45, Y(deck(C.interpolate(s).y)), '#eee'); deckbar(-27.25, 27.25, Y(z))
        [trk(o, Y(z), COL['tv']) for o in (-22.5, -18)]; [trk(o, Y(z), COL['apex']) for o in (-11.25, -6.75, -2.25, 2.25)]
        [trk(o, Y(z), COL['indy']) for o in (6.75, 11.25)]; [trk(o, Y(z), COL['orr']) for o in (18, 22.5)]
        zb = B(s); [trk(o, Y(zb), COL['bd']) for o in (18, 22.5)]
        ax3.text(29, Y(z), '%.1f' % z, fontsize=7); ax3.text(29, Y(zb), 'B/D %.1f under the deck (ORR E moves 11.25 m east before the tip)' % zb, fontsize=7, color=COL['bd'])
    if k == 1:
        zi, zd, zb = INDY(s), D(s), B(s)
        deckbar(-27.25, 6.75 - 2.25, Y(z)); [trk(o, Y(z), COL['tv']) for o in (-22.5, -18)]; [trk(o, Y(z), COL['apex']) for o in (-11.25, -6.75, -2.25, 2.25)]
        deckbar(2.0, 16.0, Y(zi)); [trk(o, Y(zi), COL['indy']) for o in (6.75, 11.25)]
        deckbar(13.25, 27.25, Y(zd)); [trk(o, Y(zd), COL['d']) for o in (18, 22.5)]
        deckbar(24.5, 48.5, Y(zb), '#cfe0ee'); [trk(o, Y(zb), COL['bd']) for o in (29.25, 43.75)]; ax3.add_patch(Rectangle((31.0, Y(zb) + 0.1), 11.0, 1.0, fc=COL['bd'], alpha=0.45))
        deckbar(45.75, 59.75, Y(z)); [trk(o, Y(z), COL['orr']) for o in (50.5, 55.0)]
        ax3.text(-46, Y(z) + 1, 'band %.1f' % z, fontsize=7); ax3.text(2, Y(zi) + 1.2, 'Indianapolis %.1f' % zi, fontsize=7, color=COL['indy'])
        ax3.text(14, Y(zd) - 3.3, 'D %.1f' % zd, fontsize=7, color=COL['d']); ax3.text(27, Y(zb) + 2.0, 'Arlington %.1f' % zb, fontsize=7, color=COL['bd'])
    if k == 2:
        zi, zd, zb = INDY(s), D(s), B(s); L = s - v.S_C0; dy = L * L / 1200
        deckbar(-27.25, 6.75 - 2.25, Y(z)); [trk(o, Y(z), COL['tv']) for o in (-22.5, -18)]; [trk(o, Y(z), COL['apex']) for o in (-11.25, -6.75, -2.25, 2.25)]
        deckbar(6.75 - dy - 4.75, 22.5 - dy + 4.75, Y(zi)); [trk(o - dy, Y(zi), COL['indy']) for o in (6.75, 11.25)]; [trk(o - dy, Y(zi), COL['d']) for o in (18, 22.5)]
        deckbar(13.25, 27.25, Y(zb)); [trk(o, Y(zb), COL['bd']) for o in (18, 22.5)]
        deckbar(24.5, 38.5, Y(z)); [trk(o, Y(z), COL['orr']) for o in (29.25, 33.75)]
        ax3.text(-46, Y(zi) + 1, 'Indianapolis %.1f and D %.1f on one deck, %.0f m into the 600 m curve' % (zi, zd, L), fontsize=7, color=COL['indy'])
        ax3.text(40, Y(z), 'band %.1f, B %.1f' % (z, zb), fontsize=7)
    if k == 3:
        zb = B(s)
        deckbar(-27.25, 29.5, Y(z)); [trk(o, Y(z), COL['tv']) for o in (-22.5, -18)]; [trk(o, Y(z), COL['apex']) for o in (-11.25, -6.75, -2.25, 2.25)]
        [trk(o, Y(zb), COL['bd']) for o in (9.0, 13.5)]; [trk(o, Y(z), COL['orr']) for o in (20.25, 24.75)]
        ax3.text(31, Y(z), 'all %.1f (B in the slot Indianapolis left)' % z, fontsize=7)
ax3.set_xlim(-47, 75); ax3.set_ylim(-3 * H - 2, H + 1); ax3.set_aspect('equal'); ax3.axis('off')
ax3.set_title('Cross sections looking north, true scale (m from the APEx line, + east). 4.5 m in a group, 6.75 m between groups, 4.75 m to the edge', fontsize=8, loc='left')
plt.savefig(SP + 'nv/North_Trunk_v4_long_section.png', dpi=105)
print('ok')
