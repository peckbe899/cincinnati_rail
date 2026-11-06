import json, numpy as np
from shapely.geometry import LineString, Point
S=''
_DMJ = json.load(open('topo/dem2m.json')); _DEM = np.load('topo/dem2m.npy', mmap_mode='r')
def g(p):
    r = int((_DMJ['y1'] - p[1]) / 2); c = int((p[0] - _DMJ['x0']) / 2); v = _DEM[r, c]
    return None if v == _DMJ['nodata'] else float(v) / 10.0
B=json.load(open('deckpage/basin.json')); L=json.load(open('dbread5/deck/layout.json'))['streets']
cp=[f for f in B['features'] if f['properties'].get('id')=='SB0595'][0]
c=L.get('SB0595',{}).get('c') or cp['geometry']['coordinates']
print('CPW first verts',[tuple(map(round,q)) for q in c[:4]])
D=json.load(open('hwy/data.json')); O=D['origin']
s0=[s for s in D['segs'] if s['r']=='OH-75' and s['a']==14.54 and 'BRT' not in s['t']][0]
OH=LineString([(x+O[0],y+O[1]) for x,y in s0['c']]); f=(19.4-14.54)/(OH.length/1000)
print('OH-75 ground by km:')
for k in np.arange(18.6,19.41,0.05):
    p=OH.interpolate((k-14.54)/f*1000).coords[0]; print('  %.2f'%k,tuple(map(round,p)),g(p))
print('straight CPW end -> OH-75 km 19.0..19.1')
for kk in (18.95,19.0,19.05,19.1):
    q=OH.interpolate((kk-14.54)/f*1000).coords[0]
    ln=LineString([c[0],q]); print(' km',kk,'len',round(ln.length),'ground:',[g(ln.interpolate(t,normalized=True).coords[0]) for t in np.linspace(0,1,9)])
print('Ludlow S22016 ground', [ (tuple(map(round,LineString(L.get('S22016',{}).get('c') or [ff for ff in B['features'] if ff['properties'].get('id')=='S22016'][0]['geometry']['coordinates']).interpolate(t,normalized=True).coords[0])) ) for t in (0,.25,.5)])
for p in [(712740,4336733),(712800,4336690),(712850,4336650),(712888,4336620),(712718,4336921),(713015,4337225),(713015,4337258),(713017,4337400),(712771,4337002)]:
    print(p,g(p))
