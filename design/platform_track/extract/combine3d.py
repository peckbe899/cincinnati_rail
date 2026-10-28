"""Combine the Deck's plan (where every track and platform is) with rail levels into 3D track lines.

    python3 combine3d.py DECK_EXTRACT PROFILES_RAIL PROFILES_FILES DECK_FILES OUT_DIR

Levels come from two places:

1. The Rail Profiles page (profiles_headless.py): rail level and structure type along each Metro line, the five TRI
   core lines and the CVG Express. A Deck track point takes the level at its chainage on the matching Profiles line,
   found by projecting the point onto that line's path, when it lies within MATCH_M of it.

2. The Deck's own levels, for what the Profiles page does not cover (APEx, ORR, Transvalley, the CUT lower level,
   the north trunk, TRI B/D and A outside the core): the level marks, the CUT summary and the intercity and C&O
   profiles that tracks.json and context.json publish. Each mark is a located level; a track takes the marks of its
   group that lie within the group's distance of it and is interpolated between them along its length. Nothing is
   extrapolated, and a gap longer than GAP_M between marks is left without a level.

Where both give a level, the Profiles level is used and the difference is listed in conflicts.csv.
Writes OUT_DIR/data/system3d.geojson (tracks with z, UTM 16N), OUT_DIR/data/platforms3d.csv and
OUT_DIR/data/conflicts.csv, and prints the coverage.
"""
import csv, json, math, os, re, sys
import numpy as np
import shapely
from shapely.geometry import LineString, Point
from pyproj import Transformer

DECK, PROF, PFILES, DFILES, OUT = sys.argv[1:6]
MATCH_M, GAP_M = 30.0, 2000.0
D = json.load(open(DECK)); PR = json.load(open(PROF))['lines']
TR = json.load(open(os.path.join(DFILES, 'tracks.json'))); CX = json.load(open(os.path.join(DFILES, 'context.json')))
NW = json.load(open(os.path.join(DFILES, 'norwood.json')))
T = Transformer.from_crs(4326, 32616, always_xy=True)
os.makedirs(os.path.join(OUT, 'data'), exist_ok=True)

# ---------------------------------------------------------------- Profiles lines in UTM
PL = {}
for lid, r in PR.items():
    fp = os.path.join(PFILES, ('rer/lines/' if lid.startswith('RER_') else 'lines/') + lid + '.json')
    path = json.load(open(fp))['path']
    xy = np.array([T.transform(lon, lat) for _, lon, lat in path]); cs = np.array([c for c, _, _ in path])
    s = np.array(r['samples'], dtype=object)
    PL[lid] = dict(line=LineString(xy), cpath=cs, sc=np.array([float(v) for v in s[:, 0]]), sz=np.array([float(v) for v in s[:, 1]]),
                   st=[v for v in s[:, 2]], saved=r['saved'])


def prof_level(lid, pts):
    """chainage, level, type, distance for points on Profiles line lid (chainage from the path's own c values)."""
    P = PL[lid]; L = P['line']; g = shapely.points(pts)
    d = shapely.distance(L, g); s = shapely.line_locate_point(L, g)
    seg = np.r_[0, np.cumsum(np.hypot(*np.diff(np.asarray(L.coords), axis=0).T))]
    c = np.interp(s, seg, P['cpath'])                               # path length to the path's chainage
    z = np.interp(c, P['sc'], P['sz']); i = np.clip(np.searchsorted(P['sc'], c), 0, len(P['sc']) - 1)
    return c, z, [P['st'][k] for k in i], d


LETTER = {'A': 'RER_1', 'B': 'RER_2', 'C': 'RER_3', 'D': 'RER_4', 'E': 'RER_5'}


def prof_ids(t):
    if t['sys'] == 'cvx': return ['CVG_Express']
    if t['sys'] == 'metro':
        m = re.search(r'Line (\d+b?)', t['name'] or ''); return ['Line_' + m.group(1)] if m else []
    return [LETTER[x] for x in re.findall(r'\b([A-E])\b', (t['name'] or '').replace('RER', '').replace('/', ' '))]


# ---------------------------------------------------------------- the Deck's own level marks, by group
num = lambda s: [float(x) for x in re.findall(r'(\d{3}\.\d{1,2}) m', s)]
MK = {}
for f in TR['features']:
    p = f['properties']
    if p.get('layer') == 'marker' and f['geometry']['type'] == 'Point': MK[p['name']] = (f['geometry']['coordinates'], p)
RM = [(m['p'], m['label']) for m in CX['rer_marks']]


def rm(prefix):
    for p, l in RM:
        if l.startswith(prefix): return p, l
    raise KeyError(prefix)


def mk(name, z=None, idx=0):
    (x, y), p = MK[name]; return (x, y, z if z is not None else (p.get('rail') or num((p.get('label') or '') + ' ' + name)[idx]), 'tracks.json mark: ' + name)


# street crossings of the APEx viaduct (summary apex_levels, Ben's deck + 6.5 m), placed on the deck streets
APEX_LV = TR['summary']['apex_levels']; STREET_XY = {'Gest': (712785, 4331547), 'Alfred': (712736, 4333983), 'Straight': (712752, 4334173)}
FIELD = TR['summary']['apex_cut']; LOW = TR['summary']['lower_rail']; DV = TR['summary']['dive']
n_sher = DV['portal'] - (DV['z1'] - DV['z_sherman']) / (DV['g'] / 100)          # 2.72% from the portal to Sherman (146.0 m)
n_plat = n_sher - (DV['z_sherman'] - LOW) / (DV['g_tun'] / 100)                 # then 0.5% to the lower platforms
trunk_north = [mk('Viaduct over Marshall'), mk('deck tip: viaduct 166.6 m, 0.28% down to Ludlow'), mk('Ludlow'),
               (712864, 4337054, 162.5, 'north viaduct end (s 5,570), held at the Ludlow level'), mk('trunk fill ends')]
G = {
    'apex': [mk('Viaduct over W 6th'), mk('Viaduct over W 8th'), (712783, 4331400, FIELD, 'CUT platform level (throat)'),
             (712783, 4331646, FIELD, 'CUT platforms'), (712783, 4332134, FIELD, 'CUT platforms'), mk('Viaduct over W Liberty'),
             (712762, 4332842, round(APEX_LV['W Liberty'] + (4332842 - 4332357) / (4333983 - 4332357) * (APEX_LV['Alfred'] - APEX_LV['W Liberty']), 2),
              'between W Liberty and Alfred, linear (deck + 6.5 m along the deck)'),
             (*STREET_XY['Alfred'], APEX_LV['Alfred'], 'apex_levels Alfred'), (*STREET_XY['Straight'], APEX_LV['Straight'], 'apex_levels Straight'),
             (712760, 4332400, round(APEX_LV['W Liberty'] + (4332400 - 4332357) / (4333983 - 4332357) * (APEX_LV['Alfred'] - APEX_LV['W Liberty']), 2), 'north throat end, between W Liberty and Alfred, linear')]
            + trunk_north + [mk('Norwood trench'), (720190, 4337955, 185.5, 'Norwood Central platforms, 185.5 m (Ben: roofs at street level, 28 October)'),
             mk('APEx bridge', 164.0), mk('Ludlow: APEx up from the bank'), mk('APEx tunnel portal'), mk('APEx under the CS line'),
             mk('Three levels', idx=1)],
    'indy': [(712752, 4332842, round(APEX_LV['W Liberty'] + (4332842 - 4332357) / (4333983 - 4332357) * (APEX_LV['Alfred'] - APEX_LV['W Liberty']), 2), 'between W Liberty and Alfred, linear'),
             (*STREET_XY['Alfred'], APEX_LV['Alfred'], 'apex_levels Alfred'), mk('Viaduct over Marshall'), (712249, 4335328, None, 'leaves the viaduct level, 2.5% up'),
             (712267, 4335609, 173.2, 'Indianapolis + D 173.2 m at s 3,928'), (*rm('under RER D')[0], 174.3, 'the Indianapolis + D deck at 174.3 m over RER A'), (710304, 4337022, 174.3, '174.3 m from s 3,971, held to the window edge')],
    'lower_north': [(712760, 4332042, LOW, 'lower platforms, north end'), (712760, n_sher, DV['z_sherman'], 'dive: Sherman'),
                    (712760, DV['portal'], DV['z1'], 'dive: portals under Findlay'), (712760, DV['n0'], DV['z0'], 'dive: over Bank')] + trunk_north,
    'lower_level': [(712783, 4331738, LOW, 'lower platforms'), (712783, 4332042, LOW, 'lower platforms'), (712783, 4332400, round(LOW + (4332400 - n_plat) * DV['g_tun'] / 100, 2), 'north fans, on the 0.5% to Sherman')],
    'cvg': [(712838, 4331646, FIELD, 'platform M at the APEx level'), (712838, 4332134, FIELD, 'platform M at the APEx level'),
            mk('Viaduct over W 8th'), mk('Viaduct over W 6th')],
    'r5': [mk('R5 leaves the west pair'), (711705, 4336560, 167.0, 'South Cumminsville, 167.0 m'), (711716, 4336972, 167.0, 'South Cumminsville, 167.0 m')],
    'bd': [(*rm('B/D twin bores')[0], 151.64, 'Straight box 151.64 m'), (*rm('B/D 3.3% up')[0], 151.64, 'box end s 2,556, 151.64 m'),
           (*rm('Camp Washington (B, D)')[0], 165.2, 'Camp Washington on the viaduct 165.2 m'), (712300, 4334892, 165.2, 'B/D split north of Camp Washington, viaduct level'),
           (*rm('Arlington (B)')[0], 165.9, 'Arlington 165.9 m'),
           (*rm('B over Ludlow')[0], 162.5, 'B over Ludlow 162.5 m'), (*rm('Northside / Spring Grove (B)')[0], 162.5, 'Northside / Spring Grove 162.5 m'),
           mk('trunk fill ends')],
    'rer_a_west': [(712783, 4331880, 135.9, 'TRI A at or below 135.9 m under the lower level (10l.26, 10z.4)'),
                   (*rm('Evans, rail')[0], 147.5, 'Evans 147.5 m'), (*rm('leaves the deck')[0], 148.4, 'leaves the deck 148.4 m'),
                   (*rm('fork, rail')[0], 159.3, 'fork 159.3 m'), (*rm('Westwood, platform')[0], 168.9, 'Westwood platform 168.9 m'),
                   (*rm('over Hopple')[0], 168.2, 'over Hopple 168.2 m'), (*rm('under RER D')[0], 167.0, 'under RER D 167.0 m'),
                   (*rm('South Cumminsville, 167.0')[0], 167.0, 'South Cumminsville 167.0 m'), (*rm('Linden over the box')[0], 144.2, 'Linden 144.2 m')],
}
# the 'leaves the viaduct' point takes the trunk level there (Marshall to the deck tip, linear)
(mx, my, mz, _), (tx, ty, tz, _) = G['apex'][G['apex'].index(mk('Viaduct over Marshall'))], mk('deck tip: viaduct 166.6 m, 0.28% down to Ludlow')
k = (4335328 - my) / (ty - my); G['indy'][1] = (712249, 4335328, round(mz + k * (tz - mz), 2), G['indy'][1][3] + ' (trunk level there, interpolated)')
# The Deck's marks are the current CUT and north-trunk design (arch viaduct basis, 10l.19 to the North Viaduct Plan of 26 October);
# the Profiles page still holds the older CUT basis (track level 154.0 m, TRI at 142.0 m) and older TRI B, D and A west routes.
# For these groups the Deck's level wins where it has one, and the difference is listed in conflicts.csv for the Profiles page.
DECK_FIRST = {'bd', 'd_upper', 'rer_a_west', 'cvg'}
TOL = {'cvg': 40, 'apex': 120, 'indy': 60, 'lower_north': 120, 'lower_level': 60, 'r5': 60, 'bd': 90, 'rer_a_west': 90}


def group_of(name, sys_, line, pid):
    n = name or ''
    if sys_ == 'apex_tr':
        if 'CVG' in n: return 'cvg'
        if 'north approach 1 of 6' in n or 'north approach 2 of 6' in n or 'Cardinal, Floridian' in n: return 'indy'
        return 'apex'
    if sys_ == 'lower_tr':
        if n.startswith('Lower-level pair'): return 'lower_north'
        if n.startswith('Lower track') or n.startswith('Lower north fan'): return 'lower_level'
        if n.startswith('R5'): return 'r5'
        if n.startswith('Intercity pair'): return 'intercity'
        if n.startswith('C&O pair'): return 'co'
        return None
    if sys_ == 'rer':
        if pid in ('R-BD-712316-4334957', 'R-B-712689-4336858', 'R-B-715612-4338596'): return 'bd'
        if pid == 'R-D-710306-4337028': return 'd_upper'
        if pid in ('R-A-712835-4331872', 'R-A-712364-4333117'): return 'rer_a_west'
    return None


def deck_level(xy, group):
    """levels from the group's marks along one track: projected marks, linear between them, no extrapolation."""
    n = len(xy); z = np.full(n, np.nan); src = [None] * n
    if group in ('intercity', 'co'):
        pr = np.array(TR['summary']['prof'][group]['c']); L = LineString(pr[:, :2]); g = shapely.points(xy)
        d = shapely.distance(L, g); s = shapely.line_locate_point(L, g); seg = np.r_[0, np.cumsum(np.hypot(*np.diff(pr[:, :2], axis=0).T))]
        ok = d < 15; z[ok] = np.interp(s[ok], seg, pr[:, 2])
        for i in np.where(ok)[0]: src[i] = 'tracks.json summary.prof.' + group
        if group == 'intercity' or group == 'co':                     # the pair starts at the lower level
            pass
        return z, src
    if group == 'd_upper':                                          # D: 165.2 at the split, 2.5% to 174.3 m (s 3,250 to 3,602), then level
        L = LineString(xy); s = shapely.line_locate_point(L, shapely.points(xy))
        if math.hypot(xy[0][0] - 712300, xy[0][1] - 4334892) > math.hypot(xy[-1][0] - 712300, xy[-1][1] - 4334892): s = L.length - s   # measured from the split
        z = np.interp(s, [0, 352, L.length], [165.2, 174.3, 174.3]); return z, ['context rer_marks: D 2.5% from s 3,250, 174.3 m from s 3,602'] * n
    marks = G.get(group)
    if not marks: return z, src
    L = LineString(xy); seg = np.r_[0, np.cumsum(np.hypot(*np.diff(np.asarray(xy), axis=0).T))]
    ctl = []
    for (x, y, zz, note) in marks:
        if zz is None: continue
        q = Point(x, y)
        if L.distance(q) <= TOL[group]: ctl.append((L.project(q), zz, note))
    ctl.sort()
    if len(ctl) < 1: return z, src
    if len(ctl) == 1:                                                # one mark: hold it 60 m either way
        s0, z0, nt = ctl[0]; m = np.abs(seg - s0) <= 60; z[m] = z0
        for i in np.where(m)[0]: src[i] = nt
        return z, src
    cs = np.array([c[0] for c in ctl]); zs = np.array([c[1] for c in ctl])
    for i, s in enumerate(seg):
        if s < cs[0] - 5 or s > cs[-1] + 5: continue
        j = min(max(np.searchsorted(cs, s), 1), len(cs) - 1)
        if cs[j] - cs[j - 1] > GAP_M: continue
        z[i] = np.interp(s, cs, zs); src[i] = ctl[j - 1][2] + ' / ' + ctl[j][2]
    return z, src


# ---------------------------------------------------------------- every track
tracks = []
for t in D['all_tracks']:
    tracks.append(dict(name=t['line'], sys=t['sys'], pid=t['pid'], from_=t['from'], xy=np.array(t['c'], float), kind='deck_line'))
for f in TR['features']:
    p, g = f['properties'], f['geometry']
    if g['type'] != 'LineString' or p.get('layer') not in ('apex', 'lower', 'passing'): continue
    if p.get('kind') in ('cvg_former',): continue
    tracks.append(dict(name=p.get('name'), sys='apex_tr' if p['layer'] != 'lower' else 'lower_tr', pid=None, from_='tracks.json', xy=np.array(g['coordinates'], float), kind=p.get('kind') or ''))
for f in NW['features']:
    p, g = f['properties'], f['geometry']
    if p.get('layer') == 'nw_track': tracks.append(dict(name='Norwood ' + p['track'], sys='nw_' + p['sys'], pid=None, from_='norwood.json', xy=np.array(g['coordinates'], float), kind='tunnel' if p.get('tunnel') else ''))

def densify(xy, step=10.0):
    out = [xy[0]]
    for a_, b_ in zip(xy[:-1], xy[1:]):
        k = max(1, int(math.ceil(math.hypot(*(b_ - a_)) / step)))
        out += [a_ + (b_ - a_) * j / k for j in range(1, k + 1)]
    return np.array(out)


for t in tracks:
    if len(t['xy']) > 1: t['xy'] = densify(t['xy'])
conflicts, feats, cover = [], [], {}
for t in tracks:
    xy = t['xy']; n = len(xy); z = np.full(n, np.nan); zsrc = [None] * n; ztype = [None] * n
    ids = prof_ids(t) if t['sys'] in ('metro', 'rer', 'cvx') else (['CVG_Express'] if t['sys'] == 'apex_tr' and 'CVG' in (t['name'] or '') else [])
    best = None
    for lid in ids:                                                  # the Profiles line it runs on; with shared tracks, the nearest
        if lid not in PL: continue
        c, zz, ty, d = prof_level(lid, xy); ok = d <= MATCH_M
        if best is None or ok.sum() > best[4].sum(): best = (lid, c, zz, ty, ok)
        t.setdefault('alt', []).append((lid, c, zz, ok))
    if best is not None:
        lid, c, zz, ty, ok = best
        z[ok] = zz[ok]
        for i in np.where(ok)[0]: zsrc[i] = 'profiles:' + lid; ztype[i] = ty[i]
        for lid2, c2, zz2, ok2 in t.get('alt', []):                   # interlining: two Profiles lines on one Deck pair
            if lid2 == lid: continue
            both = ok & ok2
            if both.sum() > 3:
                dz = np.abs(zz[both] - zz2[both]); k = int(np.argmax(dz))
                conflicts.append(dict(kind='shared track, two Profiles lines', track=t['name'], where_E=round(xy[both][k][0]), where_N=round(xy[both][k][1]),
                                      a=lid, z_a=round(float(zz[both][k]), 2), b=lid2, z_b=round(float(zz2[both][k]), 2), dz=round(float(dz[k]), 2),
                                      note='largest of %d shared points; median %.2f m, 95th percentile %.2f m' % (both.sum(), float(np.median(dz)), float(np.percentile(dz, 95)))))
    grp = 'nw' if t['sys'].startswith('nw_') else group_of(t['name'], t['sys'], t['name'], t['pid'])
    if grp == 'nw':
        if t['kind'] != 'tunnel':
            z[:] = np.where(np.isnan(z), 185.5, z); zsrc = [s or 'Norwood Central 185.5 m (Ben, 28 October)' for s in zsrc]
    elif grp:
        dz_, ds_ = deck_level(xy, grp)
        both = ~np.isnan(z) & ~np.isnan(dz_)
        if both.sum() > 3:
            dd = np.abs(z[both] - dz_[both]); k = int(np.argmax(dd))
            if dd[k] > 1.0:
                conflicts.append(dict(kind='Profiles against the Deck marks' + (' (Deck used)' if grp in DECK_FIRST else ' (Profiles used)'), track=t['name'], where_E=round(xy[both][k][0]), where_N=round(xy[both][k][1]),
                                      a=best[0] if best else '', z_a=round(float(z[both][k]), 2), b='deck:' + grp, z_b=round(float(dz_[both][k]), 2), dz=round(float(dd[k]), 2),
                                      note='largest of %d points; median %.2f m; %s' % (both.sum(), float(np.median(dd)), ds_[np.where(both)[0][k]])))
        m = (~np.isnan(dz_)) if grp in DECK_FIRST else (np.isnan(z) & ~np.isnan(dz_)); z[m] = dz_[m]
        for i in np.where(m)[0]: zsrc[i] = 'deck:' + grp + ': ' + (ds_[i] or '')
    t['z'] = z; t['zsrc'] = zsrc; t['ztype'] = ztype

# TRI stretches still without a level (routes the Profiles page draws differently): its station levels as anchors,
# placed at the Deck's platform centres, joined to the levels already on the track; no extrapolation, gaps over GAP_M left open
PSTA = {}
for lid in PL:
    fp = os.path.join(PFILES, ('rer/lines/' if lid.startswith('RER_') else 'lines/') + lid + '.json')
    PSTA[lid] = {st['name']: float(np.interp(st['c'], PL[lid]['sc'], PL[lid]['sz'])) for st in json.load(open(fp))['stations']}
for t in tracks:
    if t['sys'] != 'rer' or not np.isnan(t['z']).any(): continue
    lids = [l for l in prof_ids(t) if l in PL]
    if not lids: continue
    anchors = []
    for s_ in D['stations']:
        if s_['deleted'] or s_['sys'] != 'rer': continue
        for o in s_['stops']:
            if o['pid'] != t['pid']: continue
            for lid in lids:
                if s_['name'] in PSTA[lid]: anchors.append(((o.get('centre') or [s_['E'], s_['N']]), PSTA[lid][s_['name']], 'profiles station %s %s' % (lid, s_['name']))); break
    if not anchors: continue
    xy, z = t['xy'], t['z']; L = LineString(xy); seg = np.r_[0, np.cumsum(np.hypot(*np.diff(xy, axis=0).T))]
    ctl = [(seg[i], z[i], t['zsrc'][i]) for i in range(0, len(xy), 5) if not np.isnan(z[i])]
    for q, zz, nt in anchors:
        if L.distance(Point(q)) <= 60: ctl.append((L.project(Point(q)), zz, nt))
    ctl.sort(key=lambda c: c[0])
    if len(ctl) < 2: continue
    cs = np.array([c[0] for c in ctl]); zs = np.array([c[1] for c in ctl])
    for i in np.where(np.isnan(z))[0]:
        if seg[i] < cs[0] or seg[i] > cs[-1]: continue
        j = min(max(np.searchsorted(cs, seg[i]), 1), len(cs) - 1)
        if cs[j] - cs[j - 1] > GAP_M or not any('station' in str(ctl[k][2]) for k in (j - 1, j)): continue
        z[i] = np.interp(seg[i], cs, zs); t['zsrc'][i] = 'anchored: ' + str(ctl[j - 1][2]) + ' / ' + str(ctl[j][2])

for t in tracks:
    xy, z, zsrc, ztype, n = t['xy'], t['z'], t['zsrc'], t['ztype'], len(t['xy'])
    L = float(np.sum(np.hypot(*np.diff(xy, axis=0).T))) if n > 1 else 0.0
    have = float(np.sum(~np.isnan(z))) / max(n, 1)
    key = t['sys'] + ' | ' + (t['name'] or '')
    cv = cover.setdefault(key, [0.0, 0.0]); cv[0] += L; cv[1] += L * have
    feats.append({'type': 'Feature', 'properties': {'name': t['name'], 'sys': t['sys'], 'pid': t['pid'], 'source_plan': t['from_'],
                  'level_sources': sorted(set((s_ or 'none').split(':')[0] for s_ in zsrc)),
                  'types': [ty for ty in ztype], 'share_with_level': round(have, 3)},
                  'geometry': {'type': 'LineString', 'coordinates': [[round(a, 1), round(b, 1), (round(float(c), 2) if not np.isnan(c) else None)] for (a, b), c in zip(xy, z)]}})

json.dump({'type': 'FeatureCollection', 'name': 'system3d', 'crs': {'type': 'name', 'properties': {'name': 'urn:ogc:def:crs:EPSG::32616'}},
           'note': 'x, y from the Mill Creek Deck (plus tracks.json and norwood.json); z = rail level in metres NAVD88 from the Rail Profiles page where the track lies within %d m of its Profiles line, else from the Deck level marks; null where neither gives one.' % MATCH_M,
           'features': feats}, open(os.path.join(OUT, 'data', 'system3d.geojson'), 'w'))

# platforms: rail level at the platform centre, from the nearest track of the same line
rows = []
for s in D['stations']:
    if s['deleted']: continue
    for o in s['stops']:
        if not o.get('centre'): continue
        q = np.array(o['centre']); best = (1e9, None, None)
        for t in tracks:
            if t['pid'] != o['pid'] or not len(t['xy']): continue
            dd = np.hypot(*(t['xy'] - q).T); i = int(np.argmin(dd))
            if dd[i] < best[0]: best = (dd[i], t['z'][i], t['zsrc'][i])
        rows.append(dict(system=s['sys'], station=s['name'], line=o['line'], type=o['type'], centre_E=o['centre'][0], centre_N=o['centre'][1],
                         rail_m='' if best[1] is None or np.isnan(best[1]) else round(float(best[1]), 2), level_source=best[2] or ''))
with open(os.path.join(OUT, 'data', 'platforms3d.csv'), 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
with open(os.path.join(OUT, 'data', 'conflicts.csv'), 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=['kind', 'track', 'where_E', 'where_N', 'a', 'z_a', 'b', 'z_b', 'dz', 'note']); w.writeheader(); w.writerows(conflicts)
json.dump({k: [round(v[0]), round(v[1])] for k, v in sorted(cover.items())}, open(os.path.join(OUT, 'data', 'coverage.json'), 'w'), indent=0)
tot = sum(v[0] for v in cover.values()); got = sum(v[1] for v in cover.values())
print('tracks', len(tracks), 'length %.0f km, with a level %.0f km (%.0f%%)' % (tot / 1000, got / 1000, 100 * got / tot), 'conflicts', len(conflicts))
import pickle; pickle.dump(tracks, open(os.path.join(OUT, 'data', '_tracks3d.pkl'), 'wb'))
