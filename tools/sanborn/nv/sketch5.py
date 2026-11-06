"""North trunk v5: long section and cross sections (all paths on one viaduct; Camp Washington elevated; B/D dive to Straight)."""
try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, io, math, contextlib, importlib.util, numpy as np, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
SP = _ws.DATA
spec = importlib.util.spec_from_file_location('v5', _ws.CODE + 'nv/v5.py')
with contextlib.redirect_stdout(io.StringIO()):
    v = importlib.util.module_from_spec(spec); spec.loader.exec_module(v)
C, band, BDs, B, SH, gz, deck, at = v.C, v.band, v.BDs, v.B, v.SH, v.gz, v.deck, v.at
COL = dict(tv='#3c8d5a', apex='#16252a', indy='#6b2fa0', orr='#b0207a', bd='#2a7ab0', d='#1d5f8f')
fig = plt.figure(figsize=(20, 15))
ax = fig.add_axes([0.05, 0.56, 0.93, 0.41]); ax3 = fig.add_axes([0.01, 0.01, 0.98, 0.50])
ss = np.arange(2150, 5400, 5)
ax.plot(ss, [gz(*C.interpolate(s).coords[0]) for s in ss], color='#8a6a3a', lw=1, label='ground / deck surface (map 3)')
ax.plot(ss, [band(s) for s in ss], color=COL['apex'], lw=2.4, label='the viaduct (APEx, ORR E, Transvalley/R5, and B/D from Camp Washington north): deck + 6.5 m, then %.2f%% to Ludlow' % (100 * v.G_BAND))
sb = ss[ss <= v.S_CW1]
ax.plot(sb, [BDs(s) for s in sb], color=COL['bd'], lw=2.2, label='TRI B/D: Camp Washington on the viaduct, 3.3%% down from s %.0f to %.2f m at s %.0f, level into Straight' % (v.S_CW0, v.Z_STR, v.S_BOT))
sn = ss[(ss >= v.S_TIP - 100) & (ss <= v.S_OUT + 50)]
ax.plot(sn, [B(s) for s in sn], color=COL['bd'], lw=2.2, ls=(0, (4, 1.5)), label='TRI B: off the band through Arlington (level %.1f m), back on it at s %.0f' % (v.Z_AR, v.S_OUT))
si = ss[(ss >= v.S_A) & (ss <= v.s_clear)]
ax.plot(si, [SH(s) for s in si], color=COL['indy'], lw=3.2, alpha=0.65, label='APEx Indianapolis + TRI D, one deck: leave the band at s %.0f, %.1f%% to 174.3 m by s %.0f, west on the KMZ curve from s %.0f' % (v.S_A, 100 * v.G_SH, v.s_top, v.S_C))
for (a, b), z, t in (((2199, 2403), v.Z_STR, 'Straight (B, D), bored from here'), ((v.S_CW0, v.S_CW1), band(3066), 'Camp Washington (B, D)'), ((v.S_AR0, v.S_AR1), v.Z_AR, 'Arlington (B)')):
    ax.add_patch(Rectangle((a, z - 1.1), b - a, 1.1, color=COL['bd'], alpha=0.5)); ax.text((a + b) / 2, z + 0.6, t, fontsize=7, ha='center', color=COL['bd'])
ax.axvspan(v.s_box, v.s_deck, color=COL['bd'], alpha=0.10); ax.text((v.s_box + v.s_deck) / 2, 146.5, 'open trough', fontsize=7, ha='center', color=COL['bd'])
ax.axvspan(v.s_deck, v.S_CW0, color=COL['bd'], alpha=0.05); ax.text((v.s_deck + v.S_CW0) / 2, 146.5, 'ramp above the deck', fontsize=7, ha='center', color=COL['bd'])
ax.text((2403 + v.s_box) / 2, 146.5, 'box (dug)', fontsize=7, ha='center', color=COL['bd'])
ax.axvspan(v.S_CW1, v.S_A, color=COL['d'], alpha=0.06); ax.text((v.S_CW1 + v.S_A) / 2, 172.0, 'D leaves B (flyover: northbound D over B)', fontsize=7, ha='center', color=COL['d'])
for r in v.out['dive_streets']:
    if 's0' not in r: continue
    sm = (r['s0'] + r['s1']) / 2; c = '#c0392b' if 'ENDS' in r['result'] else ('#b9770e' if ('lower' in r['result'] or 'raise' in r['result']) else '#1f4f7a')
    dx = {'Willow Lane (carried west)': 12, 'Rawson (carried south)': -6}.get(r['street'], 0)
    ax.plot(sm, r['z'], 'v', ms=4, color=c); ax.text(sm + dx, r['z'] - 0.8, r['street'].split(' (')[0], rotation=90, fontsize=6, ha='center', va='top', color=c)
for r in v.out['north_streets']:
    if r['street'].startswith('Johnson'): continue
    ax.plot(r['s'], r['z'], 'v', ms=4, color='#1f4f7a'); ax.text(r['s'], r['z'] - 0.8, r['street'], rotation=90, fontsize=6, ha='center', va='top', color='#1f4f7a')
for s, t in ((v.S_TIP, 'deck tip'), (4146, 'KMZ Arlington'), (v.S_C, 'KMZ curve starts'), (v.s_clear, 'Indianapolis + D clear of Transvalley/R5'), (5300, 'Ludlow')):
    ax.axvline(s, color='#999', lw=0.5); ax.text(s, 177.5, t, rotation=90, fontsize=7, va='top', ha='right')
ax.set_xlim(2150, 5400); ax.set_ylim(140, 178); ax.grid(lw=0.2); ax.tick_params(labelsize=7); ax.legend(fontsize=7, loc='lower right')
ax.set_xlabel('m along the APEx line from CUT', fontsize=7)
ax.set_title('North trunk v5 (10za.32): every path on one viaduct from Ludlow to Camp Washington; B/D dive to Straight (levels in m). Red: street ends at the dive; amber: re-graded', fontsize=10, loc='left')
def trk(o, z, c): PP([o - 0.75, o + 0.75], [z, z], color=c, lw=3, solid_capstyle='butt')
def deckbar(o0, o1, z, c='#ccc'): RR(Rectangle((o0, z - 1.4), o1 - o0, 1.2, fc=c, ec='k', lw=0.5))
APEX6 = (-11.25, -6.75, -2.25, 2.25, 6.75, 11.25)
panels = [(2680, 'A  s 2,680, open trough: B/D below the deck, curving back under the APEx tracks; ORR E swinging back over it'),
          (2850, 'B  s 2,850, the ramp: B/D 3.3% down between the APEx and ORR E decks (Meeker ends here)'),
          (3066, 'C  s 3,066, Camp Washington (B, D) on the viaduct: 12 tracks and the island, 66.25 m, deck 75.75 m'),
          (3800, 'D  s 3,800: Indianapolis + southbound D climbing west of B, northbound D east of it (over B by s 3,924, the flyover); deck 77.0 m'),
          (4146, 'E  s 4,146, Arlington (B) on the band; Indianapolis + D overhead at 174.3 m, swinging west')]
H = 38; XW = 150
for k, (s, title) in enumerate(panels):
    xb = (k % 2) * XW; yb = -(k // 2) * H; Y = lambda z, yb=yb: yb + (z - 142)
    _p, _t, _r = ax3.plot, ax3.text, ax3.add_patch
    def P(xs, ys, *a, xb=xb, **kw): return _p([x + xb for x in xs], ys, *a, **kw)
    def T(x, y, *a, xb=xb, **kw): return _t(x + xb, y, *a, **kw)
    def R(rect, xb=xb): rect.set_x(rect.get_x() + xb); return _r(rect)
    globals().update(PP=P, TT=T, RR=R)
    T(-50, yb + 34, title, fontsize=7.5)
    g = [(o, gz(*at(s, o))) for o in range(-50, 72, 2)]
    P([a for a, b in g], [Y(b) for a, b in g], color='#8a6a3a', lw=1)
    z = band(s)
    if k in (0, 1):
        oc = v.o_c(s); fr = (s - 2541) / (2964 - 2541); oo = 18 + 21.25 * (1 - math.cos(math.pi * fr)) / 2
        zb = BDs(s)
        deckbar(-27.25, 16.0, Y(z)); [trk(o, Y(z), COL['tv']) for o in (-22.5, -18)]; [trk(o, Y(z), COL['apex']) for o in APEX6]
        deckbar(oo - 4.75, oo + 4.5 + 4.75, Y(z)); [trk(o, Y(z), COL['orr']) for o in (oo, oo + 4.5)]
        [trk(o, Y(zb), COL['bd']) for o in (oc - 2.25, oc + 2.25)]
        zd = deck(C.interpolate(s).y)
        if zb < zd:
            for w in (oc - 5.75, oc + 5.75): PP([w, w], [Y(zb - 1.0), Y(zd)], color='k', lw=1)
            PP([oc - 5.75, oc + 5.75], [Y(zb - 1.0)] * 2, color='k', lw=1)
        else:
            deckbar(oc - 5.75, oc + 5.75, Y(zb), '#cfe0ee')
        TT(50, Y(z), 'band %.1f' % z, fontsize=7); TT(50, Y(zb), 'B/D %.1f (deck %.1f)' % (zb, zd), fontsize=7, color=COL['bd'])
    if k == 2:
        deckbar(-27.25, 48.5, Y(z)); [trk(o, Y(z), COL['tv']) for o in (-22.5, -18)]; [trk(o, Y(z), COL['apex']) for o in APEX6]
        [trk(o, Y(z), COL['bd']) for o in (18, 32.5)]; RR(Rectangle((19.75, Y(z) + 0.1), 11.0, 1.0, fc=COL['bd'], alpha=0.45))
        [trk(o, Y(z), COL['orr']) for o in (39.25, 43.75)]
        TT(50, Y(z), 'all %.1f; Hopple and Johnson pass under at 6.5 m' % z, fontsize=7)
    if k == 3:
        zi = SH(s)
        deckbar(-27.25, 4.5, Y(z)); [trk(o, Y(z), COL['tv']) for o in (-22.5, -18)]; [trk(o, Y(z), COL['apex']) for o in APEX6[:4]]
        deckbar(2.0, 20.5, Y(zi), '#e6dcef'); [trk(o, Y(zi), COL['indy']) for o in (6.75, 11.25)]; trk(15.75, Y(zi), COL['d'])
        deckbar(17.75, 31.75, Y(z)); [trk(o, Y(z), COL['bd']) for o in (22.5, 27.0)]
        deckbar(29.0, 38.5, Y(zi), '#e6dcef'); trk(33.75, Y(zi), COL['d'])
        deckbar(35.75, 49.75, Y(z)); [trk(o, Y(z), COL['orr']) for o in (40.5, 45.0)]
        TT(52, Y(z), 'band %.1f (B, ORR E)' % z, fontsize=7); TT(52, Y(zi), 'Indianapolis + D %.1f' % zi, fontsize=7, color=COL['indy'])
    if k == 4:
        zi = SH(s); y = (s - v.S_C) ** 2 / (2 * v.R_C)
        deckbar(-27.25, 16.0, Y(z)); [trk(o, Y(z), COL['tv']) for o in (-22.5, -18)]; [trk(o, Y(z), COL['apex']) for o in APEX6[:4]]
        deckbar(6.75 - y - 4.75, 20.25 - y + 4.75, Y(zi), '#e6dcef'); [trk(o - y, Y(zi), COL['indy']) for o in (6.75, 11.25)]; [trk(o - y, Y(zi), COL['d']) for o in (15.75, 20.25)]
        deckbar(13.25, 48.5, Y(v.Z_AR)); [trk(o, Y(v.Z_AR), COL['bd']) for o in (18, 32.5)]; RR(Rectangle((19.75, Y(v.Z_AR) + 0.1), 11.0, 1.0, fc=COL['bd'], alpha=0.45))
        [trk(o, Y(z), COL['orr']) for o in (39.25, 43.75)]
        TT(50, Y(z), 'band %.1f, Arlington %.1f' % (z, v.Z_AR), fontsize=7); TT(50, Y(zi), 'Indianapolis + D %.1f, %.0f m west of their lobe slot' % (zi, y), fontsize=7, color=COL['indy'])
ax3.set_xlim(-51, XW + 100); ax3.set_ylim(-2 * H - 4, H + 1); ax3.set_aspect('equal'); ax3.axis('off')
ax3.set_title('Cross sections looking north, true scale (m from the APEx line, + east). Transvalley/R5 green, APEx black, Indianapolis purple, TRI blue, ORR E magenta. 4.5 m in a group, 6.75 m between groups, 4.75 m to the edge', fontsize=8, loc='left')
plt.savefig(SP + 'nv/North_Trunk_v5_long_section.png', dpi=105)
print('ok')
