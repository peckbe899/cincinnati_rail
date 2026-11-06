import json
from shapely.geometry import shape, LineString
from shapely.ops import unary_union
Y = json.load(open('deckpage/yard.json'))
lim = [shape(f['geometry']) for f in Y['features'] if f['properties']['layer']=='yard_limit'][0]
inb = unary_union([shape(f['geometry']) for f in Y['features'] if f['properties']['layer']=='ud_box' and f['properties'].get('cls')=='in'])
room = lim.buffer(-2.5).difference(inb.buffer(2.5))
ramp = [shape(f['geometry']) for f in Y['features'] if f['properties']['layer']=='yard_lead' and 'ramp' in f['properties'].get('name','')][0]
for n in range(4333300, 4336700, 100):
    g = LineString([(711500, n), (713200, n)]).intersection(room)
    parts = [ (round(p.bounds[0]), round(p.bounds[2])) for p in getattr(g,'geoms',[g]) if p.length>5]
    r = LineString([(711500, n), (713200, n)]).intersection(ramp)
    print(n, parts, 'ramp x', round(r.x) if r.geom_type=='Point' else '-')
