import json, numpy as np, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from shapely.geometry import LineString, Point, Polygon
from matplotlib.patches import Polygon as MP
T=json.load(open('deckpage/tracks.json'))
L=[LineString(f['geometry']['coordinates']) for f in T['features'] if f['geometry']['type']=='LineString' and 'Transcontinental' in str(f['properties'].get('name'))][0]
O=np.array(L.interpolate(4300).coords[0]); E=np.array(L.interpolate(5200).coords[0]); t=(E-O)/np.linalg.norm(E-O); n=np.array([-t[1],t[0]]); S0=4300
def P(s,o): return O+t*(s-S0)+n*o
A=Polygon(json.load(open('norwood/area_utm.json'))); TV=json.load(open('norwood/tv/tv_utm.json'))
J=json.load(open('topo/dem2m.json')); D=np.load('topo/dem2m.npy',mmap_mode='r')
x0,x1,y0,y1=719600,720900,4337600,4338300
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
# APEx (T5-T8): through pair on the page APEx line, dead straight
ptrk([(4150,-2.25),(5260,-2.25)],M,2.0); ptrk([(4150,2.25),(5260,2.25)],M,2.0)
ptrk([(4380,-2.25),(4480,-7.25),(4985,-7.25),(5085,-2.25)],M,1.4)
ptrk([(4380,2.25),(4480,7.25),(4985,7.25),(5085,2.25)],M,1.4)
# ORR (T1-T4), all south of APEx
ptrk([(4150,-11.75),(4330,-11.75),(4480,-47.09),(4860,-47.09),(5040,-25),(5170,-20.75),(5260,-20.75)],R)
ptrk([(4360,-12.5),(4490,-35.41),(4870,-35.41),(5040,-21),(5170,-16.25),(5260,-16.25)],R)
ptrk([(4150,-7.25),(4330,-7.25),(4480,-30.91),(4880,-30.91),(5060,-14),(5170,-11.75),(5260,-11.75)],R)
ptrk([(4350,-7.6),(4440,-19.23),(4890,-19.23),(5080,-9),(5170,-7.25),(5260,-7.25)],R)
# Transvalley (T9, T10): one island north; Waynesville to the prong, Hamilton east beside APEx
ptrk([(4150,7.25),(4330,7.25),(4440,19.23),(4960,19.23),(5040,24),(5094,38.5),(5115,60.7),(5139,94.6),(5158,136)],C,1.4)
ptrk([(4150,11.75),(4330,11.75),(4460,30.91),(4980,30.91),(5060,33),(5094,44.5),(5115,66.7),(5139,100.6),(5158,142)],C,1.4)
ptrk([(4990,19.23),(5110,9),(5170,7.25),(5260,7.25)],C,1.4)
ptrk([(5010,22),(5110,13.5),(5170,11.75),(5260,11.75)],C,1.4)
rect(4490,4978,-8.93,-17.23,'#e6a3e6',lab='APEx side platforms 488 m, 8.3 m (screen doors)'); rect(4490,4978,8.93,17.23,'#e6a3e6')
rect(4545,4850,-37.09,-45.41,'#ffd966',lab='ORR Norwood-Oakley Jct island (R1-R3, L71) 305 m')
rect(4545,4850,-20.91,-29.21,'#f4b183',lab='ORR Norwood island (X1, L75) 305 m')
rect(4600,4905,20.91,29.21,'#5fc8c8',lab='Transvalley island (Waynesville through + Hamilton turn), length TBD')
rect(4620,4800,-50,-68,'#a9a9a9',lab='Heritage headhouse (on the freed south strip)')
rect(4700,4720,-50,32,'none',ec='b',a=1); ax.text(*P(4712,34),'passenger tunnel',fontsize=8,color='b')
for (s_,o_,tx) in [(5265,-24,'Oakley (R1-R3, L71)'),(5265,-14,'X1/L75'),(5265,-1,'APEx (straight)'),(5265,10,'Norwood-Hamilton'),(5110,120,'Waynesville via Lebanon (CL&N prong)')]:
    ax.text(*P(s_,o_),tx,fontsize=8,weight='bold')
for s,lab in [(4459,'Montgomery Rd: L4/L14 below'),(5061,'TRI A crosses under')]:
    a=P(s,-80); b=P(s,45); ax.plot([a[0],b[0]],[a[1],b[1]],':',color='k',lw=.8); ax.text(*P(s,-108),lab,fontsize=7,ha='center')
ax.set_xlim(x0,x1); ax.set_ylim(y0,y1); ax.set_aspect('equal'); ax.legend(loc='lower left',fontsize=7)
ax.set_title('Norwood Central sketch v4 (not on the page): APEx straight on its page line, everything else around it; 10 tracks on one level; dotted cyan = Ben\'s Transvalley KMLs',fontsize=10)
plt.tight_layout(); plt.savefig('norwood/sketch4.png')
