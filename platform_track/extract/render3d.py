"""Drawings from the combined 3D tracks (combine3d.py): the north trunk long section, cross-sections of the north
viaduct, and 3D views of Union Terminal and Fountain Square.

    python3 render3d.py OUT_DIR DECK_EXTRACT DECK_FILES PROFILES_RAIL PROFILES_FILES
"""
import csv, json, math, os, pickle, re, sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from pyproj import Transformer
from shapely.geometry import LineString
import shapely

OUT, DECK, DFILES, PROF, PFILES = sys.argv[1:6]
TRK = pickle.load(open(os.path.join(OUT, 'data', '_tracks3d.pkl'), 'rb'))
D = json.load(open(DECK)); TR = json.load(open(os.path.join(DFILES, 'tracks.json'))); NW = json.load(open(os.path.join(DFILES, 'norwood.json')))
PR = json.load(open(PROF))['lines']
P3 = {(r['station'], r['line']): r for r in csv.DictReader(open(os.path.join(OUT, 'data', 'platforms3d.csv')))}
INK, MUTED, SURF = '#1f1f1f', '#6b6b6b', '#fcfcfb'
C = {'metro': '#2a78d6', 'rer': '#eb6834', 'apex': '#1baf7a', 'orr': '#eda100', 'tv': '#e87ba4', 'cvx': '#008300'}
T = Transformer.from_crs(4326, 32616, always_xy=True)


def cls(t):
    s, n, pid = t['sys'], t['name'] or '', t['pid'] or ''
    if s == 'metro': return 'metro', '-', 'Metro'
    if s == 'cvx' or 'CVG' in n: return 'cvx', '-', 'CVG Express'
    if s == 'rer':
        if pid == 'R-D-710306-4337028': return 'rer', (0, (5, 2)), 'TRI D (upper deck)'
        if pid.startswith('R-A-') or n in ('A', 'RER A'): return 'rer', (0, (1, 1.5)), 'TRI A'
        if 'B' in n and 'D' in n: return 'rer', '-', 'TRI B/D'
        if n in ('D', 'RER D'): return 'rer', (0, (5, 2)), 'TRI D'
        if n in ('E', 'RER E'): return 'rer', (0, (6, 2, 1, 2)), 'TRI E'
        return 'rer', '-', 'TRI ' + n.replace('RER ', '')
    if s == 'apex_tr':
        if 'north approach 1 of 6' in n or 'north approach 2 of 6' in n or 'Floridian (' in n: return 'apex', (0, (5, 2)), 'APEx Indianapolis'
        return 'apex', '-', 'APEx'
    if s == 'lower_tr':
        if n.startswith('R5'): return 'orr', (0, (5, 2)), 'ORR R5'
        if n.startswith('Transvalley'): return 'tv', '-', 'Transvalley'
        return 'orr', '-', 'ORR / Transvalley / intercity (lower level)'
    if s.startswith('nw_'): return {'nw_apex': 'apex', 'nw_orr': 'orr', 'nw_bay': 'orr', 'nw_tv': 'tv'}[s], '-', 'Norwood ' + s[3:]
    return 'metro', '-', s


def frame(fig, title, sub):
    fig.patch.set_facecolor(SURF)
    fig.text(0.02, 0.975, title, fontsize=17, weight='bold', color=INK, va='top')
    fig.text(0.02, 0.945, sub, fontsize=10, color=MUTED, va='top', wrap=True)


# ---------------------------------------------------------------- 1. north trunk long section (rail level against distance along the trunk)
from shapely.geometry import Point
def feat_xy(name):
    for f in TR['features']:
        if f['properties'].get('name') == name and f['geometry']['type'] == 'LineString': return f['geometry']['coordinates']
ap4 = feat_xy('APEx north approach 4 of 6')[::-1]; nw1 = feat_xy('APEx Norwood (Transcontinental), track 1 of 2')
REF = LineString([(712783, 4331300), (712783, 4332134), (712762, 4332842)] + [tuple(q) for q in ap4[1:]] + [tuple(q) for q in nw1[1:] if q[0] < 713700])
S0 = REF.project(Point(712783, 4331890))
fig, ax = plt.subplots(figsize=(18, 10)); ax.set_facecolor(SURF)
frame(fig, 'North trunk: rail levels from Union Terminal to Ludlow',
      'Distance along the APEx trunk from the CUT platform centre; every track within 70 m of it. Levels from the Deck\'s own marks (CUT summary, dive, level marks) and, for Metro and TRI where they apply, '
      'the Rail Profiles page. Grey dashed: the Profiles page\'s own TRI B (RER-2) and D (RER-4) on their own routes, its older CUT basis.')
seen = set()


def along(xy):
    g = shapely.points(xy); return shapely.line_locate_point(REF, g) - S0, shapely.distance(REF, g)


for t in TRK:
    xy, z = t['xy'], t['z']
    if len(xy) < 2: continue
    sx, d = along(xy); m = (d < 70) & ~np.isnan(z)
    if m.sum() < 2: continue
    col, ls, lab = cls(t)
    idx = np.where(m)[0]
    for r in np.split(idx, np.where(np.diff(idx) > 1)[0] + 1):
        if len(r) < 2: continue
        ax.plot(sx[r], z[r], color=C[col], ls=ls, lw=1.1 if col != 'metro' else 0.7, alpha=0.95 if col != 'metro' else 0.6, label=lab if lab not in seen else None, zorder=4); seen.add(lab)
for lid, lab in (('RER_2', 'Profiles page: RER-2 (TRI B)'), ('RER_4', 'Profiles page: RER-4 (TRI D)')):
    path = json.load(open(os.path.join(PFILES, 'rer/lines', lid + '.json')))['path']
    xy = np.array([T.transform(lo, la) for _, lo, la in path]); cs = np.array([c for c, _, _ in path])
    sm = np.array([[a, b] for a, b, _ in PR[lid]['samples']]); L = LineString(xy)
    dens = np.array([L.interpolate(v).coords[0] for v in np.arange(0, L.length, 10)])
    seg = np.r_[0, np.cumsum(np.hypot(*np.diff(xy, axis=0).T))]; zz = np.interp(np.interp(np.arange(0, L.length, 10), seg, cs), sm[:, 0], sm[:, 1])
    sx, d = along(dens); idx = np.where(d < 70)[0]
    for r in np.split(idx, np.where(np.diff(idx) > 1)[0] + 1):
        if len(r) > 1: ax.plot(sx[r], zz[r], color='#9a9a9a', ls='--', lw=1.0, label=lab if lab not in seen else None, zorder=3); seen.add(lab)
STREETS = [('Gest', (712785, 4331547)), ('W Liberty', (712761, 4332357)), ('Findlay', (712760, 4332587)), ('Bank', (712746, 4332971)), ('Alfred', (712736, 4333983)),
           ('Straight', (712752, 4334173)), ('Marshall', (712726, 4334370)), ('Hopple', (712313, 4334862)), ('Ludlow', (712678, 4336948))]
for nm, q in STREETS:
    x = REF.project(Point(q)) - S0; ax.axvline(x, color='#dddddd', lw=0.8, zorder=1); ax.text(x, 177.2, nm, rotation=90, fontsize=8, color=MUTED, ha='right', va='top')
ax.axvspan(-244, 244, color=C['apex'], alpha=0.07, zorder=0); ax.text(0, 128.6, 'CUT platforms (APEx 488 m; lower level 305 m)', ha='center', fontsize=8, color=INK)
for txt, q, z in (('lower level 144 m', (712783, 4331900), 142.2), ('dive 2.72%', (712760, 4332780), 152.0), ('deck tip 166.6 m', (712319, 4335532), 168.2),
                  ('Indianapolis + D to 174.3 m', (712267, 4335609), 175.6), ('B/D box 151.6 m, then 3.3% up', (712700, 4334300), 149.0),
                  ('TRI A 135.9 m under the lower level (Deck)', (712783, 4331860), 133.6), ('no APEx tracks in tracks.json here', (712762, 4332620), 157.0)):
    ax.text(REF.project(Point(q)) - S0, z, txt, fontsize=8.5, color=INK, ha='center', bbox=dict(fc=SURF, ec='none', alpha=0.8, pad=0.5))
ax.set_xlim(-650, 5400); ax.set_ylim(128, 178)
ax.set_xlabel('Distance along the APEx trunk from the CUT platform centre (m), north to the right', color=MUTED, fontsize=9); ax.set_ylabel('Rail level (m, NAVD88)', color=MUTED, fontsize=9)
ax.tick_params(colors=MUTED, labelsize=8, length=0)
for sp in ax.spines.values(): sp.set_color('#dddddd')
ax.grid(axis='y', color='#eeeeee', lw=0.6)
ax.legend(loc='upper left', fontsize=8.5, frameon=True, facecolor=SURF, edgecolor='#dddddd', ncol=2)
os.makedirs(os.path.join(OUT, 'plans'), exist_ok=True)
fig.savefig(os.path.join(OUT, 'plans', 'north_trunk_long_section.png'), dpi=120, facecolor=SURF); plt.close(fig)

# ---------------------------------------------------------------- 2. cross-sections of the north viaduct
CUTS = [(4332700, 'Between Findlay and Bank: lower pairs in the dive (no APEx tracks drawn here)'), (4333300, 'Western (B/D bored, under the west side)'),
        (4334250, 'Straight: B/D box under the west side'), (4334800, 'Camp Washington: B/D on the viaduct'),
        (4335400, 'North of Hopple: Indianapolis + D climbing'), (4335900, 'Arlington: Indianapolis + D deck, R5 under it')]
fig, axs = plt.subplots(len(CUTS), 1, figsize=(15, 3.9 * len(CUTS)))
frame(fig, 'North viaduct: cross-sections', 'Every track crossing each northing within 130 m of the APEx trunk, at its rail level; looking north (west on the left). Same levels as the long section. Heights true to scale.')
SHORT = {'APEx': 'APEx', 'APEx Indianapolis': 'Indy', 'ORR / Transvalley / intercity (lower level)': 'ORR/TV', 'ORR R5': 'R5', 'TRI B/D': 'B/D', 'TRI B': 'B',
         'TRI D (upper deck)': 'D', 'TRI D': 'D', 'TRI A': 'A', 'TRI E': 'E', 'CVG Express': 'CVG'}
for ax, (N, title) in zip(axs, CUTS):
    ax.set_facecolor(SURF)
    xc = REF.intersection(LineString([(711000, N), (714000, N)]))
    xc = (xc.x if xc.geom_type == 'Point' else list(xc.geoms)[0].x) if not xc.is_empty else 712700
    for t in TRK:
        xy, z = t['xy'], t['z']
        if len(xy) < 2: continue
        for i in np.where(np.diff(np.sign(xy[:, 1] - N)) != 0)[0]:
            a_, b_ = xy[i], xy[i + 1]; f = (N - a_[1]) / (b_[1] - a_[1]) if b_[1] != a_[1] else 0
            x = a_[0] + f * (b_[0] - a_[0])
            if abs(x - xc) > 130: continue
            col, ls, lab = cls(t); nm = SHORT.get(lab, lab)
            if t['sys'] == 'metro': nm = 'M' + re.sub(r'\D', '', (t['name'] or '').split('Line')[-1])
            if np.isnan(z[i]) or np.isnan(z[i + 1]):
                ax.plot(x - xc, 129.5, marker='|', ms=10, color=C[col], alpha=0.7); ax.text(x - xc, 131.2, nm, rotation=90, fontsize=6.5, ha='center', va='bottom', color=MUTED); continue
            zz = z[i] + f * (z[i + 1] - z[i])
            ax.plot(x - xc, zz, marker='o', ms=6, color=C[col], mec=INK, mew=0.4, zorder=5)
            ax.text(x - xc, zz + 1.2, nm, rotation=90, fontsize=7, ha='center', va='bottom', color=INK)
    ax.set_title('N %s: %s' % (format(N, ','), title), loc='left', fontsize=11, color=INK)
    ax.set_xlim(-130, 130); ax.set_ylim(128, 182); ax.set_aspect('equal'); ax.set_ylabel('rail (m)', fontsize=8, color=MUTED)
    ax.set_xlabel('m east of the APEx trunk centre line', fontsize=8, color=MUTED)
    ax.tick_params(colors=MUTED, labelsize=8, length=0)
    for sp in ax.spines.values(): sp.set_color('#dddddd')
    ax.grid(color='#f0f0f0', lw=0.6)
    ax.text(-128, 129.0, 'ticks at the foot: tracks with no level', fontsize=6.5, color=MUTED, va='bottom')
fig.tight_layout(rect=(0, 0, 1, 0.95)); fig.savefig(os.path.join(OUT, 'plans', 'north_viaduct_sections.png'), dpi=110, facecolor=SURF); plt.close(fig)


# ---------------------------------------------------------------- 3. 3D views
def view3d(name, box, title, sub, elev, azim, ex=3.0, zlim=(125, 180)):
    x0, x1, y0, y1 = box
    fig = plt.figure(figsize=(17, 11)); frame(fig, title, sub)
    ax = fig.add_axes([0.0, 0.0, 1.0, 0.92], projection='3d'); ax.set_facecolor(SURF)
    seen = set()
    for t in TRK:
        xy, z = t['xy'], t['z']
        if len(xy) < 2: continue
        m = (xy[:, 0] > x0) & (xy[:, 0] < x1) & (xy[:, 1] > y0) & (xy[:, 1] < y1) & ~np.isnan(z)
        idx = np.where(m)[0]
        for r in np.split(idx, np.where(np.diff(idx) > 1)[0] + 1):
            if len(r) < 2: continue
            col, ls, lab = cls(t)
            ax.plot(xy[r, 0], xy[r, 1], (z[r] - zlim[0]) * ex, color=C[col], ls=ls, lw=1.0, label=lab if lab not in seen else None); seen.add(lab)
    polys, cols = [], []
    for s in D['stations']:
        if s['deleted']: continue
        for o in s['stops']:
            r = P3.get((s['name'], o['line']))
            if not r or not r['rail_m']: continue
            for rg in o['rings']:
                a = np.array(rg)
                if not ((a[:, 0] > x0).all() and (a[:, 0] < x1).all() and (a[:, 1] > y0).all() and (a[:, 1] < y1).all()): continue
                polys.append([(p[0], p[1], (float(r['rail_m']) - zlim[0]) * ex) for p in rg]); cols.append(C[s['sys']])
    for f in TR['features']:
        p, g = f['properties'], f['geometry']
        if p.get('layer') in ('apex_plat', 'lower_plat'):
            a = np.array(g['coordinates'][0]); zz = TR['summary']['apex_cut'] if p['layer'] == 'apex_plat' else TR['summary']['lower_rail']
            if (a[:, 0] > x0).all() and (a[:, 0] < x1).all() and (a[:, 1] > y0).all() and (a[:, 1] < y1).all():
                polys.append([(q[0], q[1], (zz - zlim[0]) * ex) for q in a]); cols.append(C['apex'] if p['layer'] == 'apex_plat' else C['orr'])
    for f in NW['features']:
        p, g = f['properties'], f['geometry']
        if p.get('layer') == 'nw_plat':
            a = np.array(g['coordinates'][0])
            if (a[:, 0] > x0).all() and (a[:, 0] < x1).all(): polys.append([(q[0], q[1], (178.0 - zlim[0]) * ex) for q in a]); cols.append(C.get({'bay': 'orr'}.get(p['sys'], p['sys']), MUTED))
    if polys: ax.add_collection3d(Poly3DCollection(polys, facecolors=cols, edgecolors='none', alpha=0.35))
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_zlim(0, (zlim[1] - zlim[0]) * ex)
    zt = np.arange(math.ceil(zlim[0] / 10) * 10, zlim[1] + 1, 10); ax.set_zticks((zt - zlim[0]) * ex); ax.set_zticklabels(['%d' % v for v in zt])
    ax.set_box_aspect((x1 - x0, y1 - y0, (zlim[1] - zlim[0]) * ex))
    ax.view_init(elev=elev, azim=azim); ax.tick_params(labelsize=7, colors=MUTED)
    ax.set_xlabel('E', fontsize=8, color=MUTED); ax.set_ylabel('N', fontsize=8, color=MUTED); ax.set_zlabel('rail (m)', fontsize=8, color=MUTED)
    ax.xaxis.pane.set_alpha(0); ax.yaxis.pane.set_alpha(0); ax.zaxis.pane.set_alpha(0.03)
    ax.legend(loc='upper left', fontsize=8.5, frameon=True, facecolor=SURF, edgecolor='#dddddd', bbox_to_anchor=(0.02, 0.98))
    fig.savefig(os.path.join(OUT, 'plans', name), dpi=115, facecolor=SURF); plt.close(fig)


view3d('cut_3d.png', (712600, 713400, 4331650, 4332150), 'Union Terminal in 3D: APEx platforms, lower level, TRI box, Metro',
       'Heights 6 times true. APEx 160.3 m and the lower level 144 m from tracks.json; TRI A and the CVG Express at the Deck\'s levels (the Profiles page disagrees, see conflicts.csv); '
       'TRI B in the box, TRI E and Metro from the Rail Profiles page. Platforms at rail level. Looking north-west.', 14, -62, ex=6.0, zlim=(130, 165))
view3d('fountain_square_3d.png', (714850, 715300, 4330850, 4331250), 'Fountain Square in 3D: the Deck\'s plan at the Rail Profiles levels',
       'Heights 6 times true. Metro 1, 2, 7 and TRI A/D, B from the Rail Profiles page (Line 7 on its defaults: no saved profile). Platforms at rail level. Looking north-west.', 14, -58, ex=6.0, zlim=(135, 165))
view3d('north_trunk_3d.png', (711900, 713000, 4332300, 4336300), 'North trunk in 3D: CUT to Arlington',
       'Heights 8 times true. Levels from the Deck\'s marks and the Rail Profiles page; tracks with no level left out. Looking north-west.', 16, -120, ex=8.0, zlim=(130, 180))
print('drawn')
