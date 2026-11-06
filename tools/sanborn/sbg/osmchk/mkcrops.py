import pickle, json, sys, numpy as np, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
sys.path.insert(0,'osmchk'); sys.path.insert(0,'fit')
import crop as C
from viz3 import mosaic
R=pickle.load(open('osmchk/runs2.pkl','rb'))
KNOWN={'Eggleston Avenue','West Liberty Street','East Liberty Street','Linn Street','Freeman Avenue','Harrison Avenue','Gest Street','East Central Parkway','East Central Parkway (E.N. Canal)','East Central Parkway (E.S. Canal)','West Central Parkway','Central Parkway','Winchell Avenue','West McMicken Avenue','Garfield Place'}
A=[r for r in R['RA'] if r['L']>=40 and r['med']>3.0]
B=R['keepB']
items=[]
for i,r in enumerate(sorted(A,key=lambda r:-r['L'])): items.append(dict(id=f'A{i+1:03d}',typ='A',name=r['name'],osm=r['osm'],L=r['L'],med=round(r['med'],1),x=r['x'],y=r['y'],pts=r['pts']))
for i,r in enumerate(sorted(B,key=lambda r:-r['L'])): items.append(dict(id=f'B{i+1:03d}',typ='B',name=r['name'],hw=r['hw'],L=r['L'],x=r['x'],y=r['y'],pts=r['pts']))
def render(it):
    pts=np.array(it['pts']); cx,cy=(pts.max(0)+pts.min(0))/2; ext=np.ptp(pts,axis=0).max()
    half=float(np.clip(ext/2+45,70,230))
    x0,y0,x1,y1=cx-half,cy-half,cx+half,cy+half
    img=mosaic((x0,y0,x1,y1),0.25 if half<=170 else 0.4)
    px=1050; fig=plt.figure(figsize=(px/100,px/100),dpi=100); ax=fig.add_axes([0,0,1,1]); ax.imshow(img,extent=[x0,x1,y0,y1])
    ax.plot(pts[:,0],pts[:,1],'o',color='#ffd400',ms=9,alpha=0.35,mec='none',zorder=1)
    sc=px/(2*half)*0.72
    for f in C.L:
        p=f['properties']
        if p['layer']!='street': continue
        c=np.array(f['geometry']['coordinates'])
        if c[:,0].max()<x0 or c[:,0].min()>x1 or c[:,1].max()<y0 or c[:,1].min()>y1: continue
        ax.plot(c[:,0],c[:,1],color='#e00000',lw=1.2,zorder=3)
        m=c.mean(0)
        if x0<m[0]<x1 and y0<m[1]<y1 and p['name']: ax.text(m[0],m[1]+3,p['name'][:20],color='#b00000',fontsize=7,zorder=5)
    for f in C.OSM:
        h=f['properties'].get('highway')
        if h in ('footway','steps','path','cycleway','corridor'): continue
        c=np.array(f['geometry']['coordinates'])
        if c[:,0].max()<x0 or c[:,0].min()>x1 or c[:,1].max()<y0 or c[:,1].min()>y1: continue
        ax.plot(c[:,0],c[:,1],color='#0050ff',lw=1.2,ls=(0,(4,3)),zorder=4)
        n=f['properties'].get('name')
        if n:
            m=c[len(c)//2]
            if x0<m[0]<x1 and y0<m[1]<y1: ax.text(m[0],m[1]-7,n[:20],color='#0035b0',fontsize=7,zorder=5)
    t=f"{it['id']}  " + (f"basin '{it['name']}' vs OSM '{it['osm']}', median {it['med']} m over {it['L']} m" if it['typ']=='A' else f"OSM '{it['name']}' ({it['hw']}), {it['L']} m with no basin street")
    ax.text(x0+4,y1-4,t,fontsize=9,va='top',bbox=dict(fc='w',alpha=0.85),zorder=6)
    ax.plot([x1-54,x1-4],[y0+8,y0+8],'k-',lw=3); ax.text(x1-54,y0+12,'50 m',fontsize=8)
    ax.set_xlim(x0,x1); ax.set_ylim(y0,y1); ax.set_xticks([]); ax.set_yticks([])
    fig.savefig(f"osmchk/crops/{it['id']}.png"); plt.close(fig)
for it in items: render(it)
json.dump([{k:v for k,v in it.items() if k!='pts'} for it in items],open('osmchk/items.json','w'),indent=0)
pickle.dump(items,open('osmchk/items.pkl','wb'))
print(len(items), sum(1 for i in items if i['typ']=='A'), sum(1 for i in items if i['typ']=='B'))
