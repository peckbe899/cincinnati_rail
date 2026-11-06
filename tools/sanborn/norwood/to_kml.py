import json, numpy as np, sys
from pyproj import Transformer
from shapely.geometry import LineString as LS, Point, Polygon
from shapely.ops import substring
sys.argv=['x']; exec(open('norwood/sk9.py').read().split('# ---------- drawing ----------')[0])
T=Transformer.from_crs(26916,4326,always_xy=True)
def ll(pts): return ' '.join('%.7f,%.7f,0'%T.transform(x,y) for x,y in pts)
styles={'apex':'ffff00ff','orr':'ff2827d6','tv':'ff8b8b00','plat_apex':'99e6a3e6','plat_orr1':'9966d9ff','plat_orr2':'9983b1f4','plat_bay':'99d9d9d9','plat_tv':'99c8c85f',
 'bldg':'cc808080','pass':'66ffd7bc','l3':'ff2ca02c','l4':'ff4b568c','l14':'ffbd6794','tria':'ff2a00d4','trie':'ffb4771f','area':'ff0000ff'}
out=['<?xml version="1.0" encoding="UTF-8"?>','<kml xmlns="http://www.opengis.net/kml/2.2"><Document><name>Norwood Central sketch v10</name>']
for k,c in styles.items():
    out.append(f'<Style id="{k}"><LineStyle><color>{c}</color><width>3</width></LineStyle><PolyStyle><color>{c}</color></PolyStyle></Style>')
def line(name,pts,st): out.append(f'<Placemark><name>{name}</name><styleUrl>#{st}</styleUrl><LineString><tessellate>1</tessellate><coordinates>{ll(pts)}</coordinates></LineString></Placemark>')
def poly(name,pts,st,desc=''):
    pts=list(pts); pts=pts+[pts[0]]
    out.append(f'<Placemark><name>{name}</name><description>{desc}</description><styleUrl>#{st}</styleUrl><Polygon><outerBoundaryIs><LinearRing><coordinates>{ll(pts)}</coordinates></LinearRing></outerBoundaryIs></Polygon></Placemark>')
def R(s0,s1,o0,o1): return [P(s0,o0),P(s1,o0),P(s1,o1),P(s0,o1)]
def folder(n): out.append(f'<Folder><name>{n}</name>')
def end(): out.append('</Folder>')
folder('Track area (Ben)'); line('Station track area',list(A.exterior.coords),'area'); end()
names={'T6':'APEx through (south)','T7':'APEx through (north)','T5':'APEx platform track (south)','T8':'APEx platform track (north)',
 'T4':'ORR T4 (X1/L75 island, north face)','T3':'ORR T3 (X1/L75 island, south face)','T2':'ORR T2 (Oakley island, north face)','T1':'ORR T1 (Oakley island, south face)',
 'B1':'Bay B1 (west-facing)','B2':'Bay B2 (west-facing)','T9':'Transvalley T9 (to Hamilton)','T10':'Transvalley T10 (to Hamilton)'}
folder('Surface tracks')
for k,(kn,s0,s1,col,par) in TR.items():
    st='apex' if k in('T5','T6','T7','T8') else 'tv' if k in('T9','T10') else 'orr'
    line(names[k],[P(s,ease(kn,s)) for s in np.arange(s0,s1+1,4)],st)
line('Waynesville W1',[P(a,b) for a,b in W1[::3]],'tv'); line('Waynesville W2',[P(a,b) for a,b in W2[::3]],'tv')
end()
folder('Surface platforms')
poly('APEx platform south (488 m, screen doors)',R(APW0,APW1,-8.93,-17.23),'plat_apex','Heritage 305 m island extended 350 ft W / 250 ft E')
poly('APEx platform north (488 m, screen doors)',R(APW0,APW1,8.93,17.23),'plat_apex','Heritage 305 m island extended 350 ft W / 250 ft E')
poly('ORR Norwood island (X1, L75)',R(H0,H1,-20.91,-29.23),'plat_orr2','305 m')
poly('ORR Norwood-Oakley Jct island (R1-R3, L71)',R(H0,H1,-37.09,-45.41),'plat_orr1','305 m')
poly('Heritage bay island (west-facing)',R(H0,H1,-53.27,-61.59),'plat_bay','305 m')
poly('Transvalley island',R(H0,H1,20.91,29.23),'plat_tv','305 m')
end()
folder('Building and passages')
poly('Station building 400 x 150 ft',R(4636,4758,-72,-117.7),'bldg')
poly('Level -1 main tunnel',R(4700,4718,-72,70),'pass')
poly('Level -1 concourse (Metro 4 to TRI A)',R(4452,5045,-6,6),'pass')
end()
dd=json.load(open('deckpage/context.json'))
def ln(k,nm,pre):
    for f in dd[k]:
        if f['name']==nm and f['id'].startswith(pre):
            c=f['c']; return LS(c if isinstance(c[0][0],(int,float)) else c[0])
def stbox(G,cp,length,w):
    m=G.project(Point(cp)); seg=substring(G,m-length/2,m+length/2); return list(seg.buffer(w/2,cap_style=2).exterior.coords)[:-1]
def q(s_,o_): return tuple(P(s_,o_))
Aline=LS(list(ln('rer','RER A','R-A-718498').coords)+list(ln('rer','RER A','R-A-720547').coords))
folder('Underground stations')
poly('Level -2 Metro L3 terminus (400 ft)',stbox(LS([q(4600,15),q(4900,15)]),q(4754,15),121.92,18),'l3')
poly('Level -2 Metro L4 terminus (400 ft)',stbox(ln('metro','Line 4','M-L4-716800'),q(4458,-64),121.92,16),'l4')
poly('Level -3 Metro L14 (400 ft)',stbox(ln('metro','Line 14','M-L14'),q(4499,-64),121.92,14),'l14')
poly('Level -3 TRI A (204 m)',stbox(Aline,q(5057,0),204.2,24),'tria')
poly('Level -4 TRI E (204 m)',stbox(LS([q(4600,1),q(5100,1)]),q(4880,1),204.2,22),'trie')
end()
out.append('</Document></kml>')
open('norwood/Norwood_Central_v10.kml','w').write('\n'.join(out)); print('ok')
