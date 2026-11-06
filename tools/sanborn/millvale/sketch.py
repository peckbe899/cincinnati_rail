try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, numpy as np, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from shapely.geometry import shape, Polygon, LineString, Point
SP=_ws.DATA
P=Polygon(json.load(open(SP+'millvale/grid_area.json'))); d=json.load(open(SP+'millvale/blvd2.json')); LA=LineString(d['blvd']); LB=LineString(d['old'])
c=json.load(open(SP+'deckpage/context.json')); t=json.load(open(SP+'deckpage/tracks.json'))
th=np.radians(3.0); u=np.array([np.sin(th),np.cos(th)]); v=np.array([np.cos(th),-np.sin(th)])     # u along 3 deg (N-S), v along 93 deg (E-W)
def nsline(x0): p=np.array([x0,4336650.0]); return LineString([p-u*2500,p+u*400])
def ewline(y0): p=np.array([711900.0,y0]); return LineString([p-v*1500,p+v*1500])
opts={
 '1  Manhattan as built: avenues run with the valley, ~260 m apart; streets cross it every ~80 m':
   dict(ns=[(711815,'Borden Av.'),(712075,'Follett Av.')], ew=[4336650-80*i for i in range(23)], nsw=30, eww=18),
 '2  Turned 90 degrees: the South Cumminsville streets run on south (~90 m apart); avenues cross every ~250 m':
   dict(ns=[(711729,'Llewellyn'),(711815,'Borden'),(711918,'Dawson'),(711998,'Roll'),(712075,'Follett'),(712160,''),(712245,'')], ew=[4336650,4336476]+[4336476-250*i for i in range(1,7)], nsw=18, eww=30)}
fig,axs=plt.subplots(1,2,figsize=(15,13))
for ax,(title,o) in zip(axs,opts.items()):
    ax.set_aspect('equal'); x,y=P.exterior.xy; ax.fill(x,y,color='#f3efe4',ec='k',lw=1)
    sq=[]
    for x0,nm in o['ns']:
        g=nsline(x0).intersection(P)
        for gg in getattr(g,'geoms',[g]):
            if gg.is_empty: continue
            xx,yy=gg.buffer(o['nsw']/2,cap_style=2).exterior.xy; ax.fill(xx,yy,color='0.55')
        if nm: m=g.interpolate(0.5,normalized=True) if not g.is_empty else None; m and ax.text(m.x+8,m.y,nm,rotation=87,fontsize=7)
        for L in (LA,LB):
            xp=nsline(x0).intersection(L)
            if not xp.is_empty and P.buffer(1).contains(xp.centroid): sq.append(xp.centroid)
    for y0 in o['ew']:
        g=ewline(y0).intersection(P)
        for gg in getattr(g,'geoms',[g]):
            if gg.is_empty: continue
            xx,yy=gg.buffer(o['eww']/2,cap_style=2).exterior.xy; ax.fill(xx,yy,color='0.55')
    for f in c['rer']:
        g=LineString(f['c']).intersection(P)
        if not g.is_empty and 'RER' in f['name'] and ('A' in f['name'] or 'D' in f['name']):
            for gg in getattr(g,'geoms',[g]): xx,yy=gg.xy; ax.plot(xx,yy,color='orange',lw=3,ls='--')
    for f in t['features']:
        if f['properties'].get('name')=='APEx north approach 5 of 6':
            g=shape(f['geometry']).intersection(P)
            for gg in getattr(g,'geoms',[g]): xx,yy=gg.xy; ax.plot(xx,yy,color='r',lw=4,alpha=0.5)
    for L,ls in ((LA,'-'),(LB,'--')):
        g=L.intersection(P.buffer(20))
        for gg in getattr(g,'geoms',[g]): xx,yy=gg.xy; ax.plot(xx,yy,'g',lw=7,alpha=0.6,ls=ls)
    for s in sq: ax.add_patch(plt.Circle((s.x,s.y),28,color='g',alpha=0.35)); 
    for s in c['stations']+c['rer_stations']:
        p=Point(s['p'])
        if p.distance(P)<60: ax.plot(p.x,p.y,'ko',ms=5); ax.text(p.x+12,p.y+8,s['name'],fontsize=7)
    ax.set_title(title,fontsize=9); ax.set_xlim(711450,712500); ax.set_ylim(4334800,4336760); ax.tick_params(labelsize=6)
    ax.text(711470,4334830,f'boulevard crossings of N-S lines (squares): {len(sq)}',fontsize=8)
axs[0].plot([],[],'g',lw=7,alpha=0.6,label='boulevard'); axs[0].plot([],[],'g--',lw=7,alpha=0.6,label='old boulevard to Hopple')
axs[0].plot([],[],color='r',lw=4,alpha=0.5,label='APEx Indianapolis + RER D deck (viaduct)'); axs[0].plot([],[],color='orange',lw=3,ls='--',label='RER A / RER D (context lines)')
axs[0].legend(loc='upper left',fontsize=7)
plt.suptitle('Millvale grid area: Dreman, Geringer, the rail trunk, Hopple, Beekman (90 ha). Grey = streets (sketch widths), green circles = squares',fontsize=10)
plt.tight_layout(); plt.savefig(SP+'millvale/grid_options.png',dpi=85)
