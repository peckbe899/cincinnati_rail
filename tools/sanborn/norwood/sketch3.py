import json, numpy as np, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from shapely.geometry import LineString, Point, Polygon
from matplotlib.patches import Polygon as MP
T=json.load(open('deckpage/tracks.json'))
L=[LineString(f['geometry']['coordinates']) for f in T['features'] if f['geometry']['type']=='LineString' and 'Transcontinental' in str(f['properties'].get('name'))][0]
O=np.array(L.interpolate(4300).coords[0]); E=np.array(L.interpolate(5200).coords[0]); t=(E-O)/np.linalg.norm(E-O); n=np.array([-t[1],t[0]]); S0=4300
def P(s,o): return O+t*(s-S0)+n*o
A=Polygon(json.load(open('norwood/area_utm.json'))); TV=json.load(open('norwood/tv/tv_utm.json'))
J=json.load(open('topo/dem2m.json')); D=np.load('topo/dem2m.npy',mmap_mode='r')
x0,x1,y0,y1=719650,720850,4337600,4338300
r0=int((J['y1']-y1)/2); r1=int((J['y1']-y0)/2); c0=int((x0-J['x0'])/2); c1=int((x1-J['x0'])/2)
Z=np.array(D[r0:r1,c0:c1],float)/10; gy,gx=np.gradient(Z,2); sl=np.arctan(np.hypot(gx,gy)); az=np.arctan2(-gx,gy)
hs=np.cos(np.radians(45))*np.cos(sl)+np.sin(np.radians(45))*np.sin(sl)*np.cos(np.radians(315)-az)
fig,ax=plt.subplots(figsize=(17,10),dpi=110); ax.imshow(hs,cmap='gray',extent=(x0,x1,y0,y1),alpha=.5)
ax.plot(*A.exterior.xy,'r-',lw=2,label="Ben's track area")
for nm,c in [('Norwood 1','#00b0b0'),('Cincinnati-Lebanon','#00b0b0')]:
    q=np.array(TV[nm]); ax.plot(q[:,0],q[:,1],':',color=c,lw=1.2)
def rect(s0,s1,o0,o1,fc,ec='k',lab=None,a=.8,ls='-'):
    ax.add_patch(MP([P(s0,o0),P(s1,o0),P(s1,o1),P(s0,o1)],closed=True,fc=fc,ec=ec,lw=.7,alpha=a,label=lab,ls=ls))
def ptrk(pts,c,lw=1.3):
    q=[P(a,b) for a,b in pts]; ax.plot([p[0] for p in q],[p[1] for p in q],color=c,lw=lw)
M='m'; R='#d62728'; C='#008b8b'
# APEx (T5-T8): through pair dead straight, 6.25 m north of the page line
ptrk([(4200,4),(5215,4)],M,2.0); ptrk([(4200,8.5),(5215,8.5)],M,2.0)
ptrk([(4380,4),(4480,-1),(4985,-1),(5080,4)],M,1.4)
ptrk([(4380,8.5),(4480,13.5),(4985,13.5),(5080,8.5)],M,1.4)
# ORR (T1-T4)
ptrk([(4200,-10.5),(4330,-10.5),(4470,-38.5),(4860,-38.5),(5100,-16),(5170,-14),(5215,-14)],R)
ptrk([(4360,-11),(4480,-26.84),(4870,-26.84),(5100,-11),(5170,-9.5),(5215,-9.5)],R)
ptrk([(4200,-6),(4330,-6),(4470,-22.34),(4880,-22.34),(5100,-6),(5170,-5),(5215,-5)],R)
ptrk([(4360,-6.5),(4440,-10.68),(4890,-10.68),(5100,-2),(5170,-0.5),(5215,-0.5)],R)
# Transvalley (T9, T10): one island; Waynesville to the prong, Hamilton east
ptrk([(4200,13),(4330,13),(4440,23.18),(4960,23.18),(5040,26),(5094,38.5),(5115,60.7),(5139,94.6),(5158,136)],C,1.4)
ptrk([(4200,17.5),(4330,17.5),(4460,34.86),(4980,34.86),(5060,34),(5094,44.5),(5115,66.7),(5139,100.6),(5158,142)],C,1.4)
ptrk([(4990,23.18),(5100,16),(5170,13),(5215,13)],C,1.4)
ptrk([(5010,26.5),(5100,19.5),(5170,17.5),(5215,17.5)],C,1.4)
rect(4490,4978,-2.68,-8.68,'#e6a3e6',lab='APEx side platforms 488 m, 6 m wide (screen doors)'); rect(4490,4978,15.18,21.18,'#e6a3e6')
rect(4545,4850,-28.52,-36.82,'#ffd966',lab='ORR Norwood-Oakley Jct island (R1-R3, L71) 305 m')
rect(4545,4850,-12.36,-20.66,'#f4b183',lab='ORR Norwood island (X1, L75) 305 m')
rect(4600,4905,24.86,33.16,'#5fc8c8',lab='Transvalley island (Waynesville through + Hamilton turn), length TBD')
rect(4620,4800,-41,-66,'#a9a9a9',lab='Heritage headhouse (on the freed south strip)')
rect(4700,4720,-41,36,'none',ec='b',a=1); ax.text(*P(4712,38),'passenger tunnel',fontsize=8,color='b')
for (s_,o_,tx) in [(5215,-28,'Oakley (R1-R3, L71)'),(5215,-2,'X1/L75'),(5215,6,'APEx (straight)'),(5215,15,'Norwood-Hamilton'),(5110,120,'Waynesville via Lebanon (CL&N prong)')]:
    ax.text(*P(s_,o_),tx,fontsize=8,weight='bold')
for s,lab in [(4459,'Montgomery Rd: L4/L14 below'),(5061,'TRI A crosses under')]:
    a=P(s,-80); b=P(s,45); ax.plot([a[0],b[0]],[a[1],b[1]],':',color='k',lw=.8); ax.text(*P(s,-108),lab,fontsize=7,ha='center')
ax.set_xlim(x0,x1); ax.set_ylim(y0,y1); ax.set_aspect('equal'); ax.legend(loc='lower left',fontsize=7)
ax.set_title('Norwood Central sketch v3 (not on the page): straight APEx through pair, 10 tracks on one level; dotted cyan = Ben\'s Transvalley KMLs',fontsize=10)
plt.tight_layout(); plt.savefig('norwood/sketch3.png')
