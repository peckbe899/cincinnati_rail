import json, numpy as np, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from shapely.geometry import LineString, Point, Polygon
from matplotlib.patches import Polygon as MP
T=json.load(open('deckpage/tracks.json'))
L=[LineString(f['geometry']['coordinates']) for f in T['features'] if f['geometry']['type']=='LineString' and 'Transcontinental' in str(f['properties'].get('name'))][0]
O=np.array(L.interpolate(4300).coords[0]); E=np.array(L.interpolate(5200).coords[0]); t=(E-O)/np.linalg.norm(E-O); n=np.array([-t[1],t[0]]); S0=4300
def P(s,o): return O+t*(s-S0)+n*o
A=Polygon(json.load(open('norwood/area_utm.json'))); TV=json.load(open('norwood/tv/tv_utm.json'))
J=json.load(open('topo/dem2m.json')); D=np.load('topo/dem2m.npy',mmap_mode='r')
x0,x1,y0,y1=719600,720900,4337450,4338350
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
# both side platforms = heritage 305 m islands (4545-4850) extended 450 ft (137 m) west and 150 ft (46 m) east: 4408-4896
ptrk([(4150,-2.25),(5260,-2.25)],M,2.0); ptrk([(4150,2.25),(5260,2.25)],M,2.0)
ptrk([(4308,-2.25),(4408,-7.25),(4896,-7.25),(4996,-2.25)],M,1.4)
ptrk([(4308,2.25),(4408,7.25),(4896,7.25),(4996,2.25)],M,1.4)
# ORR (T1-T4), all south of APEx; platforms 4545-4850
ptrk([(4150,-11),(4283,-11),(4408,-19.23),(4960,-19.23),(5060,-11),(5170,-7.25),(5260,-7.25)],R)
ptrk([(4300,-13.5),(4420,-27),(4500,-30.91),(4900,-30.91),(5017,-16.5),(5170,-11.75),(5260,-11.75)],R)
ptrk([(4150,-15.5),(4283,-15.5),(4400,-30),(4510,-35.41),(4880,-35.41),(5017,-21),(5170,-16.25),(5260,-16.25)],R)
ptrk([(4330,-21),(4420,-38),(4500,-47.09),(4860,-47.09),(5017,-25.5),(5170,-20.75),(5260,-20.75)],R)
# heritage bay island on the south (west-facing, buffers at the east end)
ptrk([(4420,-36),(4500,-51.59),(4870,-51.59)],R,1.1); ptrk([(4470,-52),(4545,-63.27),(4870,-63.27)],R,1.1)
for o_ in (-51.59,-63.27):
    q=[P(4870,o_-1.5),P(4870,o_+1.5)]; ax.plot([q[0][0],q[1][0]],[q[0][1],q[1][1]],'k-',lw=2)
# Transvalley (T9, T10): one island north; Waynesville to the prong, Hamilton east beside APEx
ptrk([(4150,9.5),(4337,9.5),(4400,19.23),(5000,19.23),(5100,12),(5170,7.25),(5260,7.25)],C,1.4)
ptrk([(4150,14),(4337,14),(4400,23.73),(4520,30.91),(4990,30.91),(5060,33),(5094,44.5),(5115,66.7),(5139,100.6),(5158,142)],C,1.4)
ptrk([(4960,19.23),(5040,26),(5094,38.5),(5115,60.7),(5139,94.6),(5158,136)],C,1.4)
ptrk([(5000,30.91),(5110,17),(5170,11.75),(5260,11.75)],C,1.4)
rect(4408,4896,-8.93,-17.23,'#e6a3e6',lab='APEx side platforms 488 m: heritage islands extended 450 ft west, 150 ft east'); rect(4408,4896,8.93,17.23,'#e6a3e6')
rect(4545,4850,-37.09,-45.41,'#ffd966',lab='ORR Norwood-Oakley Jct island (R1-R3, L71) 305 m')
rect(4545,4850,-20.91,-29.23,'#f4b183',lab='ORR Norwood island (X1, L75) 305 m')
rect(4545,4850,-53.27,-61.59,'#d9d9d9',lab='Heritage bay island, west-facing, 305 m')
rect(4545,4850,20.91,29.23,'#5fc8c8',lab='Transvalley island (Waynesville + Hamilton) 305 m')
a1=P(4545,-72); b1=P(4545,36); ax.plot([a1[0],b1[0]],[a1[1],b1[1]],'--',color='0.4',lw=.7)
a1=P(4850,-72); b1=P(4850,36); ax.plot([a1[0],b1[0]],[a1[1],b1[1]],'--',color='0.4',lw=.7)
rect(4636,4758,-72,-117.7,'#a9a9a9',lab='Station building 400 x 150 ft (122 x 46 m)')
rect(4700,4718,-72,70,'none',ec='b',a=1); ax.text(*P(4730,62),'main tunnel, north exit to inner ring',fontsize=7,color='b')
rect(4430,4470,-30,40,'none',ec='b',a=1); rect(4440,4520,-30,-60,'none',ec='b',a=1); ax.text(*P(4300,-45),'west hall (Montgomery Rd)',fontsize=7,color='b',ha='center')
rect(4896,5040,-3,3,'none',ec='b',a=1); ax.text(*P(4940,-6),'east passage',fontsize=7,color='b')
from shapely.ops import substring
from shapely.geometry import LineString as LS
dd=json.load(open('deckpage/context.json'))
for f in dd['tracks']:
    c=np.array(f['c']); ax.plot(c[:,0],c[:,1],color={'rer':'#1f77ff','metro':'#2ca02c'}[f['sys']],lw=.5,alpha=.45)
def ln(k,nm,pre):
    for f in dd[k]:
        if f['name']==nm and f['id'].startswith(pre):
            c=f['c']; return LS(c if isinstance(c[0][0],(int,float)) else c[0])
def stn(G,cp,length,w,col,lab):
    m=G.project(Point(cp)); seg=substring(G,m-length/2,m+length/2)
    x,y=seg.buffer(w/2,cap_style=2).exterior.xy; ax.plot(x,y,'--',color=col,lw=1.6,label=lab)
def q(s_,o_): return tuple(P(s_,o_))
Aline=LS(list(ln('rer','RER A','R-A-718498').coords)+list(ln('rer','RER A','R-A-720547').coords))
stn(LS([q(4600,1),q(5000,1)]),q(4802,1),204.2,22,'#1f77ff','TRI E, level -3 (mined, on the axis), 204 m')
stn(Aline,q(5057,0),204.2,22,'#d4002a','TRI A, level -4 (under E), 204 m, at the A/E crossing')
stn(LS([q(4600,15),q(4900,15)]),q(4754,15),152.4,18,'#2ca02c','Metro L3 terminus, level -2, 152 m (above TRI E)')
G4=ln('metro','Line 4','M-L4-716800')
stn(G4,q(4458,-99),152.4,16,'#8c564b','Metro L4 terminus, level -2, 152 m, south of the tracks (page tail cut back)')
G14=ln('metro','Line 14','M-L14'); stn(G14,q(4510,-100),152.4,14,'#9467bd','Metro L14, level -4 (deep bore), 152 m, beside L4')
for (s_,o_,tx) in [(5265,-24,'Oakley (R1-R3, L71)'),(5265,-14,'X1/L75'),(5265,-1,'APEx (straight)'),(5265,10,'Norwood-Hamilton'),(5110,120,'Waynesville via Lebanon (CL&N prong)')]:
    ax.text(*P(s_,o_),tx,fontsize=8,weight='bold')
ax.set_xlim(x0,x1); ax.set_ylim(y0,y1); ax.set_aspect('equal'); ax.legend(loc='lower left',fontsize=6.5,ncol=2)
ax.set_title('Norwood Central sketch v8 (not on the page): station building and Metro/TRI levels; dotted cyan = Ben\'s Transvalley KMLs',fontsize=10)
plt.tight_layout(); plt.savefig('norwood/sketch8.png')
