"""North trunk viaduct v3 sketch: plan, long section, cross sections at true elevation."""
try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, math, numpy as np, rasterio, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon
from shapely.geometry import LineString, Point, shape, box
from shapely.ops import substring
import importlib.util, sys
SP = _ws.DATA
spec = importlib.util.spec_from_file_location('v3', _ws.CODE + 'nv/v3.py')
import io, contextlib
with contextlib.redirect_stdout(io.StringIO()):
    v3 = importlib.util.module_from_spec(spec); spec.loader.exec_module(v3)
C, band, tv, bd, r5, indy_at, gz, deck = v3.C, v3.band, v3.tv, v3.bd, v3.r5, v3.indy_at, v3.gz, v3.deck
S_TIP, S_LUD = v3.S_TIP, v3.S_LUD
IP = LineString(v3.out['indy_path'])
L = json.load(open(SP + 'nv/lines.json')); RA = json.load(open(SP + 'rera/rera.json'))
CTX = json.load(open(SP + 'deckpage/context.json'))
ORRK = json.load(open(SP + 'nv/orr_near.json'))['lines']
COL = dict(tv='#3c8d5a', apex='#16252a', indy='#6b2fa0', orr='#b0207a', bd='#2a7ab0', r5='#e0218a', rera='#d07a1c')

def at(s, o):
    p = C.interpolate(s); q = C.interpolate(min(s + 3, C.length)); d = np.array([q.x - p.x, q.y - p.y]); d /= np.linalg.norm(d)
    return np.array([p.x, p.y]) + np.array([d[1], -d[0]]) * o          # o > 0 east (right looking north)
def strip(ax, s0, s1, o0, o1, **k):
    ss = np.linspace(s0, s1, max(2, int((s1 - s0) / 10)))
    a = np.array([at(s, o0) for s in ss]); b = np.array([at(s, o1) for s in ss])
    ax.fill(np.r_[a[:, 0], b[::-1, 0]], np.r_[a[:, 1], b[::-1, 1]], **k)
def offline(ax, s0, s1, ofun, **k):
    ss = np.linspace(s0, s1, max(2, int((s1 - s0) / 10)))
    a = np.array([at(s, ofun(s)) for s in ss]); ax.plot(a[:, 0], a[:, 1], **k); return a

fig = plt.figure(figsize=(22, 15))
ax = fig.add_axes([0.01, 0.04, 0.40, 0.92]); ax2 = fig.add_axes([0.45, 0.58, 0.54, 0.38]); ax3 = fig.add_axes([0.45, 0.02, 0.54, 0.50])
x0, y0, x1, y1 = 711640, 4335150, 712960, 4337200
DEM = v3.DEM
win = rasterio.windows.from_bounds(x0, y0, x1, y1, DEM.transform); Z = DEM.read(1, window=win, out_shape=(int((y1 - y0) / 5), int((x1 - x0) / 5))).astype(float) / 10
ax.imshow(Z, extent=(x0, x1, y0, y1), cmap='Greys_r', vmin=140, vmax=200, alpha=0.30)
ax.contourf(np.linspace(x0, x1, Z.shape[1]), np.linspace(y1, y0, Z.shape[0]), Z, levels=[0, 147], colors=['#7aa6c9'], alpha=0.45)
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
# groups (offsets from the APEx KMZ line, + east)
SM = v3.out and 2502
strip(ax, SM, S_TIP, -27.25, 27.25, fc='#16252a', alpha=0.10, ec='#16252a', lw=0.5)
strip(ax, SM, 5600, -24.75, -15.75, fc=COL['tv'], alpha=0.55, lw=0)                      # Transvalley
strip(ax, SM, 4135, -13.5, -4.5, fc=COL['indy'], alpha=0.55, lw=0)                       # Indianapolis on the arch viaduct
strip(ax, SM, 5600, -4.5, 13.5, fc=COL['apex'], alpha=0.55, lw=0)                        # Dayton/Norwood
strip(ax, SM, 5600, 15.75, 24.75, fc=COL['orr'], alpha=0.55, lw=0)                       # ORR
strip(ax, 4943, 5600, -13.5, -4.5, fc=COL['bd'], alpha=0.55, lw=0)                       # B up in the old Indianapolis slot
# B/D box: centreline to the station, then drifting into the slot
def bdo(s):
    if s < 4300: return 0.0
    if s < 4700: return -9.0 * (s - 4300) / 400
    return -9.0
offline(ax, 3000, 4943, bdo, color=COL['bd'], lw=2.2, ls=(0, (4, 2)))
st = np.array([at(s, 0) for s in np.linspace(*v3.S_STN, 20)])
ax.plot(st[:, 0], st[:, 1], color=COL['bd'], lw=9, alpha=0.35, solid_capstyle='butt')
# D westward underground along the TRIMET Greensburg line
dk = [o for o in L if o['src'] == 'TRIMET3D' and o['name'] == 'Greensburg-California 3D'][0]
D3 = np.array(dk['c']); pD = C.interpolate(v3.S_D); kd = int(np.argmin(np.hypot(D3[:, 0] - pD.x, D3[:, 1] - pD.y)))
kt = int(np.argmin(np.hypot(D3[:, 0] - 711300, D3[:, 1] - 4336650)))
dseg = D3[min(kd, kt):max(kd, kt) + 1]; ax.plot(dseg[:, 0], dseg[:, 1], color=COL['bd'], lw=1.8, ls=(0, (4, 2)))
# Indianapolis
ia = np.array(IP.coords); ia = ia[(ia[:, 0] > x0) & (ia[:, 1] < y1)]
ax.plot(ia[:, 0], ia[:, 1], color=COL['indy'], lw=4, alpha=0.75)
# R5: east of ORR from s 4300, over the band from s 4800, west to South Cumminsville, then north on SW-10
def r5path(s0=4790, Rr=250.0, h1=300.0, Lst=270, h2=14.0):
    p = at(s0, 31.5); q = at(s0 + 3, 31.5); d = (q - p) / np.linalg.norm(q - p); h = math.degrees(math.atan2(d[0], d[1])); pts = [p.copy()]
    def step(p, h, ds): r = math.radians(h); return p + ds * np.array([math.sin(r), math.cos(r)])
    while 0.5 < (h - h1) % 360 < 180: h -= math.degrees(2 / Rr); p = step(p, h, 2); pts.append(p.copy())
    for _ in range(int(Lst / 2)): p = step(p, h, 2); pts.append(p.copy())
    while 0.5 < (h2 - h) % 360 < 180: h += math.degrees(2 / Rr); p = step(p, h, 2); pts.append(p.copy())
    return np.array(pts)
SC = np.array([711893.5, 4336646.6])
r5p = np.r_[np.array([at(s, 31.5) for s in np.linspace(4300, 4788, 25)]), r5path()]
ax.plot(r5p[:, 0], r5p[:, 1], color=COL['r5'], lw=3, alpha=0.8)
sw = [o for o in ORRK if 'Northside-Northgate' in o['name']][0]; swc = np.array(sw['pts'])
ax.plot(swc[:, 0], swc[:, 1], color=COL['r5'], lw=1.5, ls=(0, (3, 2)), alpha=0.8)
R5L = LineString(r5p)
# where R5 is over the band
ov = [C.project(Point(q)) for q in r5p if C.distance(Point(q)) < 27.25]
r5_over = (min(ov), max(ov)) if ov else (None, None)
# RER A
for k in ('A',):
    c = np.array(RA['lines'][k]); ax.plot(c[:, 0], c[:, 1], color=COL['rera'], lw=1.6, alpha=0.85)
for s in CTX['rer_stations']:
    if s['name'] in ('South Cumminsville', 'Northside', 'Northside / Spring Grove', 'Hopple'):
        ax.plot(*s['p'], 'o', ms=5, color=COL['rera'] if s['lines'] == ['A'] else COL['bd'])
def lab(p, t, d, c='k', fs=7.2):
    ax.annotate(t, p, p + np.array(d), fontsize=fs, color=c, arrowprops=dict(arrowstyle='-', lw=0.5, color=c))
lab(at(S_TIP, 27), 'deck tip 166.6 m: Indianapolis climbing 1.3%,\nTransvalley dropping 2%, B/D under the deck', (100, -40))
lab(at(4146, 0), 'Arlington (B, D): box station at the KMZ point,\n145.8 m, under the viaduct', (150, -95), COL['bd'])
lab(at(4100, -20), 'Indianapolis over Transvalley\n(7.5 m), s 4,081-4,130', (-330, -60), COL['indy'])
lab(at(v3.S_D, -5), 'D leaves the box west\n(underground, under RER A)', (-330, 10), COL['bd'])
lab(at(4500, 31.5), 'R5 leaves ORR (east), 0.6% up', (90, -20), COL['r5'])
lab(at(4890, 0), 'R5 over the band, s 4,836-4,948\n(166.4 m, 7.3 m or more)', (120, -70), COL['r5'])
lab(at(4943, -9), 'Ford: B comes up in the old\nIndianapolis slot, 2.3%', (-330, 40), COL['bd'])
lab(at(S_LUD, 24), 'Ludlow: all at 155.5 m', (100, -10), '#b23a2e')
lab(np.array([712770.7, 4337001.7]), 'Northside/Spring Grove (B): surface', (40, 40), COL['bd'])
lab(r5p[-1], 'R5 joins SW-10 (250 m curves, indicative);\nRER A passes over it', (-20, 60), COL['r5'])
lab(np.array([711815, 4336410]), 'Indianapolis over RER A (7.3 m)', (-180, -110), COL['indy'])
ax.text(711640, 4335200, 'I-75 trench\n(< 147 m)', fontsize=7, color='#2f5f86')
for g in [shape(f['geometry']) for f in json.load(open(SP + 'lph/osm_north.geojson'))['features'] if f['properties'].get('name') == 'Ludlow Avenue']:
    if g.intersects(BB) and g.geom_type == 'LineString': ax.plot(*g.xy, color='#b23a2e', lw=1.4)
from matplotlib.lines import Line2D
hl = [Line2D([], [], color=COL[k], lw=6, alpha=0.6) for k in ('tv', 'indy', 'apex', 'orr')] + [Line2D([], [], color=COL['bd'], lw=2, ls='--'), Line2D([], [], color=COL['r5'], lw=3), Line2D([], [], color=COL['rera'], lw=1.6)]
ax.legend(hl, ['Transvalley pair', 'APEx Indianapolis pair', 'APEx Dayton/Norwood (4)', 'ORR/intercity pair', 'TRI B/D box (D west underground)', 'ORR R5 (Hamilton)', 'RER A'], fontsize=7, loc='upper left')
ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect('equal'); ax.tick_params(labelsize=6); ax.grid(lw=0.2)
ax.set_title('North trunk v3: Indianapolis leaves from the west side, ORR stays east (no ORR-Indianapolis crossing)', fontsize=10.5, loc='left')

# long section
ss = np.arange(2400, 5700, 5)
ax2.plot(ss, [gz(*C.interpolate(s).coords[0]) for s in ss], color='#8a6a3a', lw=1, label='ground / deck surface')
ax2.plot(ss, [band(s) for s in ss], color=COL['apex'], lw=2.2, label='APEx Dayton/Norwood + ORR: deck + 6.5 m, then 0.79% to Ludlow')
ax2.plot(ss, [tv(s) for s in ss], color=COL['tv'], lw=1.6, label='Transvalley: 2% from the tip, 159.8 m, rejoins at s 4,754')
si = ss[(ss >= 3600) & (ss <= 4300)]
ax2.plot(si, [indy_at(s - v3.S_I0) for s in si], color=COL['indy'], lw=1.8, label='Indianapolis: 1.3% from s 3,800 to 174.3 m (plotted on trunk chainage)')
ax2.plot(ss, [bd(s) for s in ss], color=COL['bd'], lw=1.8, ls='--', label='TRI B/D box (B to the surface at Ludlow, 2.3%)')
sr = ss[(ss >= 4300) & (ss <= 4950)]
ax2.plot(sr, [r5(s) for s in sr], color=COL['r5'], lw=1.8, label='ORR R5: 0.6% up to 166.4 m, over the band from s 4,800')
for r in v3.out['streets']:
    ax2.plot(r['s'], r['ground'], 'v', ms=3, color='#1f4f7a'); ax2.text(r['s'], r['ground'] - 1.0, r['street'].split()[0], rotation=90, fontsize=5.5, ha='center', va='top', color='#1f4f7a')
ax2.axvspan(*v3.S_STN, color=COL['bd'], alpha=0.12)
for s, t in ((2541, 'Marshall'), (3181, 'Hopple'), (S_TIP, 'deck tip'), (4146, 'Arlington (box)'), (4105, 'Indy over Transvalley'), (v3.S_D, 'D leaves'), (4800, 'R5 over'), (4943, 'Ford: B trough'), (S_LUD, 'Ludlow'), (5368, '1922 Ludlow bridge')):
    ax2.axvline(s, color='#999', lw=0.5); ax2.text(s, 177.3, t, rotation=90, fontsize=6.5, va='top', ha='right')
ax2.set_ylim(138, 178); ax2.set_xlim(2400, 5700); ax2.legend(fontsize=6.3, loc='lower left', ncol=2); ax2.grid(lw=0.2); ax2.tick_params(labelsize=7)
ax2.set_xlabel('m along the APEx line from CUT (corrected chainage)', fontsize=7); ax2.set_title('Long section (levels in m)', fontsize=9, loc='left')

# cross sections at true elevation (offset east +, looking north)
def trk(axx, o, z, c, lw=3): axx.plot([o - 0.75, o + 0.75], [z, z], color=c, lw=lw, solid_capstyle='butt')
def deckbar(axx, o0, o1, z, c='#ccc'): axx.add_patch(Rectangle((o0, z - 1.4), o1 - o0, 1.2, fc=c, ec='k', lw=0.5))
panels = [(0.0, 'A  Lobe, s 3,500 (Stock-Ethan): 10 tracks, 45.0 m, deck 54.5 m (as built)'),
          (1.0, 'B  s 4,100 (Arlington): Indianapolis over Transvalley; box station below'),
          (2.0, 'C  s 4,600 (Earl-Whiteley): 8 on the viaduct, slot open, R5 on its own deck'),
          (3.0, 'D  s 5,150 (Ford-Ludlow): B up in the slot; 10 tracks, 47.25 m, 56.75 m')]
H = 36
for k, (row, title) in enumerate(panels):
    yb = -row * H; ax3.text(-46, yb + 31, title, fontsize=8)
    def Y(z): return yb + (z - 140) * 1.0
    s = (3500, 4100, 4600, 5150)[k]
    gnd = [(o, gz(*at(s, o))) for o in range(-45, 56, 2)]
    ax3.plot([g[0] for g in gnd], [Y(g[1]) for g in gnd], color='#8a6a3a', lw=1)
    if k == 0:
        deckbar(ax3, -45, 55, Y(deck(C.interpolate(s).y)), '#eee'); z = band(s)
        deckbar(ax3, -27.25, 27.25, Y(z))
        for o in (-22.5, -18): trk(ax3, o, Y(z), COL['tv'])
        for o in (-11.25, -6.75): trk(ax3, o, Y(z), COL['indy'])
        for o in (-2.25, 2.25, 6.75, 11.25): trk(ax3, o, Y(z), COL['apex'])
        for o in (18, 22.5): trk(ax3, o, Y(z), COL['orr'])
        for o in (-2.25, 2.25): trk(ax3, o, Y(151.8), COL['bd'])
        ax3.text(30, Y(z), '%.1f' % z, fontsize=6.5); ax3.text(30, Y(151.8), 'B/D under the deck 151.8', fontsize=6.5, color=COL['bd'])
    if k == 1:
        z = band(s); zt = tv(s); zi = indy_at(s - v3.S_I0)
        deckbar(ax3, -6.75 + 2.25, 27.25, Y(z)); deckbar(ax3, -27.25, -13.25, Y(zt))
        for o in (-22.5, -18): trk(ax3, o, Y(zt), COL['tv'])
        deckbar(ax3, -27.5, -13.0, Y(zi)); [trk(ax3, o, Y(zi), COL['indy']) for o in (-22.5, -18.0)]
        for o in (-2.25 + 4.5, 2.25 + 4.5, 6.75 + 4.5, 11.25 + 4.5): pass
        for o in (-2.25, 2.25, 6.75, 11.25): trk(ax3, o, Y(z), COL['apex'])
        for o in (18, 22.5): trk(ax3, o, Y(z), COL['orr'])
        zb = bd(s); ax3.add_patch(Rectangle((-9.5, Y(zb) - 0.6), 19, 7.2, fc='none', ec=COL['bd'], lw=0.8))
        trk(ax3, -7.25, Y(zb), COL['bd']); trk(ax3, 7.25, Y(zb), COL['bd']); ax3.add_patch(Rectangle((-5.5, Y(zb) + 0.2), 11, 1.0, fc=COL['bd'], alpha=0.4))
        ax3.text(30, Y(z), 'APEx/ORR %.1f' % z, fontsize=6.5); ax3.text(-12, Y(zi) + 0.2, 'Indianapolis %.1f (crossing over Transvalley)' % zi, fontsize=6.5, color=COL['indy'])
        ax3.text(-46, Y(zt) - 3, 'Transvalley %.1f' % zt, fontsize=6.5, color=COL['tv']); ax3.text(12, Y(zb) + 1, 'Arlington box station %.1f (island 11 m)' % zb, fontsize=6.5, color=COL['bd'])
    if k == 2:
        z = band(s); zt = tv(s); zr = r5(s)
        deckbar(ax3, -27.25, -13.25, Y(zt)); deckbar(ax3, -6.75, 27.25, Y(z)); deckbar(ax3, 24.5, 38.5, Y(zr))
        for o in (-22.5, -18): trk(ax3, o, Y(zt), COL['tv'])
        for o in (-2.25, 2.25, 6.75, 11.25): trk(ax3, o, Y(z), COL['apex'])
        for o in (18, 22.5): trk(ax3, o, Y(z), COL['orr'])
        for o in (29.25, 33.75): trk(ax3, o, Y(zr), COL['r5'])
        zb = bd(s); ax3.add_patch(Rectangle((-14, Y(zb) - 0.6), 10, 6.6, fc='none', ec=COL['bd'], lw=0.8)); trk(ax3, -11.25, Y(zb), COL['bd']); trk(ax3, -6.75, Y(zb), COL['bd'])
        ax3.text(40, Y(zr), 'R5 %.1f' % zr, fontsize=6.5, color=COL['r5']); ax3.text(40, Y(z) - 2, 'APEx/ORR %.1f' % z, fontsize=6.5)
        ax3.text(-46, Y(zt) + 1, 'Transvalley %.1f' % zt, fontsize=6.5, color=COL['tv']); ax3.text(-46, Y(zb), 'B/D box %.1f' % zb, fontsize=6.5, color=COL['bd'])
        ax3.text(-12.5, Y(z) + 2.0, 'open slot', fontsize=6, color='#666')
    if k == 3:
        z = band(s); zb = bd(s); sh = 7.0
        deckbar(ax3, -29.5 + sh, -15.5 + sh, Y(z)); deckbar(ax3, -6.75 + sh, 27.25 + sh, Y(z))
        for o in (-24.75, -20.25): trk(ax3, o + sh, Y(z), COL['tv'])
        for o in (-2.25, 2.25, 6.75, 11.25): trk(ax3, o + sh, Y(z), COL['apex'])
        for o in (18, 22.5): trk(ax3, o + sh, Y(z), COL['orr'])
        ax3.plot([-15.5 + sh, -15.5 + sh, -6.75 + sh, -6.75 + sh], [Y(z) - 1.4, Y(zb) - 0.6, Y(zb) - 0.6, Y(z) - 1.4], color=COL['bd'], lw=0.8)
        trk(ax3, -13.5 + sh, Y(zb), COL['bd']); trk(ax3, -9.0 + sh, Y(zb), COL['bd'])
        ax3.text(36, Y(z), 'band %.1f, about 7 m east of the KMZ line' % z, fontsize=6.5); ax3.text(-46, Y(zb), 'B trough %.1f' % zb, fontsize=6.5, color=COL['bd'])
        ax3.text(-46, Y(146) - 2, 'I-75 trench edge about 26 m west', fontsize=6.5, color='#2f5f86')
ax3.set_xlim(-47, 62); ax3.set_ylim(-3 * H - 4, H + 2); ax3.set_aspect('equal'); ax3.axis('off')
ax3.set_title('Cross sections looking north, true scale (offset from the APEx line, + east; 4.5 m in a group, 6.75 m between groups, 4.75 m to the edge)', fontsize=8, loc='left')
plt.savefig(SP + 'nv/North_Trunk_Viaduct_sketch_v3.png', dpi=105)
print('R5 over the band, s %.0f-%.0f' % r5_over)
