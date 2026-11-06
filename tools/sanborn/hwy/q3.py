import json, numpy as np
from shapely.geometry import LineString, Point
exec(open('hwy/q2.py').read().split("B=json.load")[0])
D=json.load(open('hwy/data.json')); O=D['origin']
s0=[s for s in D['segs'] if s['r']=='OH-75' and s['a']==14.54 and 'BRT' not in s['t']][0]
OH=LineString([(x+O[0],y+O[1]) for x,y in s0['c']]); f=(19.4-14.54)/(OH.length/1000)
s1=[s for s in D['segs'] if s['r']=='OH-75' and s['a']==19.4 and 'BRT' not in s['t']][0]
OH2=LineString([(x+O[0],y+O[1]) for x,y in s1['c']])
print('offset m (+ = right of NB direction? computed as SE side)'); 
print('km   '+' '.join('%6d'%o for o in (-40,-20,0,20,30,40,60,80,100,120)))
for k in np.arange(18.9,19.42,0.05):
    d=(k-14.54)/f*1000; p=np.array(OH.interpolate(d).coords[0]); q=np.array(OH.interpolate(d+1).coords[0]); t=(q-p)/np.linalg.norm(q-p)
    n=np.array([-t[1],t[0]])  # left of increasing km (heading SW) -> which side?
    # make n point SE (toward smaller y / larger x side): check
    if n[1]>0: n=-n
    print('%.2f '%k+' '.join('%6.1f'%(g(p+o*n) or -1) for o in (-40,-20,0,20,30,40,60,80,100,120)))
