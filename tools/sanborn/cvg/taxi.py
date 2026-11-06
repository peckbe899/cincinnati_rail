try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Ben (17 October): taxiways and aprons for CVG from his CVG_Layout.tif (the FAA airport diagram, January 2020, georeferenced, 4 m pixels).
# The grey pavement is taken off the diagram (text and the black runways closed over), turned to UTM 16N, and cut where the canon runways
# (longer than on the diagram) run; the parallel taxiways are carried on along the lengthened runways at the diagram's own offsets.
import numpy as np, json, math
from PIL import Image
from pyproj import Transformer
from scipy import ndimage as nd
from skimage import measure, morphology
from shapely.geometry import Polygon, MultiPolygon, LineString, Point, shape, mapping, box
from shapely.ops import unary_union, transform as stransform
S = _ws.DATA
im = Image.open(S + 'cvgkmz/cvg_layout.tif'); tg = im.tag_v2; a = np.array(im)[..., :3].astype(int)
x0, y0, px = tg[33922][3], tg[33922][4], tg[33550][0]
g = a.mean(2)
grey = (g > 190) & (g < 225) & (np.ptp(a, axis=2) < 12)
blk = g < 60
# the pavement: grey, plus black marks inside it (letters, centre dots) when small; runways (long black bars) are kept apart
lab, n = nd.label(blk); sz = nd.sum(blk, lab, range(1, n + 1)); small = np.isin(lab, 1 + np.where(sz < 600)[0])
pav = grey | (small & nd.binary_dilation(grey, iterations=3))
pav = morphology.closing(pav, morphology.disk(2)); pav = morphology.opening(pav, morphology.disk(1))
pav = morphology.remove_small_objects(pav, max_size=300)
# drop the legend boxes and margins: keep pavement inside the airfield frame
H, W = pav.shape; frame = np.zeros_like(pav); frame[int(H * 0.17):int(H * 0.86), int(W * 0.12):int(W * 0.97)] = True; pav &= frame
t = Transformer.from_crs(3857, 26916, always_xy=True)
outs, holes = [], []
for c in measure.find_contours(np.pad(pav, 1).astype(float), 0.5):
    if len(c) < 6: continue
    X, Y = t.transform(x0 + (c[:, 1] - 1) * px, y0 - (c[:, 0] - 1) * px)
    xy = np.c_[X, Y]; sa = 0.5 * np.sum(xy[:-1, 0] * xy[1:, 1] - xy[1:, 0] * xy[:-1, 1])
    p = Polygon(xy).buffer(0)
    if p.area < 100: continue
    (outs if sa > 0 else holes).append(p)
if sum(p.area for p in holes) > sum(p.area for p in outs): outs, holes = holes, outs   # find_contours' orientation: the outer rings are the larger set
PAV = unary_union(outs).difference(unary_union(holes)).simplify(1.5)
A = json.load(open(S + 'deckpage/airport.json'))
RW = unary_union([shape(f['geometry']) for f in A['features'] if f['properties']['layer'] == 'cvg_runway'])
BL = unary_union([shape(f['geometry']) for f in A['features'] if f['properties']['layer'] == 'cvg_building'])
PAV = PAV.difference(RW.buffer(1)).difference(BL)
PAV = unary_union([q for q in getattr(PAV, 'geoms', [PAV]) if q.area > 3000])   # drops the specks left by the diagram's lettering
# carry the parallel taxiways along the lengthened runways (diagram runway ends read off the black bars)
CL = {f['properties']['name']: f['geometry']['coordinates'] for f in A['features'] if f['properties']['layer'] == 'cvg_runway_cl'}
ext = []; log = {}
PB = PAV.buffer(0)
REAL = {'Runway 18R/36L': 2438.4, 'Runway 18L/36R': 3048.0, 'Runway 18C/36C': 3352.8, 'Runway 9L/27R': 3657.6}   # diagram lengths (8,000, 10,000, 11,000, 12,000 ft)
for nm, c in CL.items():
    a_, b_ = np.array(c[0]), np.array(c[1]); L = np.linalg.norm(b_ - a_); u = (b_ - a_) / L; nrm = np.array([-u[1], u[0]]); log[nm] = dict(canon_m=round(L), diagram_m=REAL.get(nm))
    if nm not in REAL or L - REAL[nm] < 50: continue          # only the lengthened runways get their parallel carried on
    for side in (1, -1):
        # the parallel taxiway: the nearest pavement band 80-260 m off, read along the runway
        offs_ = []
        for s_ in np.arange(0, L, 25.0):
            o = next((off for off in range(80, 262, 3) if PB.contains(Point(*(a_ + u * s_ + nrm * side * off)))), None); offs_.append(o)
        good = [o for o in offs_ if o is not None]
        if len(good) < 0.4 * len(offs_): continue
        off = float(np.median(good)); on = [o is not None and abs(o - off) < 15 for o in offs_]
        if sum(on) < 0.4 * len(on): continue
        k0 = on.index(True); k1 = len(on) - 1 - on[::-1].index(True)
        sa, sb = k0 * 25.0, k1 * 25.0
        for (e0, e1, endpt) in ((0.0, sa, 0.0), (sb, L, L)):
            if e1 - e0 < 60: continue
            ext.append(LineString([a_ + u * e0 + nrm * side * off, a_ + u * e1 + nrm * side * off]).buffer(11.5, cap_style=2))
            ext.append(LineString([a_ + u * endpt + nrm * side * off, a_ + u * endpt]).buffer(11.5, cap_style=2))      # entry at the new runway end
            log[nm].setdefault('extended', []).append([round(e1 - e0), 'left' if side > 0 else 'right', round(off)])
EXT = unary_union(ext).difference(RW.buffer(1)) if ext else Polygon()
feats = []
def addf(layer, g, **p):
    for q in getattr(g, 'geoms', [g]):
        if q.geom_type == 'Polygon' and q.area > 200: feats.append(dict(type='Feature', properties=dict(layer=layer, **p), geometry=json.loads(json.dumps(mapping(q.simplify(0.5)), default=float))))
addf('cvg_taxi', PAV, src='FAA airport diagram, January 2020 (Ben’s CVG_Layout.tif), grey pavement: taxiways and aprons', name='Taxiways and aprons')
addf('cvg_taxi', EXT, src='carried along the lengthened runway at the diagram’s parallel-taxiway offset (drawing value)', name='Taxiway along the runway extension', ext=True)
A['features'] = [f for f in A['features'] if f['properties']['layer'] != 'cvg_taxi'] + feats
A['taxi_log'] = log
json.dump(A, open(S + 'deckpage/airport.json', 'w'))
print(len(feats), round(PAV.area), json.dumps(log))
