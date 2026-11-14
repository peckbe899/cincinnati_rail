"""Today's block edges for a plate, from Hamilton County's public parcel map (14 November 2026).

    cd data/sanborn
    python ../../tools/sanborn/guided/parcels.py N        -> today/parcels_N.geojson, today/blocks_N.geojson

Source: CAGIS, COUNTYWIDE/Cadastral MapServer layer 0 (parcel polygons). Only geometry is asked for (no owner, address
or value fields), inside the plate's world box plus 100 m, in EPSG:26916. A block is the union of the parcels that
touch (gaps under 1 m closed); its outline is the block edge the Sanborn plate draws as the front line of the lots.
"""
import json, os, sys, urllib.parse, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import streets as S  # noqa: E402
from shapely.geometry import shape, mapping, Polygon  # noqa: E402
from shapely.ops import unary_union  # noqa: E402
URL = 'https://cagisonline.hamilton-co.org/arcgis/rest/services/COUNTYWIDE/Cadastral/MapServer/0/query'
N = sys.argv[1]; P = S.Plate(N); x0, y0, x1, y1 = P.box.buffer(100).bounds
OUT = S.SP + 'today/'; os.makedirs(OUT, exist_ok=True)
feats, off = [], 0
while True:
    q = dict(where='1=1', geometry=f'{x0},{y0},{x1},{y1}', geometryType='esriGeometryEnvelope', inSR=26916, outSR=26916,
             spatialRel='esriSpatialRelIntersects', outFields='OBJECTID', returnGeometry='true', f='geojson',
             resultOffset=off, resultRecordCount=1000, orderByFields='OBJECTID')
    r = urllib.request.Request(URL + '?' + urllib.parse.urlencode(q), headers={'User-Agent': 'Mozilla/5.0'})
    d = json.load(urllib.request.urlopen(r, timeout=120)); f = d.get('features', [])
    feats += f; off += len(f); print('fetched', off, flush=True)
    if len(f) < 1000: break
for f in feats: f['properties'] = {}
json.dump(dict(type='FeatureCollection', crs='EPSG:26916', source=URL, features=feats),
          open(OUT + f'parcels_{N}.geojson', 'w', encoding='utf8', newline='\n'))
gs = [shape(f['geometry']).buffer(0) for f in feats if f.get('geometry')]
u = unary_union([g.buffer(0.5) for g in gs]).buffer(-0.5)
blocks = [Polygon(b.exterior) for b in getattr(u, 'geoms', [u]) if b.area > 200]
json.dump(dict(type='FeatureCollection', crs='EPSG:26916', features=[dict(type='Feature', properties=dict(id=i, area=round(b.area)), geometry=mapping(b.simplify(0.2))) for i, b in enumerate(blocks)]),
          open(OUT + f'blocks_{N}.geojson', 'w', encoding='utf8', newline='\n'))
print('parcels', len(gs), 'blocks', len(blocks))
