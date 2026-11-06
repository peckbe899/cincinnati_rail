import sys, re, json
import xml.etree.ElementTree as ET
from pyproj import Transformer
tr = Transformer.from_crs(4326, 26916, always_xy=True)
src = sys.argv[1]; out = sys.argv[2]
ns = {'k':'http://www.opengis.net/kml/2.2'}
root = ET.parse(src).getroot()
def walk(el, path):
    for ch in el:
        tag = ch.tag.split('}')[1]
        if tag in ('Folder','Document'):
            nm = ch.find('k:name', ns)
            walk(ch, path+[nm.text if nm is not None else ''])
        elif tag == 'Placemark':
            nm = ch.find('k:name', ns); nm = nm.text if nm is not None else ''
            ds = ch.find('k:description', ns); ds = ds.text if ds is not None else ''
            for ls in ch.iter('{http://www.opengis.net/kml/2.2}LineString'):
                c = ls.find('k:coordinates', ns).text.split()
                pts = []
                for t in c:
                    v = t.split(',')
                    x, y = tr.transform(float(v[0]), float(v[1]))
                    pts.append((round(x,1), round(y,1)))
                yield_list.append(dict(path=path, name=nm, desc=(ds or '')[:300], pts=pts))
            for pt in ch.iter('{http://www.opengis.net/kml/2.2}Point'):
                v = pt.find('k:coordinates', ns).text.strip().split(',')
                x, y = tr.transform(float(v[0]), float(v[1]))
                yield_pts.append(dict(path=path, name=nm, desc=(ds or '')[:200], xy=(round(x,1), round(y,1))))
yield_list = []; yield_pts = []
walk(root, [])
X0,X1,Y0,Y1 = 706000, 722000, 4328000, 4346000
near = [l for l in yield_list if any(X0<x<X1 and Y0<y<Y1 for x,y in l['pts'])]
nearp = [p for p in yield_pts if X0<p['xy'][0]<X1 and Y0<p['xy'][1]<Y1]
print('total lines', len(yield_list), 'points', len(yield_pts), 'near lines', len(near), 'near pts', len(nearp))
from collections import Counter
print(Counter(' / '.join(l['path']) for l in yield_list).most_common(40))
for l in near:
    print('/'.join(l['path']), '|', l['name'], '|', len(l['pts']), '|', l['desc'][:120].replace('\n',' '))
json.dump(dict(lines=near, pts=nearp), open(out,'w'))
