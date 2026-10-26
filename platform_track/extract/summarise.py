"""Turn the Deck extract (deck_headless.py) into tables, per-area GeoJSON and plan drawings.

    python3 summarise.py EXTRACT_JSON DECK_FILES_DIR OUT_DIR

Writes OUT_DIR/data/stations_platforms.csv, OUT_DIR/data/lines.csv, OUT_DIR/data/areas/<area>.geojson and
OUT_DIR/plans/<area>.png. Coordinates are UTM zone 16N metres, as in both editors.
"""
import csv, json, math, os, sys
import numpy as np
from pyproj import Transformer
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MPoly

EXTRACT, FILES, OUT = sys.argv[1:4]
D = json.load(open(EXTRACT))
TR = json.load(open(os.path.join(FILES, 'tracks.json')))
NW = json.load(open(os.path.join(FILES, 'norwood.json')))
CX = json.load(open(os.path.join(FILES, 'context.json')))
os.makedirs(os.path.join(OUT, 'data', 'areas'), exist_ok=True)
os.makedirs(os.path.join(OUT, 'plans'), exist_ok=True)

# ---------------------------------------------------------------- tables
rows = []
for s in D['stations']:
    for o in s['stops']:
        bands = o['bands']; trk = o.get('track_offsets') or []
        b = o.get('bored_at_centre')
        rows.append(dict(
            system=s['sys'], station=s['name'], line=o['line'] or '(fixed, no line id)', line_id=o['pid'] or '', station_deleted=s['deleted'],
            era=o['era'] or '', construction_at_platform='bored' if b else ('box' if b is False else ''),
            type_generated=o['type_generated'], type_now=o['type'], type_set_by_ben=(o['edit'] or {}).get('t', ''),
            offset_now_m=o['o'], offset_generated_m=o['o_generated'], offset_set_by_ben=(o['edit'] or {}).get('o', ''),
            platform_length_m=o['L'], platform_widths_m=';'.join('%.2f' % (x[1] - x[0]) for x in bands),
            platform_bands_m=';'.join('%.2f..%.2f' % tuple(x) for x in bands),
            track_offsets_m=';'.join('%.2f' % x for x in trk), track_spacing_m=('%.2f' % (trk[0] - trk[-1])) if len(trk) >= 2 else '',
            tracks_from=o.get('tracks_from') or '', drawn_from_settings=o['live'],
            centre_E=(o.get('centre') or ['', ''])[0], centre_N=(o.get('centre') or ['', ''])[1], heading_deg=o.get('heading', ''),
            station_E=s['E'], station_N=s['N'], areas=';'.join(s['areas'])))
rows.sort(key=lambda r: (r['system'], r['station'], r['line']))
with open(os.path.join(OUT, 'data', 'stations_platforms.csv'), 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

with open(os.path.join(OUT, 'data', 'lines.csv'), 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['line_id', 'label', 'system', 'era', 'length_m', 'drawn_from_settings', 'line_edited', 'bored_m', 'box_m', 'bored_runs'])
    for l in D['lines']:
        bm = l.get('bored_m'); w.writerow([l['id'], l['label'], l['sys'], l['era'] or '', l['length_m'], l['live'], l['edited'],
                                          bm if bm is not None else '', round(l['length_m'] - bm) if bm is not None else '',
                                          ' '.join('%d-%d:%s' % tuple(r) for r in l.get('bored_runs', []))])

# ---------------------------------------------------------------- areas
AREAS = {'fountain_square': (715090, 4331050, 280), 'cut': (712980, 4331900, 420), 'norwood_central': (720200, 4337960, 560)}


def inwin(c, k, pad=1.0):
    x, y, r = AREAS[k]; return any(abs(q[0] - x) <= r * 1.5 * pad and abs(q[1] - y) <= r * pad for q in c)


def feat(props, gtype, coords):
    return {'type': 'Feature', 'properties': props, 'geometry': {'type': gtype, 'coordinates': coords}}


def area_features(k):
    out = []
    for s in D['stations']:
        if s['deleted']: continue
        for o in s['stops']:
            for i, rg in enumerate(o['rings']):
                if inwin(rg, k):
                    out.append(feat({'layer': s['sys'] + '_platform', 'station': s['name'], 'line': o['line'], 'type': o['type'], 'n': i,
                                     'width_m': round(o['bands'][i][1] - o['bands'][i][0], 2) if i < len(o['bands']) else None,
                                     'length_m': o['L'], 'source': 'Mill Creek Deck (deck_headless)'}, 'Polygon', [rg + [rg[0]]]))
    for t in D['key_tracks'][k]:
        out.append(feat({'layer': t['sys'] + '_track', 'line': t['line'], 'from': t['from'], 'source': 'Mill Creek Deck (deck_headless)'}, 'LineString', t['c']))
    if k == 'cut':
        for f in TR['features']:
            g = f['geometry']; p = f['properties']
            cs = g['coordinates'] if g['type'] == 'LineString' else (g['coordinates'][0] if g['type'] == 'Polygon' else [g['coordinates']] if g['type'] == 'Point' else [])
            if cs and inwin(cs, k): out.append({'type': 'Feature', 'properties': dict(p, source='tracks.json'), 'geometry': g})
    if k == 'norwood_central':
        for f in NW['features']:
            if f['properties'].get('hide'): continue
            out.append({'type': 'Feature', 'properties': dict(f['properties'], source='norwood.json'), 'geometry': f['geometry']})
    return out


for k in AREAS:
    json.dump({'type': 'FeatureCollection', 'name': k, 'crs': {'type': 'name', 'properties': {'name': 'urn:ogc:def:crs:EPSG::32616'}},
               'features': area_features(k)}, open(os.path.join(OUT, 'data', 'areas', k + '.geojson'), 'w'))

# ---------------------------------------------------------------- plans
COL = {'metro': '#2a78d6', 'rer': '#eb6834', 'apex': '#1baf7a', 'orr': '#eda100', 'tv': '#e87ba4', 'cvx': '#008300', 'bay': '#eda100'}
INK, MUTED, SURF = '#1f1f1f', '#6b6b6b', '#fcfcfb'
UTM = Transformer.from_crs(4326, 32616, always_xy=True)
LON0, LAT0, R = -84.5125, 39.1018, 6378137.0
Cc, Sc = math.cos(math.radians(11)), math.sin(math.radians(11))


def fs_to_utm(u, v):      # inverse of fs_kmz_layout.to_frame
    x, y = Cc * u - Sc * v, Sc * u + Cc * v
    k = R * math.cos(math.radians(LAT0))
    lon = LON0 + math.degrees(x / k)
    m0 = math.log(math.tan(math.pi / 4 + math.radians(LAT0) / 2))
    lat = math.degrees(2 * math.atan(math.exp(y / k + m0)) - math.pi / 2)
    return UTM.transform(lon, lat)


def setup(k, title, sub):
    x, y, r = AREAS[k]
    fig, ax = plt.subplots(figsize=(15, 10.5)); fig.patch.set_facecolor(SURF); ax.set_facecolor(SURF)
    ax.set_xlim(x - r * 1.5, x + r * 1.5); ax.set_ylim(y - r, y + r); ax.set_aspect('equal')
    ax.tick_params(colors=MUTED, labelsize=8, length=0)
    for sp in ax.spines.values(): sp.set_color('#dddddd')
    ax.ticklabel_format(useOffset=False, style='plain')
    fig.text(0.02, 0.975, title, fontsize=17, weight='bold', color=INK, va='top')
    fig.text(0.02, 0.945, sub, fontsize=10, color=MUTED, va='top')
    # scale bar
    x0, y0 = x - r * 1.45, y - r * 0.93
    ax.plot([x0, x0 + 100], [y0, y0], color=INK, lw=2); ax.text(x0 + 50, y0 + 6, '100 m', ha='center', fontsize=8, color=INK)
    return fig, ax


def platforms(ax, k, systems=('metro', 'rer', 'cvx'), label=True):
    done, placed = set(), []
    for s in D['stations']:
        if s['deleted'] or s['sys'] not in systems: continue
        for o in s['stops']:
            for rg in o['rings']:
                if not inwin(rg, k): continue
                ax.add_patch(MPoly(rg, closed=True, fc=COL[s['sys']], ec=COL[s['sys']], alpha=0.35, lw=0.6, zorder=4))
            if label and o['rings'] and inwin(o['rings'][0], k, 0.95):
                c = np.mean(np.array([q for rg in o['rings'] for q in rg]), axis=0); key = (s['name'], o['line'])
                if key in done: continue
                done.add(key)
                while any(abs(c[0] - p[0]) < 110 and abs(c[1] - p[1]) < 22 for p in placed): c = c + np.array([0.0, -24.0])   # keep labels apart
                placed.append(c)
                txt = '%s\n%s, %s' % (s['name'], o['line'].replace('Metro ', ''), o['type']) if o['line'] else '%s\nTRI A/B/D box, %d islands' % (s['name'], len(o['rings']))
                ax.text(c[0], c[1], txt, fontsize=7.5, color=INK,
                        ha='center', va='center', zorder=9, bbox=dict(fc=SURF, ec='none', alpha=0.75, pad=0.6))


def deck_tracks(ax, k, systems=('metro', 'rer', 'cvx'), dashed=()):
    for t in D['key_tracks'][k]:
        if t['sys'] not in systems: continue
        c = np.array(t['c']); ax.plot(c[:, 0], c[:, 1], color=COL[t['sys']], lw=0.9, ls='--' if t['sys'] in dashed else '-', zorder=5)


def legend(ax, items):
    from matplotlib.lines import Line2D
    hs = [Line2D([0], [0], color=c, lw=2.2, ls=ls, label=l) for l, c, ls in items]
    ax.legend(handles=hs, loc='upper right', fontsize=8.5, frameon=True, facecolor=SURF, edgecolor='#dddddd')


# Fountain Square: the Deck against the Fountain Square model (fs_model.py, 2026-10-26)
fig, ax = setup('fountain_square', 'Fountain Square: platforms and tracks in the Mill Creek Deck',
                'Filled: the Deck as saved (layout %s). Black dashed: the Fountain Square model (Ben\'s KMZ platforms; Metro still at 500 ft there). '
                'Metro 400 ft, TRI 670 ft.' % D.get('layout_updated', '')[:10])
deck_tracks(ax, 'fountain_square'); platforms(ax, 'fountain_square')
MODEL = [('A/D westbound island (model)', [(-185.1, 9.1), (19.1, 9.1), (19.1, 19.1), (-185.1, 19.1)]),
         ('A/D eastbound island (model)', [(-185.1, -17.9), (19.1, -17.9), (19.1, -7.9), (-185.1, -7.9)]),
         ('B island (model)', [(81.0, 22.7), (93.0, 22.7), (93.0, 226.9), (81.0, 226.9)])]
RECT = lambda u0, u1, v0, v1: [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
MODEL += [('Line 1 platforms (model)', RECT(-7.8, 144.6, -53.5, -48.05)), ('', RECT(-7.8, 144.6, -66.95, -61.5)),
          ('Line 7 platforms (model)', RECT(-129.6, 22.8, 88.25, 93.7)), ('', RECT(-129.6, 22.8, 74.8, 80.25)),
          ('Line 2 platforms (model)', RECT(-63.95, -58.5, -108.9, 43.5)), ('', RECT(-50.5, -45.05, -108.9, 43.5))]   # fs_model.py PARTS
for nm, poly in MODEL:
    pts = [fs_to_utm(u, v) for u, v in poly]; ax.add_patch(MPoly(pts, closed=True, fill=False, ec=INK, ls='--', lw=1.0, zorder=6))
legend(ax, [('Metro (Deck)', COL['metro'], '-'), ('TRI / RER (Deck)', COL['rer'], '-'), ('Fountain Square model', INK, '--')])
fig.savefig(os.path.join(OUT, 'plans', 'fountain_square.png'), dpi=130, facecolor=SURF); plt.close(fig)

# CUT: APEx level 0 and the lower level -2 (tracks.json), the TRI box, Metro
fig, ax = setup('cut', 'Union Terminal: APEx field, lower level, TRI box and Metro',
                'APEx level 0 (rail 160.3 m) and the lower level -2 (rail 144 m) from tracks.json; TRI and Metro from the Deck as saved. Switch marks as small crosses.')
for f in TR['features']:
    p, g = f['properties'], f['geometry']; L = p.get('layer')
    if g['type'] == 'LineString':
        c = np.array(g['coordinates'])
        if not inwin(c, 'cut'): continue
        if L == 'apex':
            col = COL['cvx'] if 'CVG' in p.get('name', '') else COL['apex']
            ax.plot(c[:, 0], c[:, 1], color=col, lw=0.8, zorder=3)
        elif L == 'lower':
            ax.plot(c[:, 0], c[:, 1], color=COL['orr'], lw=0.9, ls='--' if p.get('state') in ('under', 'ramp') else '-', zorder=3)
        elif L == 'passing':
            ax.plot(c[:, 0], c[:, 1], color=MUTED, lw=0.8, zorder=3)
    elif g['type'] == 'Polygon' and L in ('apex_plat', 'lower_plat'):
        rg = g['coordinates'][0]
        if inwin(rg, 'cut'):
            col = COL['cvx'] if 'CVG' in p.get('name', '') else COL['apex'] if L == 'apex_plat' else COL['orr']
            ax.add_patch(MPoly(rg, closed=True, fc=col, ec=col, alpha=0.25 if L == 'apex_plat' else 0.45, lw=0.5, zorder=2 if L == 'apex_plat' else 3))
    elif g['type'] == 'Point' and p.get('kind') == 'switch':
        q = g['coordinates']
        if inwin([q], 'cut'): ax.plot(q[0], q[1], marker='x', ms=4, color=INK, mew=0.8, zorder=7)
deck_tracks(ax, 'cut', dashed=('rer', 'metro')); platforms(ax, 'cut')
ax.text(712783, 4332075, 'APEx field: 7 islands + M\n488 m, level 0\nLower A-H: 4 islands\n305 m, level -2', fontsize=8, ha='center', color=INK, zorder=9,
        bbox=dict(fc=SURF, ec='none', alpha=0.8))
legend(ax, [('APEx level 0', COL['apex'], '-'), ('Lower level -2 (dashed under the deck)', COL['orr'], '-'), ('CVG Express', COL['cvx'], '-'),
            ('TRI / RER (underground)', COL['rer'], '--'), ('Metro (underground)', COL['metro'], '--')])
fig.savefig(os.path.join(OUT, 'plans', 'cut.png'), dpi=130, facecolor=SURF); plt.close(fig)

# Norwood Central: sketch v13 (norwood.json) with Metro and TRI below
fig, ax = setup('norwood_central', 'Norwood Central: surface tracks (sketch v13) and the lines below',
                'Surface tracks and platforms from norwood.json (rail about 178 m, in a cut); Metro and TRI from the Deck as saved, dashed (underground). '
                'Metro 3 terminates at platform level.')
for f in NW['features']:
    p, g = f['properties'], f['geometry']; L = p.get('layer')
    if p.get('hide'): continue
    if L == 'nw_track':
        c = np.array(g['coordinates']); ax.plot(c[:, 0], c[:, 1], color=COL.get(p['sys'], MUTED), lw=1.0, ls='--' if p.get('tunnel') else '-', zorder=5)
        ax.text(c[0, 0], c[0, 1], ' ' + p['track'], fontsize=6.5, color=INK, ha='right', va='center', zorder=9)
    elif L == 'nw_plat':
        rg = g['coordinates'][0]; ax.add_patch(MPoly(rg, closed=True, fc=COL.get(p['sys'], MUTED), ec=COL.get(p['sys'], MUTED), alpha=0.4, lw=0.5, zorder=4))
        c = np.mean(np.array(rg), axis=0); ax.text(c[0], c[1], p.get('label', ''), fontsize=7, ha='center', va='center', color=INK, zorder=9)
    elif L in ('nw_conc', 'nw_bldg'):
        rg = g['coordinates'][0] if g['type'] == 'Polygon' else None
        if rg: ax.add_patch(MPoly(rg, closed=True, fill=False, ec=MUTED, lw=1.0, ls=':' if L == 'nw_conc' else '-', zorder=6))
deck_tracks(ax, 'norwood_central', systems=('metro', 'rer'), dashed=('metro', 'rer')); platforms(ax, 'norwood_central', systems=('metro', 'rer'))
legend(ax, [('APEx', COL['apex'], '-'), ('ORR and bays', COL['orr'], '-'), ('Transvalley (dashed underground)', COL['tv'], '-'),
            ('TRI / RER (underground)', COL['rer'], '--'), ('Metro', COL['metro'], '--'), ('Concourse (dotted), building', MUTED, ':')])
fig.savefig(os.path.join(OUT, 'plans', 'norwood_central.png'), dpi=130, facecolor=SURF); plt.close(fig)

# Norwood Central track diagram: along the APEx through track T7 (s from the APEx platform centre), offsets stretched x4
from shapely.geometry import LineString as SL, Point as SP, Polygon as SPoly
NT = {f['properties']['track'] + ('*' if f['properties'].get('tunnel') else ''): f for f in NW['features'] if f['properties'].get('layer') == 'nw_track'}
T7 = SL(NT['T7']['geometry']['coordinates'])
S0 = T7.project(SPoly([tuple(q) for f in NW['features'] if f['properties'].get('label') == 'APEx S' for q in f['geometry']['coordinates'][0]]).centroid)
FRAME_S0 = 4682.0     # Norwood frame s of the APEx platform centre (W1 leaves T9 at frame s 4,850, 168 m east of it)
EX = 4.0


def so(q):
    s = T7.project(SP(q)); a, b = T7.interpolate(max(s - 2, 0)), T7.interpolate(min(s + 2, T7.length))
    d = np.array([b.x - a.x, b.y - a.y]); d /= np.linalg.norm(d); base = T7.interpolate(s)
    return s - S0, float(np.dot([q[0] - base.x, q[1] - base.y], [-d[1], d[0]]))


fig, ax = plt.subplots(figsize=(16, 9)); fig.patch.set_facecolor(SURF); ax.set_facecolor(SURF)
fig.text(0.02, 0.975, 'Norwood Central: track diagram (sketch v13)', fontsize=17, weight='bold', color=INK, va='top')
fig.text(0.02, 0.945, 'Distance along the APEx through track T7 from the APEx platform centre (Norwood frame s %d); offsets from T7, north up, stretched x%d. '
         'Turnouts are where a track leaves another; crossings marked x.' % (FRAME_S0, EX), fontsize=10, color=MUTED, va='top')
for f in NW['features']:
    p, g = f['properties'], f['geometry']; L = p.get('layer')
    if L == 'nw_track':
        c = np.array([so(q) for q in g['coordinates']]); ax.plot(c[:, 0], c[:, 1] * EX, color=COL.get(p['sys'], MUTED), lw=1.4, ls='--' if p.get('tunnel') else '-', zorder=5)
        if not p.get('tunnel'): ax.text(c[0, 0] - 6, c[0, 1] * EX, p['track'], fontsize=8, ha='right', va='center', color=INK)
    elif L == 'nw_plat':
        c = np.array([so(q) for q in g['coordinates'][0]]); ax.add_patch(MPoly(np.c_[c[:, 0], c[:, 1] * EX], closed=True, fc=COL.get(p['sys'], MUTED), alpha=0.35, ec='none', zorder=3))
        ax.text(c[:, 0].mean(), c[:, 1].mean() * EX, '%s  %d m' % (p['label'], p['length_m']), fontsize=8, ha='center', va='center', color=INK, zorder=9)
CROSS = []
for a in NT:
    for b in NT:
        if a < b:
            x = SL(NT[a]['geometry']['coordinates']).intersection(SL(NT[b]['geometry']['coordinates']))
            for q in ([x] if x.geom_type == 'Point' else [g for g in getattr(x, 'geoms', []) if g.geom_type == 'Point']):
                s_, o_ = so((q.x, q.y))
                if a.rstrip('*') == b.rstrip('*'): continue
                la, lb = SL(NT[a]['geometry']['coordinates']), SL(NT[b]['geometry']['coordinates'])
                if min(SP(la.coords[0]).distance(q), SP(la.coords[-1]).distance(q), SP(lb.coords[0]).distance(q), SP(lb.coords[-1]).distance(q)) < 0.5: continue   # a turnout
                pa, pb = la.project(q), lb.project(q)
                if all(la.interpolate(pa + d).distance(lb.interpolate(pb + d)) < 0.3 for d in (-5, 5)) or \
                   any(la.interpolate(pa + d).distance(lb) < 0.3 for d in (-6, 6)): continue                       # running together or merging
                CROSS.append((a.rstrip('*'), b.rstrip('*'), round(s_ + FRAME_S0), round(o_, 1)))
                ax.plot(s_, o_ * EX, marker='x', ms=7, mew=1.6, color=INK, zorder=8)
for t in D['key_tracks']['norwood_central']:
    c = np.array([so(q) for q in t['c']]); m = (np.abs(c[:, 1]) < 110) & (c[:, 0] > -600) & (c[:, 0] < 700)
    if m.sum() > 1: ax.plot(c[m, 0], c[m, 1] * EX, color=COL[t['sys']], lw=0.9, ls=':', zorder=2)
ax.set_xlim(-600, 700); ax.set_ylim(-110 * EX, 110 * EX)
ax.set_yticks(np.arange(-100, 101, 20) * EX); ax.set_yticklabels(['%d' % v for v in np.arange(-100, 101, 20)])
ax.set_xlabel('m along T7 from the APEx platform centre', color=MUTED, fontsize=9); ax.set_ylabel('m from T7 (north +)', color=MUTED, fontsize=9)
ax.tick_params(colors=MUTED, labelsize=8, length=0)
for sp in ax.spines.values(): sp.set_color('#dddddd')
ax.grid(axis='x', color='#eeeeee', lw=0.6)
legend(ax, [('APEx', COL['apex'], '-'), ('ORR and bays', COL['orr'], '-'), ('Transvalley (dashed underground)', COL['tv'], '-'),
            ('Metro and TRI below (dotted)', COL['metro'], ':')])
fig.savefig(os.path.join(OUT, 'plans', 'norwood_central_tracks.png'), dpi=130, facecolor=SURF); plt.close(fig)
print('Norwood level crossings (track, track, frame s, offset from T7):', CROSS)
print('rows', len(rows), 'lines', len(D['lines']))
