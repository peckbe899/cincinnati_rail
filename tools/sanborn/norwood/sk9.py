import json, numpy as np, math, sys, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from shapely.geometry import LineString as LS, Point, Polygon
from shapely.ops import substring
from matplotlib.patches import Polygon as MP, Rectangle
from scipy.interpolate import splprep, splev
F=json.load(open('norwood/frame.json')); O=np.array(F['o']); t=np.array(F['t']); n=np.array(F['n'])
def P(s,o): return O+t*(s-4300)+n*o
def ease(kn,s):
    if s<=kn[0][0]: return kn[0][1]
    for (s0,o0),(s1,o1) in zip(kn,kn[1:]):
        if s<=s1:
            u=(s-s0)/(s1-s0) if s1>s0 else 1; return o0+(o1-o0)*(1-math.cos(math.pi*u))/2
    return kn[-1][1]
def rmin(kn):
    r=1e9
    for (s0,o0),(s1,o1) in zip(kn,kn[1:]):
        d=abs(o1-o0); L=s1-s0
        if d>0 and L>0: r=min(r,2*L*L/(math.pi**2*d))
    return r
APW0,APW1=4438,4926; H0,H1=4545,4850
TR={}; M='m'; R='#d62728'; C='#008b8b'
def add(k,kn,s0,s1,col,parent=None,sdiv=None):
    if parent: kn=[(sdiv,ease(TR[parent][0],sdiv))]+kn
    TR[k]=(kn,s0 if not parent else sdiv,s1,col,parent)
add('T6',[(0,-2.25)],4150,5300,M); add('T7',[(0,2.25)],4150,5300,M)
add('T5',[(APW0,-7.25),(APW1,-7.25),(5040,-2.25)],0,5040,M,'T6',4318)
add('T8',[(APW0,7.25),(APW1,7.25),(5040,2.25)],0,5040,M,'T7',4318)
add('T4',[(4300,-10.5),(4434,-19.23),(4900,-19.23),(5060,-7.25)],4150,5300,R)
add('T3',[(4480,-30.91),(4860,-30.91),(5060,-11.75)],0,5300,R,'T4',4300)
add('T2',[(4283,-15),(4480,-35.41),(4870,-35.41),(5060,-16.25)],4150,5300,R)
add('B2',[(4520,-63.27),(4870,-63.27)],0,4870,R,'T2',4285)
add('B1',[(4490,-51.59),(4870,-51.59)],0,4870,R,'T2',4295)
add('T1',[(4480,-47.09),(4855,-47.09),(5065,-20.75)],0,5300,R,'T2',4300)
add('T9',[(4150,10.5),(4337,11),(4430,19.23),(4960,19.23),(5210,7.25)],4150,5300,C)
add('T10',[(4150,15),(4337,15.5),(4430,23.73),(4530,30.91),(4990,30.91),(5240,11.75)],4150,5300,C)
def off(k,s): return ease(TR[k][0],s)
# Waynesville pair: spline through the KML prong, offsets +-2.25
wp=np.array([(4985,28.66),(5025,28.9),(5062,32.0),(5094,42.5),(5115,62.7),(5139,96.6),(5158,138.1),(5178,218.7)])
tck,_=splprep([wp[:,0],wp[:,1]],s=60,k=3); uu=np.linspace(0,1,400); ws,wo=splev(uu,tck); d1=np.array(splev(uu,tck,der=1)); d2=np.array(splev(uu,tck,der=2))
curv=np.abs(d1[0]*d2[1]-d1[1]*d2[0])/np.power(d1[0]**2+d1[1]**2,1.5); Rw=1/curv.max()
tn=d1/np.hypot(*d1); nw=np.array([-tn[1],tn[0]])
W1=np.c_[ws+nw[0]*-2.25, wo+nw[1]*-2.25]; W2=np.c_[ws+nw[0]*2.25, wo+nw[1]*2.25]
A=Polygon(json.load(open('norwood/area_utm.json')))
if 'check' in sys.argv:
    for k in TR: print(k,'Rmin %.0f'%rmin(TR[k][0]))
    print('Waynesville Rmin %.0f'%Rw)
    bad=[]; sep={}
    for s in np.arange(4283,5200,5):
        live=sorted([(off(k,s),k) for k in TR if TR[k][1]<=s<=TR[k][2]])
        for (o1,k1),(o2,k2) in zip(live,live[1:]):
            g=o2-o1; fam=(TR[k1][4]==k2 or TR[k2][4]==k1 or (TR[k1][4] and TR[k1][4]==TR[k2][4]))
            if fam: continue
            if g<4.2: bad.append((int(s),k1,k2,round(g,1)))
        for o_,k in live:
            if s>4290 and s<5150 and not A.buffer(-1.0).contains(Point(P(s,o_))): bad.append((int(s),k,'outside',round(o_,1)))
    print(len(bad)); [print(b) for b in bad[:60]]
    sys.exit()
# ---------- drawing ----------
J=json.load(open('topo/dem2m.json')); D=np.load('topo/dem2m.npy',mmap_mode='r')
x0,x1,y0,y1=719600,720900,4337450,4338350
r0=int((J['y1']-y1)/2); r1=int((J['y1']-y0)/2); c0=int((x0-J['x0'])/2); c1=int((x1-J['x0'])/2)
Z=np.array(D[r0:r1,c0:c1],float)/10; gy,gx=np.gradient(Z,2); sl=np.arctan(np.hypot(gx,gy)); az=np.arctan2(-gx,gy)
hs=np.cos(np.radians(45))*np.cos(sl)+np.sin(np.radians(45))*np.sin(sl)*np.cos(np.radians(315)-az)
fig=plt.figure(figsize=(17,14),dpi=110); ax=fig.add_axes([0.03,0.30,0.94,0.67]); bx=fig.add_axes([0.06,0.04,0.9,0.21])
ax.imshow(hs,cmap='gray',extent=(x0,x1,y0,y1),alpha=.45)
ax.plot(*A.exterior.xy,'r-',lw=2,label="Ben's track area")
TV=json.load(open('norwood/tv/tv_utm.json'))
for nm in ['Norwood 1','Cincinnati-Lebanon']:
    q=np.array(TV[nm]); ax.plot(q[:,0],q[:,1],':',color='#00b0b0',lw=1)
def rect(s0,s1,o0,o1,fc,ec='k',lab=None,a=.85,lw=.7):
    ax.add_patch(MP([P(s0,o0),P(s1,o0),P(s1,o1),P(s0,o1)],closed=True,fc=fc,ec=ec,lw=lw,alpha=a,label=lab))
for k,(kn,s0,s1,col,par) in TR.items():
    ss=np.arange(s0,s1+1,2); q=np.array([P(s,ease(kn,s)) for s in ss]); ax.plot(q[:,0],q[:,1],color=col,lw=2.0 if k in('T6','T7') else 1.3)
for Wc in (W1,W2):
    q=np.array([P(a,b) for a,b in Wc]); ax.plot(q[:,0],q[:,1],color=C,lw=1.3)
for o_ in (-51.59,-63.27):
    q=[P(4870,o_-1.5),P(4870,o_+1.5)]; ax.plot([q[0][0],q[1][0]],[q[0][1],q[1][1]],'k-',lw=2)
rect(APW0,APW1,-8.93,-17.23,'#e6a3e6',lab='APEx side platforms 488 m (heritage + 350 ft W, 250 ft E)'); rect(APW0,APW1,8.93,17.23,'#e6a3e6')
rect(H0,H1,-37.09,-45.41,'#ffd966',lab='ORR Norwood-Oakley Jct island (R1-R3, L71)')
rect(H0,H1,-20.91,-29.23,'#f4b183',lab='ORR Norwood island (X1, L75)')
rect(H0,H1,-53.27,-61.59,'#d9d9d9',lab='Heritage bay island (west-facing)')
rect(H0,H1,20.91,29.23,'#5fc8c8',lab='Transvalley island')
rect(4636,4758,-72,-117.7,'#a9a9a9',lab='Station building 400 x 150 ft')
rect(4700,4718,-72,70,'#cfe2ff',ec='b',a=.5,lab='Level -1: main tunnel (building to inner ring)')
rect(4452,5045,-6,6,'#bcd7ff',ec='b',a=.5,lab='Level -1: concourse, Metro 4 to TRI A, above TRI E')
dd=json.load(open('deckpage/context.json'))
for f in dd['tracks']:
    c=np.array(f['c']); ax.plot(c[:,0],c[:,1],color={'rer':'#1f77ff','metro':'#2ca02c'}[f['sys']],lw=.5,alpha=.4)
def ln(k,nm,pre):
    for f in dd[k]:
        if f['name']==nm and f['id'].startswith(pre):
            c=f['c']; return LS(c if isinstance(c[0][0],(int,float)) else c[0])
def stn(G,cp,length,w,col,lab,ls='--'):
    m=G.project(Point(cp)); seg=substring(G,m-length/2,m+length/2)
    x,y=seg.buffer(w/2,cap_style=2).exterior.xy; ax.plot(x,y,ls=ls,color=col,lw=1.7,label=lab)
def q(s_,o_): return tuple(P(s_,o_))
Aline=LS(list(ln('rer','RER A','R-A-718498').coords)+list(ln('rer','RER A','R-A-720547').coords))
G4=ln('metro','Line 4','M-L4-716800'); G14=ln('metro','Line 14','M-L14')
stn(LS([q(4600,15),q(4900,15)]),q(4754,15),121.92,18,'#2ca02c','Level -2: Metro L3 terminus, 400 ft (122 m)')
stn(G4,q(4458,-64),121.92,16,'#8c564b','Level -2: Metro L4 terminus, 400 ft (122 m) (stops short of L3)')
stn(G14,q(4499,-64),121.92,14,'#9467bd','Level -3: Metro L14, 400 ft (122 m) (under L3)')
stn(Aline,q(5057,0),204.2,24,'#d4002a','Level -3: TRI A, 204 m (larger box)')
stn(LS([q(4600,1),q(5100,1)]),q(4880,1),204.2,22,'#1f77ff','Level -4: TRI E, 204 m, deep bore, under everything',ls=':')
for (s_,o_,tx) in [(5262,-24,'Oakley (R1-R3, L71)'),(5262,-14,'X1/L75'),(5262,-1,'APEx (straight)'),(5262,10,'Norwood-Hamilton'),(5165,165,'Waynesville via Lebanon (CL&N prong)')]:
    ax.text(*P(s_,o_),tx,fontsize=8,weight='bold')
ax.text(*P(4140,6),'6 tracks',fontsize=8,weight='bold',ha='right'); ax.text(*P(5262,22),'8 tracks + Waynesville',fontsize=8,weight='bold')
ax.set_xlim(x0,x1); ax.set_ylim(y0,y1); ax.set_aspect('equal'); ax.legend(loc='lower left',fontsize=6.5,ncol=2)
ax.set_title('Norwood Central sketch v10 (not on the page): smoothed throats, levels per Ben',fontsize=10)
# ---- schematic long section along the axis ----
bx.set_xlim(4380,5120); bx.set_ylim(-4.8,0.8); bx.set_yticks([0,-1,-2,-3,-4]); bx.set_yticklabels(['0 tracks','-1','-2','-3','-4'])
bx.axhline(0,color='k',lw=1); bx.set_xlabel('distance along the station (m, page chainage)'); bx.set_title('Schematic long section (projected onto the station axis; levels are order only, not depths)',fontsize=9)
def bar(s0,s1,lv,col,lab,h=0.55):
    bx.add_patch(Rectangle((s0,lv-h/2),s1-s0,h,fc=col,ec='k',lw=.6,alpha=.85)); bx.text((s0+s1)/2,lv,lab,ha='center',va='center',fontsize=7)
bar(APW0,APW1,0.35,'#e6a3e6','',0.3); bx.text(4560,0.35,'APEx platforms (surface)',fontsize=7,va='center')
bar(4700,4718,-0.5,'#cfe2ff','',1.0); bx.text(4722,-0.35,'main tunnel up to building',fontsize=7)
bar(4452,5045,-1,'#bcd7ff','concourse (Metro 4 to TRI A)')
bar(4693,4815,-2,'#9bd39b','L3 terminus (beside, north)'); bx.plot([4380,4693],[-2,-2],color='#2ca02c',lw=3)
bar(4440,4476,-2,'#c49c94','L4'); bar(4466,4520,-3,'#c5b0d5','L14')
bar(5029,5085,-3,'#ff9896','TRI A')
bar(4778,4982,-4,'#aec7e8','TRI E platforms'); bx.plot([4380,4778],[-4,-4],color='#1f77ff',lw=3); bx.plot([4982,5120],[-4,-4],color='#1f77ff',lw=3)
plt.savefig('norwood/sketch10.png')
print('Waynesville Rmin %.0f'%Rw)
