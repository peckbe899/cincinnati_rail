import json
from shapely.geometry import shape, box
from shapely.ops import unary_union
Y = json.load(open('deckpage/yard.json'))
lim = [shape(f['geometry']) for f in Y['features'] if f['properties']['layer']=='yard_limit'][0]
inb = unary_union([shape(f['geometry']) for f in Y['features'] if f['properties']['layer']=='ud_box' and f['properties'].get('cls')=='in'])
room = lim.difference(inb)
fans = unary_union([shape(f['geometry']) for f in Y['features'] if f['properties']['layer']=='yard_fan'])
print('limit %.1f ha, room %.1f ha, yards %.1f' % (lim.area/1e4, room.area/1e4, fans.area/1e4))
for n in range(4330800, 4336800, 400):
    b = box(711000, n, 714000, n+400)
    r = room.intersection(b); y = fans.intersection(b)
    print(n, 'room %.1f yards %.1f  width %.0f' % (r.area/1e4, y.area/1e4, r.area/400))
