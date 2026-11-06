# Norwood Central for the deck page (Ben, 23 October: put the station in, not the Line 3 station). Surface layout of sketch v10
# (norwood/sk9.py) -> deckpage/norwood.json: tracks, platforms, the station building, level -1 passages, Ben's track area, labels.
# Metro 4 and 14 and TRI A and E are drawn by the page's Metro and RER layers (moved by rer1023/norwood_pass.py).
import json, numpy as np, sys
sys.argv = ['x']; exec(open('norwood/sk10.py').read().split('# ---------- drawing ----------')[0])   # v11 throats (24 October)
OUT = []
def r2(pts): return [[round(float(x), 2), round(float(y), 2)] for x, y in pts]
def line(layer, pts, **p): OUT.append(dict(type='Feature', properties=dict(layer=layer, **p), geometry=dict(type='LineString', coordinates=r2(pts))))
def poly(layer, pts, **p): pts = list(pts); OUT.append(dict(type='Feature', properties=dict(layer=layer, **p), geometry=dict(type='Polygon', coordinates=[r2(pts + [pts[0]])])))
def pt(layer, p_, **p): OUT.append(dict(type='Feature', properties=dict(layer=layer, **p), geometry=dict(type='Point', coordinates=[round(float(p_[0]), 2), round(float(p_[1]), 2)])))
def R(s0, s1, o0, o1): return [P(s0, o0), P(s1, o0), P(s1, o1), P(s0, o1)]
poly('nw_area', list(A.exterior.coords)[:-1], name='Station track area (Ben, 23 October; superseded by his street ends, 24 October)', hide=True)
names = {'T6': 'APEx through track (south)', 'T7': 'APEx through track (north)', 'T5': 'APEx platform track (south)', 'T8': 'APEx platform track (north)',
         'T4': 'ORR T4 (X1 / L75 island, north face)', 'T3': 'ORR T3 (X1 / L75 island, south face)', 'T2': 'ORR T2 (Oakley island, north face)', 'T1': 'ORR T1 (Oakley island, south face)',
         'B1': 'Bay B1 (west-facing)', 'B2': 'Bay B2 (west-facing)', 'T9': 'Transvalley T9', 'T10': 'Transvalley T10'}
for k, (kn, s0, s1, col, par) in TR.items():
    sysn = 'apex' if k in ('T5', 'T6', 'T7', 'T8') else 'tv' if k in ('T9', 'T10') else 'bay' if k in ('B1', 'B2') else 'orr'
    line('nw_track', [P(s, ease(kn, s)) for s in np.arange(s0, s1 + 1, 4)], sys=sysn, name=names[k], track=k)
for nm_, W_ in (('W1', W1), ('W2', W2)):                         # v13: underground north of the station (dashed), wide each side of TRI A to the meet point
    k_ = W_[:, 1] <= 60; i_ = int(np.argmin(k_)) if not k_.all() else len(W_)
    line('nw_track', [P(a, b) for a, b in W_[:i_ + 1][::2]], sys='tv', name=f'Transvalley, Waynesville {nm_}', track=nm_)
    if i_ < len(W_): line('nw_track', [P(a, b) for a, b in W_[i_:][::2]], sys='tv', tunnel=True, name=f'Transvalley, Waynesville {nm_} (underground, climbing towards Norwood; one track each side of TRI A)', track=nm_)
pt('nw_lab', P(*MEET), text='TRI/TV meet')
pt('nw_mark', P(*MEET), name='TRI/TV meet (Ben, 24 October)', note='north of here the Transvalley runs with TRI A under the streets; south of it TRI A goes deeper to its box and the Transvalley climbs to Norwood, straddling it')
AP = 'Heritage 1,000 ft island, rebuilt as a side platform with through tracks between and extended to 1,600 ft (350 ft west, 250 ft east); screen doors'
poly('nw_plat', R(APW0, APW1, -8.93, -17.23), sys='apex', name='APEx platform, south (tracks T5 / T6 through)', label='APEx S', length_m=488.0, note=AP)
poly('nw_plat', R(APW0, APW1, 8.93, 17.23), sys='apex', name='APEx platform, north (tracks T8 / T7 through)', label='APEx N', length_m=488.0, note=AP)
poly('nw_plat', R(H0, H1, -20.91, -29.23), sys='orr', name='ORR Norwood island (X1, L75), tracks T4 / T3', label='ORR 3-4', length_m=305.0, note='heritage 1,000 ft island')
poly('nw_plat', R(H0, H1, -37.09, -45.41), sys='orr', name='ORR Norwood-Oakley Jct island (R1-R3, L71), tracks T2 / T1', label='ORR 1-2', length_m=305.0, note='heritage 1,000 ft island')
poly('nw_plat', R(H0, H1, -53.27, -61.59), sys='bay', name='Heritage bay island (west-facing), bays B1 / B2', label='Bays', length_m=305.0, note='heritage 1,000 ft island, buffers at the east end')
poly('nw_plat', R(H0, H1, 20.91, 29.23), sys='tv', name='Transvalley island, tracks T9 / T10', label='TV', length_m=305.0,
     note='heritage 1,000 ft island. Norwood-Hamilton terminates from the east and can use any non-APEx face; Cincinnati-Waynesville via Lebanon runs through, out the prong')
FE = json.load(open('norwood/floral_edge.json'))['floral_north']          # Floral Avenue's north edge at s 4,636 / 4,697 / 4,758
CC, CW = 4697.5, 30.0                                                  # elevated concourse: centred on the heritage platforms (4,545-4,850); width a drawing value
def fe(s_): return float(np.interp(s_, [4636, 4697, 4758], FE))
B0, B1 = CC - 61.0, CC + 61.0
poly('nw_bldg', [P(B0, fe(B0)), P(B1, fe(B1)), P(B1, fe(B1) + 45.72), P(B0, fe(B0) + 45.72)], name='Norwood Central station building',
     note='about 400 x 150 ft (122 x 46 m), front on Floral Avenue, centred on the concourse (Ben, 24 October); entrance to the concourse slightly sloped up, as at Union Terminal')
from shapely.geometry import LineString as _LS
_ir = _LS(json.load(open('nwring/ring_utm.json'))['coords']).buffer(22.86, cap_style=2)
def ring_s_edge(s_):
    x = _LS([P(s_, 0), P(s_, 300)]).intersection(_ir); return min(float((np.asarray(c) - O) @ n) for g in getattr(x, 'geoms', [x]) for c in g.coords)
poly('nw_conc', [P(CC - CW / 2, fe(CC - CW / 2) + 45.72), P(CC + CW / 2, fe(CC + CW / 2) + 45.72), P(CC + CW / 2, ring_s_edge(CC + CW / 2)), P(CC - CW / 2, ring_s_edge(CC - CW / 2))],
     name='Elevated concourse (above the platform roofs)', note='from the station building over every track to the Inner Ring on the north side (Baltimore Penn rather than New Haven); width 30 m is a drawing value')
poly('nw_pass', R(4452, 5045, -6, 6), name='Level -1: passage, Metro 4 to TRI A', note='under the platforms along the station axis, above TRI E; lifts and stairs up to the concourse')
pt('nw_lab', P(CC, -90), text='Norwood Central', big=True)
pt('nw_lab', P(CC, -165), text='Platforms sunken, roofs at street level; concourse above them; Montgomery on a viaduct. Below the platforms: -1 passage · -2 Metro 4 · -3 Metro 14, TRI A · -4 TRI E')
pt('nw_lab', P(4646, 52), text='Metro 3 terminus at platform level')
pt('nw_lab', P(CC, -104), text='Station building')
pt('nw_lab', P(CC, 45), text='Concourse')
json.dump(dict(type='FeatureCollection', name='norwood', note='Norwood Central, sketch v13 (24 October 2026): relaxed throats, Transvalley/Waynesville double junction, Waynesville underground straddling TRI A to the meet point, elevated concourse, building on Floral centred on it', features=OUT),
          open('deckpage/norwood.json', 'w'), separators=(',', ':'))
print('norwood.json', len(OUT), 'features')
