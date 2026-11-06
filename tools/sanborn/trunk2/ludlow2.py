import json,sys,numpy as np
sys.path.insert(0,'trunk2'); 
exec(open('trunk2/ludlow.py').read().split('best=None')[0])
from shapely.strtree import STRtree
BJ=json.load(open(SP+'deckpage/basin.json'))
obs=[]
for f in BJ['features']:
    p=f['properties']; g=shape(f['geometry'])
    if p.get('layer')=='block': obs.append(('BLK '+str(p.get('id','')),g))
    if p.get('layer')=='street' and g.geom_type=='LineString': obs.append(('S '+(p.get('name') or ''),g.buffer(p.get('width_m',12)/2,cap_style=2)))
for f in H['features']:
    if f['properties'].get('layer')=='hw_area': obs.append(('CEM',shape(f['geometry'])))
tree=STRtree([g for _,g in obs])
for s0,s1,fa,fb in ((4650,7400,0.45,0.3),(4650,7400,0.5,0.3)):
    p0,t0,p3,t3=pt(s0),tan(s0),pt(s1),tan(s1); L=np.hypot(*(p3-p0)); c=bez(p0,t0,p3,t3,fa*L,fb*L,1400)
    print('R',round(minr(c)),'clear',round(east_clear(c),1))
    cl=LineString(c)
    for s in range(4700,7400,200):
        q=pt(s); d=cl.distance(Point(q)); 
        # signed: west positive
        j=int(np.argmin(np.hypot(*(c-q).T))); t=c[min(j+1,len(c)-1)]-c[max(j-1,0)]; e=np.array([t[1],-t[0]])/np.hypot(*t)
        print(s, 'shift west of current %.1f'%(-(q-c[j])@e*-1))
    # west footprint: from -50 to +27 offsets
    t=np.gradient(c,axis=0); t/=np.hypot(t[:,0],t[:,1])[:,None]; e=np.c_[t[:,1],-t[:,0]]
    from shapely.geometry import Polygon
    left=c-e*50; right=c+e*27; poly=Polygon(np.vstack([left,right[::-1]]))
    hits=sorted({obs[i][0] for i in tree.query(poly) if obs[i][1].intersects(poly)})
    print(hits[:40])
