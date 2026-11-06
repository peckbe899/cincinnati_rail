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
def rail(s):
    z_arch=deck(C.interpolate(min(s,s_tip)).y)+6.5
    return min(z_arch, Z_LUD+G*(s_lud-s)) if s<s_lud else Z_LUD
def old_apex(s):   # portal at the tip 151.8, 0.94% up to Marshall
    return min(164.5, 151.8+0.0094*(s_tip-s)) if s<=s_tip else None
S_IND, S_D, S_BDJ, S_MON = 4135, 4559, 4399, 3903
def bd(s):
    if s<=S_MON: return 151.8 if s>=s_tip-200 else None
    return min(151.8+0.025*(s-S_MON), rail(s))
L=json.load(open(SP+'nv/lines.json'))
T3={o['name']:o for o in L if o['src']=='TRIMET3D'}
GR=LineString(T3['Greensburg-California 3D']['c']); APXI=max([LineString(o['c']) for o in L if o['src']=='APEx' and o['name']=='Greensburg-CUT TRIMET'],key=lambda g:g.length)
fig=plt.figure(figsize=(20,14))
ax=fig.add_axes([0.02,0.05,0.42,0.9]); ax2=fig.add_axes([0.5,0.55,0.48,0.4]); ax3=fig.add_axes([0.5,0.06,0.48,0.38])
x0,y0,x1,y1=711650,4334250,713150,4337150
win=rasterio.windows.from_bounds(x0,y0,x1,y1,DEM.transform); Z=DEM.read(1,window=win,out_shape=(int((y1-y0)/5),int((x1-x0)/5))).astype(float)/10
ax.imshow(Z,extent=(x0,x1,y0,y1),cmap='Greys_r',vmin=140,vmax=200,alpha=0.35)
ax.contourf(np.linspace(x0,x1,Z.shape[1]),np.linspace(y1,y0,Z.shape[0]),Z,levels=[0,147],colors=['#7aa6c9'],alpha=0.5)
D=json.load(open(SP+'deck/deck.json'))['features']; B=json.load(open(SP+'deckpage/basin.json'))['features']
BB=box(x0,y0,x1,y1)
for f in D:
    p=f['properties']; g=shape(f['geometry'])
    if not g.intersects(BB): continue
    if p['layer']=='deck':
        for q in getattr(g,'geoms',[g]): ax.plot(*q.exterior.xy,'k--',lw=0.7)
    if p['layer']=='street': ax.plot(*g.xy,color='#1f4f7a',lw=1.0)
for f in B:
    p=f['properties']; g=shape(f['geometry'])
    if p['layer']=='street' and g.intersects(BB): ax.plot(*g.xy,color='#999',lw=0.5 if p['kind']=='we_alley' else 0.9)
# viaduct band and pieces
def band(s0,s1,off0,off1,**k):
    seg=substring(C,s0,s1); pts=[]
    a=np.array(seg.coords)
    t=np.gradient(a,axis=0); t/=np.hypot(t[:,0],t[:,1])[:,None]; n=np.c_[-t[:,1],t[:,0]]
    ring=np.r_[a+n*off0, (a+n*off1)[::-1]]; ax.fill(ring[:,0],ring[:,1],**k)
band(s_mar,s_tip,-27.25,27.25,fc='#16252a',alpha=0.22,ec='#16252a',lw=0.6)
band(s_tip,s_lud,-28.4,28.4,fc='#d07a1c',alpha=0.30,ec='#8a4b0a',lw=0.8)
band(S_MON,S_BDJ,30,44,fc='#2a7ab0',alpha=0.35,ec='#2a7ab0',lw=0.6)
ax.plot(*substring(APXI,0,APXI.length).xy,color='#16252a',lw=1.6,ls='-.')
ax.plot(*GR.xy,color='#2a7ab0',lw=1.4,ls='-.')
LUD=[shape(f['geometry']) for f in json.load(open(SP+'lph/osm_north.geojson'))['features'] if f['properties'].get('name')=='Ludlow Avenue']
for g in LUD:
    if g.intersects(BB) and g.geom_type=='LineString': ax.plot(*g.xy,color='#b23a2e',lw=1.6)
def lab(s,t,dx=60,dy=0,c='k'):
    p=C.interpolate(s); ax.plot(p.x,p.y,'o',ms=4,color=c); ax.annotate(t,(p.x,p.y),(p.x+dx,p.y+dy),fontsize=7.5,color=c,arrowprops=dict(arrowstyle='-',lw=0.5,color=c))
lab(s_mar,'Marshall: APEx 164.5 m (arch viaduct, as now)',120)
lab(3181,'Hopple: can cross at deck level\n(viaduct 6.5 m over it, like Marshall)',120)
lab(s_tip,'deck tip: rail 166.6 m\n(was the APEx portal, 151.8 m)',140,-60)
lab(S_IND,'Arlington: APEx Indianapolis pair\nleaves west (166 m), over B/D',-560,40)
lab(S_BDJ,'TRI B/D on the viaduct (164 m)',140,-20,'#2a7ab0')
lab(S_D,'Adelaide: TRI D leaves west (163 m)',-520,60,'#2a7ab0')
lab(4895,'Whiteley: 7.4 m clear (least, Millvale)',140)
lab(s_lud,'Ludlow Ave: rails at ground, 155.5 m;\nLudlow keeps its bridge (10v.5)',120,-40,'#b23a2e')
ax.text(712950,4334320,'blue fill: I-75 trench (map 3)',fontsize=7,color='#2a5a80')
ax.set_xlim(x0,x1); ax.set_ylim(y0,y1); ax.set_aspect('equal'); ax.tick_params(labelsize=6); ax.grid(lw=0.2)
ax.set_title('North trunk viaduct, Marshall to Ludlow (proposal)',fontsize=11,loc='left')
# long section
ss=np.arange(2400,6000,10)
ax2.plot(ss,[gz(*C.interpolate(s).coords[0]) for s in ss],color='#8a6a3a',lw=1,label='ground / deck surface (map 3)')
ax2.plot(ss,[rail(s) for s in ss],color='#d07a1c',lw=2.2,label='APEx + ORR, proposed (10 tracks)')
ax2.plot(ss,[old_apex(s) for s in ss],color='#16252a',lw=1,ls='--',label='APEx now (portal at the tip, 0.94%)')
ax2.plot(ss,[bd(s) for s in ss],color='#2a7ab0',lw=1.8,label='TRI B/D, proposed')
t3=np.array(T3['Dayton-Independence 3D']['c']); z3=np.array(T3['Dayton-Independence 3D']['z'])
st=[C.project(Point(q)) for q in t3]; m=[(s,z) for s,z,q in zip(st,z3,t3) if 2400<s<6000 and C.distance(Point(q))<40]
ax2.plot([a for a,b in m],[b for a,b in m],color='#2a7ab0',lw=0.8,ls=':',label='TRI B/D now (TRIMET 3D)')
for nm,lb,s,x,y,z in V['rows']:
    if lb!='APEx/ORR': continue
    ax2.plot([s,s],[z,rail(s)],color='#1f4f7a',lw=0.6); ax2.plot(s,z,'v',ms=3,color='#1f4f7a')
    ax2.text(s,z-1.2,nm.split()[0],rotation=90,fontsize=5.5,ha='center',va='top',color='#1f4f7a')
for s,t in ((s_mar,'Marshall'),(3181,'Hopple'),(s_tip,'deck tip'),(S_IND,'Indy pair leaves'),(S_D,'TRI D leaves'),(s_lud,'Ludlow')):
    ax2.axvline(s,color='#999',lw=0.5); ax2.text(s,171.5,t,rotation=90,fontsize=6.5,va='top',ha='right')
ax2.set_ylim(140,172); ax2.set_xlim(2400,6000); ax2.legend(fontsize=6.5,loc='lower left'); ax2.grid(lw=0.2); ax2.tick_params(labelsize=7)
ax2.set_xlabel('m along the APEx line from CUT',fontsize=7); ax2.set_ylabel('m',fontsize=7)
ax2.set_title('Long section: 0.75% up from Ludlow to the arch-viaduct level, held over the deck to Marshall',fontsize=9,loc='left')
# cross sections
def xsec(y0,title,tracks):
    w=4.75; xs=[]; x=0
    for i,(g,n) in enumerate(tracks):
        if i: x+=(4.5 if g.startswith('APEx') and tracks[i-1][0].startswith('APEx') else 6.75)
        for k in range(n): xs.append((x,g)); x+=4.5
        x-=4.5
    span=xs[-1][0]-xs[0][0]; W=span+2*w
    ax3.add_patch(Rectangle((-w,y0),W,1.2,fc='#ddd',ec='k',lw=0.6))
    colc={'APEx':'#16252a','ORR':'#b0207a','TRI':'#2a7ab0'}
    for x,g in xs: ax3.plot([x-0.72,x+0.72],[y0+1.25,y0+1.25],color=colc[g.split()[0]],lw=3); 
    gx={}
    for x,g in xs: gx.setdefault(g,[]).append(x)
    for g,v in gx.items(): ax3.text(np.mean(v),y0+2.1,g,ha='center',fontsize=7,color=colc[g.split()[0]])
    ax3.text(-w,y0+4.2,'%s: %d tracks, %.2f m between outer tracks, deck %.1f m' % (title,len(xs),span,W),fontsize=8)
    return W
xsec(10,'Deck tip to Arlington',[('ORR W',2),('APEx Indy',2),('APEx Dayton+Norwood',4),('ORR E',2)])
ax3.text(-4.75,8.3,'+ TRI B/D (2) rising 2.5% in an open ramp beside the west edge, from a box under Monmouth; the Indianapolis pair crosses over ORR W and the ramp to leave west',fontsize=7,color='#2a7ab0')
xsec(0,'Arlington to Ludlow',[('TRI B/D',2),('ORR W',2),('APEx Dayton+Norwood',4),('ORR E',2)])
ax3.set_xlim(-8,70); ax3.set_ylim(-2,16); ax3.axis('off')
ax3.set_title('Cross sections (looking north). Spacing 4.5 m in a group, 6.75 m between groups (as drawn at CUT);\n4.75 m from the outer track to the deck edge (14 m double-track HSR deck at 4.5 m centres)',fontsize=8,loc='left')
plt.savefig(SP+'nv/North_Trunk_Viaduct_sketch.png',dpi=110)
