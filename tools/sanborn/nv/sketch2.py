try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, math, numpy as np, rasterio, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from shapely.geometry import LineString, Point, shape, box
from shapely.ops import substring
SP=_ws.DATA
P=json.load(open(SP+'nv/profile.json')); C=LineString(P['C']); V=json.load(open(SP+'nv/viaduct.json'))
DEM=rasterio.open(SP+'handoff/out/map3_profile_dem_dm.vrt')
def gz(e,n): return list(DEM.sample([(e,n)]))[0][0]/10
def deck(n): return 151.8+(n-4330700)/4840*8.2
s_tip,s_lud,s_mar=V['s_tip'],V['s_lud'],V['s_mar']
G=0.0075; Z_LUD=155.5
def via(s):
    z_arch=deck(C.interpolate(min(s,s_tip)).y)+6.5
    return min(z_arch, Z_LUD+G*(s_lud-s)) if s<s_lud else Z_LUD
S_MON=3903; S_ST0,S_ST1=4398,4602; Z_ST=163.0; S_FLY=4810
S_RAMP_TOP=S_MON+(Z_ST-151.8)/0.025
def bd(s):
    if s<=S_MON: return 151.8 if s>=s_tip-250 else None
    if s<=S_RAMP_TOP: return 151.8+0.025*(s-S_MON)
    if s<=S_ST1: return Z_ST
    return max(Z_LUD, Z_ST-(Z_ST-Z_LUD)/(s_lud-S_ST1)*(s-S_ST1)) if s<=s_lud+200 else None
def dz(s): return Z_ST+0.03*(s-S_ST1) if S_ST1<=s<=S_FLY+20 else None
def indy(s): return via(s) if s<=4085 else (166.6+0.01*(s-4085) if s<=S_FLY+20 else None)
def old_apex(s): return min(164.5, 151.8+0.0094*(s_tip-s)) if s<=s_tip else None
L=json.load(open(SP+'nv/lines.json')); T3={o['name']:o for o in L if o['src']=='TRIMET3D'}
GR=LineString(T3['Greensburg-California 3D']['c'])
fig=plt.figure(figsize=(20,14.5))
ax=fig.add_axes([0.02,0.05,0.42,0.9]); ax2=fig.add_axes([0.5,0.56,0.48,0.39]); ax3=fig.add_axes([0.5,0.03,0.48,0.47])
x0,y0,x1,y1=711700,4334250,713150,4337150
win=rasterio.windows.from_bounds(x0,y0,x1,y1,DEM.transform); Z=DEM.read(1,window=win,out_shape=(int((y1-y0)/5),int((x1-x0)/5))).astype(float)/10
ax.imshow(Z,extent=(x0,x1,y0,y1),cmap='Greys_r',vmin=140,vmax=200,alpha=0.35)
ax.contourf(np.linspace(x0,x1,Z.shape[1]),np.linspace(y1,y0,Z.shape[0]),Z,levels=[0,147],colors=['#7aa6c9'],alpha=0.45)
D=json.load(open(SP+'deck/deck.json'))['features']; B=json.load(open(SP+'deckpage/basin.json'))['features']; BB=box(x0,y0,x1,y1)
for f in D:
    p=f['properties']; g=shape(f['geometry'])
    if not g.intersects(BB): continue
    if p['layer']=='deck':
        for q in getattr(g,'geoms',[g]): ax.plot(*q.exterior.xy,'k--',lw=0.7)
    if p['layer']=='street': ax.plot(*g.xy,color='#1f4f7a',lw=1.0)
for f in B:
    p=f['properties']; g=shape(f['geometry'])
    if p['layer']=='street' and g.intersects(BB): ax.plot(*g.xy,color='#999',lw=0.5 if p['kind']=='we_alley' else 0.9)
def band(s0,s1,o0,o1,**k):
    a=np.array(substring(C,s0,s1).coords); t=np.gradient(a,axis=0); t/=np.hypot(t[:,0],t[:,1])[:,None]; n=np.c_[-t[:,1],t[:,0]]
    ring=np.r_[a+n*o0,(a+n*o1)[::-1]]; ax.fill(ring[:,0],ring[:,1],**k)
def at(s,o):
    p=C.interpolate(s); q=C.interpolate(s+3); d=np.array([q.x-p.x,q.y-p.y]); d/=np.linalg.norm(d); return np.array([p.x,p.y])+np.array([-d[1],d[0]])*o
band(s_mar,s_tip,28.4,-28.4,fc='#16252a',alpha=0.22,ec='#16252a',lw=0.6)
band(s_tip,s_lud,28.4,-28.4,fc='#d07a1c',alpha=0.30,ec='#8a4b0a',lw=0.8)
band(S_MON,S_ST0,-33,-47,fc='#2a7ab0',alpha=0.35,ec='#2a7ab0',lw=0.6)
band(S_ST0,S_ST1,-33,-57,fc='#2a7ab0',alpha=0.55,ec='#2a7ab0',lw=0.8)
band(S_ST1,S_FLY,-33,-47,fc='#2a7ab0',alpha=0.35,ec='#2a7ab0',lw=0.6)
# flyover: from the east side at S_FLY, NW onto the Greensburg 3D line
g3=np.array(GR.coords); k=int(np.argmin(np.hypot(g3[:,0]-711970,g3[:,1]-4336244)))
p0=at(S_FLY-60,-40); p1=at(S_FLY,0); p2=g3[k]
fly=[p0+(p1-p0)*t for t in np.linspace(0,1,8)]+[p1+(p2-p1)*t for t in np.linspace(0,1,10)]
fly=np.array(fly); ax.plot(fly[:,0],fly[:,1],color='#5a2a8a',lw=7,alpha=0.45,solid_capstyle='butt')
west=np.array([q for q in g3 if q[0]<p2[0]+1 and q[1]>p2[1]-1][:400]); ax.plot(west[:,0],west[:,1],color='#5a2a8a',lw=2.5,alpha=0.7)
ax.plot(*at(4146,0),'s',ms=6,mfc='none',mec='#2a7ab0'); ax.annotate('Arlington (B) in the KMZ: 250 m north of the deck tip,\non the climb from under the deck',at(4146,0),at(4146,0)+np.array([-560,-90]),fontsize=7,color='#2a7ab0',arrowprops=dict(arrowstyle='-',lw=0.5,color='#2a7ab0'))
def lab(s,t,dx=60,dy=0,c='k',o=0):
    p=at(s,o); ax.plot(*p,'o',ms=4,color=c); ax.annotate(t,p,p+np.array([dx,dy]),fontsize=7.5,color=c,arrowprops=dict(arrowstyle='-',lw=0.5,color=c))
lab(s_mar,'Marshall: APEx 164.5 m (as now)',120)
lab(3181,'Hopple: at deck level under the viaduct\n(6.5 m, like Marshall)',120)
lab(s_tip,'deck tip: viaduct 166.6 m;\nB/D under Monmouth in a box (151.8 m)',140,-70)
lab((S_ST0+S_ST1)/2,'Arlington (B, D) moved ~350 m north:\nelevated, 163.0 m, entrances at Marquis and Adelaide',140,-30,'#2a7ab0',-45)
lab(S_FLY,'Earl: D and the Indianapolis pair fly over\nORR E, APEx and ORR W at about 169-174 m',-640,90,'#5a2a8a',0)
lab(4895,'Whiteley: 7.4 m clear',140)
lab(s_lud,'Ludlow: all tracks at ground, 155.5 m\n(Ludlow keeps its bridge)',120,-40,'#b23a2e')
lab(5725,'Northside/Spring Grove (B): surface',120,10,'#2a7ab0')
LUD=[shape(f['geometry']) for f in json.load(open(SP+'lph/osm_north.geojson'))['features'] if f['properties'].get('name')=='Ludlow Avenue']
for g in LUD:
    if g.intersects(BB) and g.geom_type=='LineString': ax.plot(*g.xy,color='#b23a2e',lw=1.6)
ax.set_xlim(x0,x1); ax.set_ylim(y0,y1); ax.set_aspect('equal'); ax.tick_params(labelsize=6); ax.grid(lw=0.2)
ax.set_title('North trunk viaduct v2: TRIMET group (Indianapolis + TRI B/D) on the east side',fontsize=11,loc='left')
ss=np.arange(2400,6000,10)
ax2.plot(ss,[gz(*C.interpolate(s).coords[0]) for s in ss],color='#8a6a3a',lw=1,label='ground / deck surface (map 3)')
ax2.plot(ss,[via(s) for s in ss],color='#d07a1c',lw=2.2,label='APEx Dayton/Norwood + ORR (viaduct)')
ax2.plot(ss,[indy(s) for s in ss],color='#16252a',lw=1.5,label='APEx Indianapolis pair')
ax2.plot(ss,[bd(s) for s in ss],color='#2a7ab0',lw=1.8,label='TRI B (B/D south of Arlington)')
ax2.plot(ss,[dz(s) for s in ss],color='#5a2a8a',lw=1.8,label='TRI D to the flyover')
ax2.plot(ss,[old_apex(s) for s in ss],color='#16252a',lw=0.8,ls='--',label='APEx now (portal at the tip)')
for nm,lb,s,x,y,z in V['rows']:
    if lb!='APEx/ORR': continue
    ax2.plot(s,z,'v',ms=3,color='#1f4f7a'); ax2.text(s,z-1.2,nm.split()[0],rotation=90,fontsize=5.5,ha='center',va='top',color='#1f4f7a')
ax2.axvspan(S_ST0,S_ST1,color='#2a7ab0',alpha=0.12)
for s,t in ((s_mar,'Marshall'),(3181,'Hopple'),(s_tip,'deck tip'),(4146,'Arlington (KMZ)'),((S_ST0+S_ST1)/2,'Arlington, moved'),(S_FLY,'flyover'),(s_lud,'Ludlow'),(5725,'Northside/Spring Grove')):
    ax2.axvline(s,color='#999',lw=0.5); ax2.text(s,177.5,t,rotation=90,fontsize=6.5,va='top',ha='right')
ax2.set_ylim(140,178); ax2.set_xlim(2400,6000); ax2.legend(fontsize=6.5,loc='lower left'); ax2.grid(lw=0.2); ax2.tick_params(labelsize=7)
ax2.set_xlabel('m along the APEx line from CUT',fontsize=7)
ax2.set_title('Long section',fontsize=9,loc='left')
def xsec(y0,title,tracks,island_after=None,note=''):
    w=4.75; xs=[]; x=0
    for i,(g,n) in enumerate(tracks):
        if i: x+=(4.5 if g.startswith('APEx') and tracks[i-1][0].startswith('APEx') else 6.75)
        for kk in range(n):
            xs.append((x,g)); x+= (14.5 if (island_after==g and kk==0) else 4.5)
        x-= (4.5)
    span=xs[-1][0]-xs[0][0]; W=span+2*w
    ax3.add_patch(Rectangle((-w,y0),W,1.2,fc='#ddd',ec='k',lw=0.6))
    colc={'APEx':'#16252a','ORR':'#b0207a','TRI':'#2a7ab0'}
    for x,g in xs: ax3.plot([x-0.72,x+0.72],[y0+1.25,y0+1.25],color=colc[g.split()[0]],lw=3)
    if island_after:
        xx=[x for x,g in xs if g==island_after]; ax3.add_patch(Rectangle((xx[0]+1.75,y0+1.2),11,0.9,fc='#2a7ab0',alpha=0.4))
    gx={}
    for x,g in xs: gx.setdefault(g,[]).append(x)
    for g,v in gx.items(): ax3.text(np.mean(v),y0+2.3,g,ha='center',fontsize=7,color=colc[g.split()[0]])
    ax3.text(-w,y0+4.0,'%s: %d tracks, deck %.0f m%s' % (title,len(xs),W,note),fontsize=8)
xsec(30,'Marshall to the deck tip (arch viaduct over the lobe)',[('ORR W',2),('APEx Dayton+Norwood',4),('ORR E',2),('APEx Indy',2)],note='; TRI B/D under the deck beneath the Indianapolis pair')
xsec(20,'Deck tip to Arlington',[('ORR W',2),('APEx Dayton+Norwood',4),('ORR E',2),('APEx Indy',2),('TRI B/D',2)],note=' (B/D climbing 2.5% from the Monmouth box, Indy 1%)')
xsec(10,'Arlington station',[('ORR W',2),('APEx Dayton+Norwood',4),('ORR E',2),('APEx Indy',2),('TRI B/D',2)],island_after='TRI B/D',note=' (island 11 m)')
xsec(0,'Earl (after the flyover) to Ludlow',[('ORR W',2),('APEx Dayton+Norwood',4),('ORR E',2),('TRI B',2)])
ax3.set_xlim(-8,92); ax3.set_ylim(-2,38); ax3.axis('off')
ax3.set_title('Cross sections, looking north (4.5 m within a group, 6.75 m between groups, 4.75 m outer track to edge; one deck drawn per section)',fontsize=8,loc='left')
plt.savefig(SP+'nv/North_Trunk_Viaduct_sketch_v2.png',dpi=110)
print('ramp top s %.0f; B at Sassafras %.1f; D at flyover %.1f (viaduct %.1f); Indy at flyover %.1f' % (S_RAMP_TOP, bd(4322), dz(S_FLY), via(S_FLY), indy(S_FLY)))
for nm,s,zs in (('Brashears',4674,152.1),('Earl',4810,152.9),('Whiteley',4895,152.9),('Spring Grove',5061,149.2),('Ford',5107,151.2),('Colerain',5189,151.3),('Ford2',5204,151.3)):
    print('  B over %-12s %.1f clear %.1f' % (nm, bd(s), bd(s)-zs))
