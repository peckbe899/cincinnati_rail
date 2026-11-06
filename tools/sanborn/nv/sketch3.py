"""North trunk viaduct v3 sketch: plan, long section, cross sections at true elevation (corrected chainage)."""
try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, math, io, contextlib, importlib.util, numpy as np, rasterio, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.lines import Line2D
from shapely.geometry import LineString, Point, shape, box
SP = _ws.DATA
spec = importlib.util.spec_from_file_location('v3', _ws.CODE + 'nv/v3.py')
with contextlib.redirect_stdout(io.StringIO()):
    v3 = importlib.util.module_from_spec(spec); spec.loader.exec_module(v3)
C, band, tv, bd, r5, indy_at, d_at, gz, deck = v3.C, v3.band, v3.tv, v3.bd, v3.r5, v3.indy_at, v3.d_at, v3.gz, v3.deck
S_TIP, S_LUD = v3.S_TIP, v3.S_LUD
IP = LineString(v3.out['indy_path']); DP = LineString(v3.out['d_path'])
RA = json.load(open(SP + 'rera/rera.json'))
CTX = json.load(open(SP + 'deckpage/context.json')); ORRK = json.load(open(SP + 'nv/orr_near.json'))['lines']
COL = dict(tv='#3c8d5a', apex='#16252a', indy='#6b2fa0', orr='#b0207a', bd='#2a7ab0', d='#1d5f8f', r5='#e0218a', rera='#d07a1c')
# lateral layout (m from the APEx KMZ line, + east, looking north)
O = dict(tv_lobe=(-22.5, -18.0), tv=(-24.75, -20.25), tv_stn=(-34.75, -30.25), indy=(-11.25, -6.75), slot=(-13.5, -9.0),
         stn=(-23.5, -9.0), dn=(-2.25, 2.25, 6.75, 11.25), orr=(18.0, 22.5), r5=(29.25, 33.75))

def at(s, o):
    p = C.interpolate(s); q = C.interpolate(min(s + 3, C.length)); d = np.array([q.x - p.x, q.y - p.y]); d /= np.linalg.norm(d)
    return np.array([p.x, p.y]) + np.array([d[1], -d[0]]) * o
def strip(ax, s0, s1, f0, f1, **k):
    ss = np.linspace(s0, s1, max(2, int((s1 - s0) / 8)))
    o0 = [f0(s) if callable(f0) else f0 for s in ss]; o1 = [f1(s) if callable(f1) else f1 for s in ss]
    a = np.array([at(s, o) for s, o in zip(ss, o0)]); b = np.array([at(s, o) for s, o in zip(ss, o1)])
    ax.fill(np.r_[a[:, 0], b[::-1, 0]], np.r_[a[:, 1], b[::-1, 1]], **k)
def ease(s, s0, s1, a, b):
    if s <= s0: return a
    if s >= s1: return b
    t = (s - s0) / (s1 - s0); return a + (b - a) * (3 * t * t - 2 * t ** 3)
def tv_off(s):   # Transvalley centre: lobe -20.25, -22.5 north of the tip, -32.5 along the Arlington station
    if s < 4150: return ease(s, 3895, 4000, -20.25, -22.5)
    if s < 4600: return ease(s, 4150, 4290, -22.5, -32.5)
    return ease(s, 4510, 4660, -32.5, -22.5)

fig = plt.figure(figsize=(22, 15))
ax = fig.add_axes([0.01, 0.03, 0.40, 0.92]); ax2 = fig.add_axes([0.45, 0.60, 0.54, 0.36]); ax3 = fig.add_axes([0.45, 0.01, 0.54, 0.53])
x0, y0, x1, y1 = 711620, 4335300, 712960, 4337280
DEM = v3.DEM
win = rasterio.windows.from_bounds(x0, y0, x1, y1, DEM.transform); Z = DEM.read(1, window=win, out_shape=(int((y1 - y0) / 4), int((x1 - x0) / 4))).astype(float) / 10
ax.imshow(Z, extent=(x0, x1, y0, y1), cmap='Greys_r', vmin=140, vmax=200, alpha=0.30)
ax.contourf(np.linspace(x0, x1, Z.shape[1]), np.linspace(y1, y0, Z.shape[0]), Z, levels=[0, 147], colors=['#7aa6c9'], alpha=0.40)
BB = box(x0, y0, x1, y1)
for f in json.load(open(SP + 'deck/deck.json'))['features']:
    p = f['properties']; g = shape(f['geometry'])
    if not g.intersects(BB): continue
    if p['layer'] == 'deck':
        for q in getattr(g, 'geoms', [g]): ax.plot(*q.exterior.xy, 'k--', lw=0.7)
    if p['layer'] == 'street': ax.plot(*g.xy, color='#1f4f7a', lw=0.8, alpha=0.7)
for f in json.load(open(SP + 'deckpage/basin.json'))['features']:
    p = f['properties']; g = shape(f['geometry'])
    if p['layer'] == 'street' and g.intersects(BB): ax.plot(*g.xy, color='#999', lw=0.4 if p.get('kind') == 'we_alley' else 0.7)
for r in v3.out['streets']:
    if r['bd_result'] == 'CUT': ax.plot(*at(r['s'], -11.25), 'x', ms=9, mew=2, color='#c0392b')
strip(ax, 3500, 5650, lambda s: tv_off(s) - 4, lambda s: tv_off(s) + 4, fc=COL['tv'], alpha=0.6, lw=0)
strip(ax, 3500, 4040, -13.0, -5.0, fc=COL['indy'], alpha=0.6, lw=0)
strip(ax, 3500, 5650, -4.0, 13.0, fc=COL['apex'], alpha=0.6, lw=0)
strip(ax, 3500, 5650, 16.0, 24.5, fc=COL['orr'], alpha=0.6, lw=0)
strip(ax, S_TIP, 5650, lambda s: -14.5 if not (4260 < s < 4540) else -25.0, -8.0, fc=COL['bd'], alpha=0.55, lw=0)
st = np.array([at(s, -16.25) for s in np.linspace(*v3.S_STN, 20)]); ax.plot(st[:, 0], st[:, 1], color='white', lw=3, alpha=0.9, solid_capstyle='butt')
da = np.array(DP.coords); ax.plot(da[:, 0], da[:, 1], color=COL['d'], lw=3.2, alpha=0.85)
ia = np.array(IP.coords); ax.plot(ia[:, 0], ia[:, 1], color=COL['indy'], lw=4, alpha=0.75)
def r5path(s0=4790, Rr=250.0, h1=300.0, Lst=270, h2=14.0):
    p = at(s0, 31.5); q = at(s0 + 3, 31.5); d = (q - p) / np.linalg.norm(q - p); h = math.degrees(math.atan2(d[0], d[1])); pts = [p.copy()]
    def step(p, h, ds): r = math.radians(h); return p + ds * np.array([math.sin(r), math.cos(r)])
    while 0.5 < (h - h1) % 360 < 180: h -= math.degrees(2 / Rr); p = step(p, h, 2); pts.append(p.copy())
    for _ in range(int(Lst / 2)): p = step(p, h, 2); pts.append(p.copy())
    while 0.5 < (h2 - h) % 360 < 180: h += math.degrees(2 / Rr); p = step(p, h, 2); pts.append(p.copy())
    return np.array(pts)
r5p = np.r_[np.array([at(s, 31.5) for s in np.linspace(4300, 4788, 25)]), r5path()]
ax.plot(r5p[:, 0], r5p[:, 1], color=COL['r5'], lw=3, alpha=0.85)
ov = [C.project(Point(q)) for q in r5p if C.distance(Point(q)) < 29.5]; r5_over = (min(ov), max(ov))
sw = np.array([o for o in ORRK if 'Northside-Northgate' in o['name']][0]['pts']); ax.plot(sw[:, 0], sw[:, 1], color=COL['r5'], lw=1.5, ls=(0, (3, 2)), alpha=0.8)
cs = np.array([o for o in ORRK if 'Cumminsville Spur' in o['name']][0]['pts']); ax.plot(cs[:, 0], cs[:, 1], color=COL['r5'], lw=0.8, ls=(0, (1, 2)), alpha=0.7)
c = np.array(RA['lines']['A']); ax.plot(c[:, 0], c[:, 1], color=COL['rera'], lw=1.6, alpha=0.85)
for s in CTX['rer_stations']:
    if s['name'] in ('South Cumminsville', 'Northside', 'Northside / Spring Grove', 'Arlington'):
        isA = s['lines'] == ['A']
        ax.plot(*s['p'], 'o', ms=5, mfc='white' if s['name'] == 'Arlington' else (COL['rera'] if isA else COL['bd']), mec=COL['rera'] if isA else COL['bd'])
for g in [shape(f['geometry']) for f in json.load(open(SP + 'lph/osm_north.geojson'))['features'] if f['properties'].get('name') == 'Ludlow Avenue']:
    if g.intersects(BB) and g.geom_type == 'LineString': ax.plot(*g.xy, color='#b23a2e', lw=1.4)
def lab(p, t, d, c='k', fs=7.2):
    ax.annotate(t, p, p + np.array(d), fontsize=fs, color=c, arrowprops=dict(arrowstyle='-', lw=0.5, color=c))
lab(at(S_TIP, 27), 'deck tip, s 3,895: arch viaduct 166.6 m. Indianapolis climbs 1.3% from s 3,800;\nTransvalley drops 2%; B/D leaves the deck at 151.8 m and climbs 3.3% in the slot', (40, -60))
lab(at(4062, -11.25), 'Sassafras: cut by the B/D ramp (157.1 m over a 154.1 m street)', (-340, -40), '#c0392b')
lab(at(4110, -21), 'Indianapolis over Transvalley, s 4,081-4,130, 7.5 m', (-345, 10), COL['indy'])
lab(np.array([712256.9, 4335826.9]), 'KMZ Arlington point (s 4,146)', (160, -30), COL['bd'])
lab(at(4402, -16.25), 'Arlington (B), elevated at 163.0 m, s 4,300-4,504;\nentrances from Adelaide and Brashears; Transvalley\nmoved 10 m west along it', (190, -40), COL['bd'])
lab(at(4330, -30), 'D splits at s 4,242 (163.0 m), climbs on at 3.3%,\nover Transvalley s 4,361-4,400 (7.2 m), 300 m curve', (-330, 70), COL['d'])
lab(at(4560, 31.5), 'R5 leaves the ORR pair at s 4,300 (flat junction), 0.7% up to 167.0 m', (40, -55), COL['r5'])
lab(at(4900, 12), 'R5 over the band, s %d-%d, 7.3 m or more' % r5_over, (120, -45), COL['r5'])
lab(np.array([711810, 4336404]), 'D and Indianapolis over RER A at 174.3 m (7.3 m, as ruled)', (-190, -140), COL['indy'])
lab(at(S_LUD, 24), 'Ludlow, s 5,300: all at 155.5 m', (90, -10), '#b23a2e')
lab(np.array([712770.7, 4337001.7]), 'Northside/Spring Grove (B), surface', (30, 50), COL['bd'])
lab(r5p[-1], 'R5 joins SW-10 north of South Cumminsville\n(250 m curves, indicative)', (60, -40), COL['r5'])
ax.text(712040, 4336010, 'I-75 trench', fontsize=7, color='#2f5f86', rotation=50)
hl = [Line2D([], [], color=COL[k], lw=6, alpha=0.6) for k in ('tv', 'indy', 'apex', 'orr', 'bd')] + [Line2D([], [], color=COL['d'], lw=3), Line2D([], [], color=COL['r5'], lw=3), Line2D([], [], color=COL['rera'], lw=1.6), Line2D([], [], color='#c0392b', marker='x', lw=0, ms=8, mew=2)]
ax.legend(hl, ['Transvalley pair', 'APEx Indianapolis pair', 'APEx Dayton/Norwood (4)', 'ORR/intercity pair', 'TRI B/D, then B, in the slot Indianapolis leaves', 'TRI D', 'ORR R5 (Hamilton, SW-10)', 'RER A', 'street cut'], fontsize=7, loc='upper left')
ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect('equal'); ax.tick_params(labelsize=6); ax.grid(lw=0.2)
ax.set_title('North trunk v3: Indianapolis leaves from the west side, ORR stays on the east (no ORR-Indianapolis crossing)', fontsize=10.5, loc='left')

ss = np.arange(2400, 5700, 5)
ax2.plot(ss, [gz(*C.interpolate(s).coords[0]) for s in ss], color='#8a6a3a', lw=1, label='ground / deck surface (map 3)')
ax2.plot(ss, [band(s) for s in ss], color=COL['apex'], lw=2.2, label='APEx Dayton/Norwood + ORR: deck + 6.5 m, then 0.79% to Ludlow')
ax2.plot(ss, [tv(s) for s in ss], color=COL['tv'], lw=1.6, label='Transvalley: 2% from the tip to 159.8 m, rejoins at s 4,754')
si = ss[(ss >= 3600) & (ss <= 4350)]; ax2.plot(si, [indy_at(s - v3.S_I0) for s in si], color=COL['indy'], lw=1.8, label='Indianapolis: 1.3% from s 3,800 to 174.3 m')
ax2.plot(ss, [bd(s) for s in ss], color=COL['bd'], lw=1.8, label='TRI B/D: 3.3% from the tip; B 163.0 m at Arlington, 0.94% to Ludlow')
sd = ss[(ss >= v3.S_D) & (ss <= 4600)]; ax2.plot(sd, [d_at(s - v3.S_D) for s in sd], color=COL['d'], lw=1.6, ls='--', label='TRI D: 3.3% on from the split to 174.3 m')
sr = ss[(ss >= 4300) & (ss <= 4960)]; ax2.plot(sr, [r5(s) for s in sr], color=COL['r5'], lw=1.8, label='ORR R5: 0.7%% to 167.0 m, over the band s %d-%d' % r5_over)
for r in v3.out['streets']:
    ax2.plot(r['s'], r['ground'], 'v', ms=3.5, color='#c0392b' if r['bd_result'] == 'CUT' else '#1f4f7a')
    ax2.text(r['s'], r['ground'] - 1.0, r['street'].split()[0], rotation=90, fontsize=5.5, ha='center', va='top', color='#1f4f7a')
ax2.axvspan(*v3.S_STN, color=COL['bd'], alpha=0.12)
for s, t in ((2541, 'Marshall'), (3181, 'Hopple'), (S_TIP, 'deck tip'), (4105, 'Indy over Transvalley'), (v3.S_D, 'D splits'), (4402, 'Arlington (B)'), (r5_over[0], 'R5 over'), (S_LUD, 'Ludlow'), (5368, '1922 Ludlow bridge')):
    ax2.axvline(s, color='#999', lw=0.5); ax2.text(s, 177.3, t, rotation=90, fontsize=6.5, va='top', ha='right')
ax2.set_ylim(140, 178); ax2.set_xlim(2400, 5700); ax2.legend(fontsize=6.3, loc='lower left', ncol=2); ax2.grid(lw=0.2); ax2.tick_params(labelsize=7)
ax2.set_xlabel('m along the APEx line from CUT (corrected chainage)', fontsize=7); ax2.set_title('Long section (levels in m)', fontsize=9, loc='left')

def trk(o, z, c, lw=3): ax3.plot([o - 0.75, o + 0.75], [z, z], color=c, lw=lw, solid_capstyle='butt')
def deckbar(o0, o1, z, c='#ccc'): ax3.add_patch(Rectangle((o0, z - 1.4), o1 - o0, 1.2, fc=c, ec='k', lw=0.5))
H = 37
specs = [(3500, 'A  s 3,500, lobe: 10 tracks, 45.0 m between outer tracks, deck 54.5 m (as built); B/D under the deck'),
         (4100, 'B  s 4,100 (Arlington St): Indianapolis crossing over Transvalley; B/D ramp in the slot'),
         (4420, 'C  s 4,420 (Arlington station): 8 tracks + B island, 57.25 m, about 67 m wide; R5 on its own deck'),
         (5150, 'D  s 5,150 (Ford-Ludlow): 10 tracks, 47.25 m, 56.75 m; to grade at Ludlow')]
for k, (s, title) in enumerate(specs):
    yb = -k * H; Y = lambda z, yb=yb: yb + (z - 140)
    ax3.text(-46, yb + 34, title, fontsize=8)
    gnd = [(o, gz(*at(s, o))) for o in range(-46, 56, 2)]
    ax3.plot([g[0] for g in gnd], [Y(g[1]) for g in gnd], color='#8a6a3a', lw=1)
    z = band(s)
    if k == 0:
        deckbar(-46, 55, Y(deck(C.interpolate(s).y)), '#eee'); deckbar(-27.25, 27.25, Y(z))
        for o in O['tv_lobe']: trk(o, Y(z), COL['tv'])
        for o in O['indy']: trk(o, Y(z), COL['indy'])
        for o in O['dn']: trk(o, Y(z), COL['apex'])
        for o in O['orr']: trk(o, Y(z), COL['orr'])
        for o in (-2.25, 2.25): trk(o, Y(151.8), COL['bd'])
        ax3.text(29, Y(z), '%.1f' % z, fontsize=6.5); ax3.text(29, Y(151.8), 'B/D 151.8 under the deck', fontsize=6.5, color=COL['bd'])
    if k == 1:
        zt, zi, zb = tv(s), indy_at(s - v3.S_I0), bd(s)
        deckbar(-29.5, -15.5, Y(zt)); [trk(o, Y(zt), COL['tv']) for o in O['tv']]
        deckbar(-30.0, -13.5, Y(zi)); [trk(o, Y(zi), COL['indy']) for o in (-24.0, -19.5)]
        deckbar(-7.0, 27.25, Y(z)); [trk(o, Y(z), COL['apex']) for o in O['dn']]; [trk(o, Y(z), COL['orr']) for o in O['orr']]
        ax3.plot([-16.5, -16.5, -6.0, -6.0], [Y(zb) + 5, Y(zb) - 0.8, Y(zb) - 0.8, Y(zb) + 5], color=COL['bd'], lw=0.8); [trk(o, Y(zb), COL['bd']) for o in O['slot']]
        ax3.text(29, Y(z), 'APEx/ORR %.1f' % z, fontsize=6.5); ax3.text(-46, Y(zi) + 0.5, 'Indianapolis %.1f' % zi, fontsize=6.5, color=COL['indy'])
        ax3.text(-46, Y(zt) - 2.5, 'Transvalley %.1f' % zt, fontsize=6.5, color=COL['tv']); ax3.text(-5, Y(zb) - 3.8, 'B/D ramp %.1f' % zb, fontsize=6.5, color=COL['bd'])
    if k == 2:
        zt, zb, zr = tv(s), bd(s), r5(s)
        deckbar(-39.5, -25.5, Y(zt)); [trk(o, Y(zt), COL['tv']) for o in O['tv_stn']]
        deckbar(-28.25, -4.25, Y(zb), '#cfe0ee'); [trk(o, Y(zb), COL['bd']) for o in O['stn']]
        ax3.add_patch(Rectangle((-21.75, Y(zb) + 0.1), 11.0, 1.0, fc=COL['bd'], alpha=0.45))
        deckbar(-7.0, 27.25, Y(z)); [trk(o, Y(z), COL['apex']) for o in O['dn']]; [trk(o, Y(z), COL['orr']) for o in O['orr']]
        deckbar(24.5, 38.5, Y(zr)); [trk(o, Y(zr), COL['r5']) for o in O['r5']]
        ax3.text(-46, Y(zt) - 3.0, 'Transvalley %.1f' % zt, fontsize=6.5, color=COL['tv']); ax3.text(-24, Y(zb) + 2.2, 'Arlington (B) %.1f, island 11 m' % zb, fontsize=6.5, color=COL['bd'])
        ax3.text(29, Y(z) - 3.2, 'APEx/ORR %.1f' % z, fontsize=6.5); ax3.text(40, Y(zr) + 0.5, 'R5 %.1f' % zr, fontsize=6.5, color=COL['r5'])
        ax3.text(-46, Y(172), 'D is already west of Transvalley here, about 170 m', fontsize=6.5, color=COL['d'])
    if k == 3:
        zb = bd(s)
        deckbar(-29.5, 27.25, Y(z))
        for o in O['tv']: trk(o, Y(z), COL['tv'])
        for o in O['slot']: trk(o, Y(zb), COL['bd'])
        for o in O['dn']: trk(o, Y(z), COL['apex'])
        for o in O['orr']: trk(o, Y(z), COL['orr'])
        ax3.text(29, Y(z), 'Transvalley/APEx/ORR %.1f, B %.1f' % (z, zb), fontsize=6.5)
        ax3.text(-46, Y(146) - 2.5, 'I-75 trench edge about 26 m west: the band moves 5-7 m east from Ford', fontsize=6.5, color='#2f5f86')
ax3.set_xlim(-47, 62); ax3.set_ylim(-3 * H - 4, H + 0.5); ax3.set_aspect('equal'); ax3.axis('off')
ax3.set_title('Cross sections looking north, true scale (m from the APEx line, + east). Working spacing: 4.5 m in a group, 6.75 m between groups, 4.75 m to the edge', fontsize=8, loc='left')
plt.savefig(SP + 'nv/North_Trunk_Viaduct_sketch_v3.png', dpi=105)
print('R5 over the band, s %.0f-%.0f' % r5_over)
