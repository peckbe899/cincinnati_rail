import json, numpy as np, math, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from shapely.geometry import LineString, Point, Polygon
from matplotlib.patches import Polygon as MP
T=json.load(open('deckpage/tracks.json'))
L=[LineString(f['geometry']['coordinates']) for f in T['features'] if f['geometry']['type']=='LineString' and 'Transcontinental' in str(f['properties'].get('name'))][0]
O=np.array(L.interpolate(4300).coords[0]); E=np.array(L.interpolate(5200).coords[0]); t=(E-O)/np.linalg.norm(E-O); n=np.array([-t[1],t[0]])
S0=4300
def P(s,o): return O+t*(s-S0)+n*o
A=Polygon(json.load(open('norwood/area_utm.json')))
J=json.load(open('topo/dem2m.json')); D=np.load('topo/dem2m.npy',mmap_mode='r')
x0,x1,y0,y1=719650,720800,4337650,4338300
r0=int((J['y1']-y1)/2); r1=int((J['y1']-y0)/2); c0=int((x0-J['x0'])/2); c1=int((x1-J['x0'])/2)
Z=np.array(D[r0:r1,c0:c1],float)/10; gy,gx=np.gradient(Z,2); sl=np.arctan(np.hypot(gx,gy)); az=np.arctan2(-gx,gy)
hs=np.cos(np.radians(45))*np.cos(sl)+np.sin(np.radians(45))*np.sin(sl)*np.cos(np.radians(315)-az)
fig,ax=plt.subplots(figsize=(17,10),dpi=110); ax.imshow(hs,cmap='gray',extent=(x0,x1,y0,y1),alpha=.55)
ax.plot(*A.exterior.xy,'r-',lw=2,label="Ben's station area")
for (s_,o_,tx) in [(5205,-35,'to Oakley (R1-R3, L71, TRI E)'),(5205,25,'APEx diagonal + X1/L75 pair'),(5150,95,'NE prong (CL&N lower approach; TRI A on the page)')]: ax.text(*P(s_,o_),tx,fontsize=8,color='k',weight='bold')
def rect(s0,s1,o0,o1,fc,ec='k',lab=None,a=.8):
    ax.add_patch(MP([P(s0,o0),P(s1,o0),P(s1,o1),P(s0,o1)],closed=True,fc=fc,ec=ec,lw=.6,alpha=a,label=lab))
def trk(o,s0,s1,c,lw=1.2):
    a=P(s0,o); b=P(s1,o); ax.plot([a[0],b[0]],[a[1],b[1]],color=c,lw=lw)
# APEx: 488 m platforms s 4490-4978; ORR 305 m s 4545-4850; whole section 4 m south of the first try
AP0,AP1=4490,4978; OR0,OR1=4545,4850
def ptrk(pts,c,lw=1.3):
    q=[P(a,b) for a,b in pts]; ax.plot([p[0] for p in q],[p[1] for p in q],color=c,lw=lw)
M='m'; R='#d62728'
ptrk([(4250,5.5),(4330,5.5),(4460,13.02),(5080,13.02),(5180,7.0),(5215,7.0)],M,1.6)
ptrk([(4250,10),(4330,10),(4460,17.52),(5080,17.52),(5180,11.5),(5215,11.5)],M,1.6)
ptrk([(4380,6.9),(4470,8.02),(4995,8.02),(5080,13.02)],M,1.6)
ptrk([(4380,11.6),(4480,22.52),(4990,22.52),(5080,17.52)],M,1.6)
ptrk([(4250,-1),(4330,-1),(4420,-4.46),(4900,-4.46),(5150,2.0),(5215,2.0)],R)
ptrk([(4330,-1),(4480,-16.14),(4900,-16.14),(5150,-2.5),(5215,-2.5)],R)
ptrk([(4250,-5.5),(4330,-5.5),(4480,-20.64),(4880,-20.64),(5150,-7.5),(5215,-7.5)],R)
ptrk([(4360,-6.5),(4500,-32.32),(4870,-32.32),(5150,-12),(5215,-12)],R)
rect(AP0,AP1,23.6+0.5,32.5,'#e6a3e6',lab='APEx platforms, 488 m (screen doors)'); rect(AP0,AP1,-1.96,6.34,'#e6a3e6')
rect(OR0,OR1,-6.14,-14.44,'#f4b183',lab='ORR Norwood island (X1, L75), 305 m'); rect(OR0,OR1,-22.32,-30.62,'#ffd966',lab='ORR Norwood-Oakley Jct island (R1-R3, L71), 305 m')
rect(4620,4780,-35.3,-62,'#a9a9a9',lab='Heritage headhouse (New Haven type)')
rect(4690,4710,-35.3,33,'none',ec='b',a=1); 
a=P(4715,-45); ax.annotate('passenger tunnel',P(4700,36),fontsize=8,color='b')
# below-grade boxes (dashed)
def box(s0,s1,o0,o1,c,lab):
    pts=[P(s0,o0),P(s1,o0),P(s1,o1),P(s0,o1),P(s0,o0)]; ax.plot([p[0] for p in pts],[p[1] for p in pts],'--',color=c,lw=1.4,label=lab)
box(4598,4802,-10,2,'#1f77ff','TRI E box below, 204 m (on the axis)')
box(4754,4906,8,22,'#2ca02c','Metro Line 3 box below, 152 m')
d=json.load(open('deckpage/context.json'))
for f in d['tracks']:
    c=np.array(f['c']); ax.plot(c[:,0],c[:,1],color={'rer':'#1f77ff','metro':'#2ca02c'}[f['sys']],lw=.6,alpha=.6)
for k in ['stations','rer_stations']:
    for s in d[k]:
        p=s['p']
        if x0<p[0]<x1 and y0<p[1]<y1: ax.plot(*p,'ko',ms=3); ax.text(p[0]+6,p[1]-12,s['name']+' '+str(s.get('line') or s.get('lines')),fontsize=6)
for s,lab in [(4459,'Montgomery Rd: L4/L14 below'),(5061,'TRI A crosses under')]:
    a=P(s,-75); b=P(s,45); ax.plot([a[0],b[0]],[a[1],b[1]],':',color='k',lw=.8); ax.text(*P(s,-82),lab,fontsize=7,ha='center')
ax.set_xlim(x0,x1); ax.set_ylim(y0,y1); ax.set_aspect('equal'); ax.legend(loc='lower left',fontsize=7)
ax.set_title('Norwood Central sketch (not on the page): 8 tracks on one level, offsets from the page APEx line',fontsize=10)
plt.tight_layout(); plt.savefig('norwood/sketch.png')
