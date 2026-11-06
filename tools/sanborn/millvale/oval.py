try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, sys, numpy as np, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from shapely.geometry import LineString, Polygon, Point
from shapely import affinity
SP=_ws.DATA
sys.argv=[sys.argv[0]]
exec(open(_ws.CODE+'millvale/panhandle.py').read().split("if __name__ == '__main__'")[0])
# D. Columbus Circle: an oval rotary centred on the crossing, long axis on the boulevard; every road meets the ring
X=B.intersection(F); cx,cy=X.coords[0]
p=np.array(B.interpolate(B.project(X)).coords[0]); q=np.array(B.interpolate(B.project(X)+1).coords[0]); ang=np.degrees(np.arctan2(*(q-p)[::-1]))
A_, B_ = 95.0, 48.0; RW = 14.0
def ell(a,b): return affinity.rotate(affinity.scale(Point(cx,cy).buffer(1,resolution=64),a,b),ang,origin=(cx,cy))
ring=LineString(ell(A_,B_).exterior.coords); parkD=ell(A_-RW/2,B_-RW/2)
SD=[]
for n,g,w in ST:
    if n in ('Millvale Boulevard','Follett Avenue (carried south)','New street M4','New street M5'):
        g=g.difference(ell(A_,B_).buffer(-0.5))
    for qq in getattr(g,'geoms',[g]):
        if qq.geom_type=='LineString' and qq.length>3: SD.append((n,qq,w))
SD.append(('ring',ring,RW))
bD,bandsD=blocks(SD,extra=parkD)
legs=[]
for n,g,w in SD:
    if n=='ring': continue
    x=g.intersection(ring)
    for pt in getattr(x,'geoms',[x]):
        if not pt.is_empty and pt.geom_type=='Point': legs.append(pt.coords[0])
fig,axs=plt.subplots(1,2,figsize=(13.5,7.8))
draw(axs[0],SP2,bP,bandsP,'B, Panhandle version (Fell/Oak)',park=park,signals=sig,
     notes=['Boulevard splits into two one-way carriageways on its own line; park between (%.2f ha, 250 m long)'%(park.area/1e4),
            'South-west-bound on the west side, north-east-bound on the east; boulevard traffic never turns',
            'Follett ends on the carriageways and uses them for 3 blocks; M4 and M5 end at them'])
for line,lab in ((cwW,'SW'),(cwE,'NE')):
    a=line.interpolate(0.45,normalized=True); b=line.interpolate(0.52 if lab=='SW' else 0.38,normalized=True)
    axs[0].annotate('',xy=(b.x,b.y),xytext=(a.x,a.y),arrowprops=dict(arrowstyle='-|>',color='k',lw=1.2))
draw(axs[1],SD,bD,bandsD,'D. Columbus Circle: an oval rotary',park=parkD,signals=[],
     notes=['A %d x %d m oval on the boulevard line, park in the middle (%.2f ha), one-way ring'%(2*A_,2*B_,parkD.area/1e4),
            'Boulevard, Follett, M4 and M5 all enter the ring (%d entries); no signals inside'%len(legs),
            'Smoother than B for the avenue, but boulevard traffic weaves around half the ring'])
for (x,y) in legs: axs[1].plot(x,y,'s',ms=5,mfc='white',mec='k')
a=ring.interpolate(0.10,normalized=True); b=ring.interpolate(0.13,normalized=True); axs[1].annotate('',xy=(b.x,b.y),xytext=(a.x,a.y),arrowprops=dict(arrowstyle='-|>',color='k',lw=1.2))
h=[plt.Line2D([],[],color='#2a6fd6',ls=(0,(4,3)),label='culverts'),plt.Rectangle((0,0),1,1,fc='none',ec='#c0392b',hatch='////',label='viaducts (no blocks under)'),
   plt.Line2D([],[],marker='o',ls='',mfc='#f1c40f',mec='k',label='signalled junction'),plt.Line2D([],[],marker='s',ls='',mfc='white',mec='k',label='yield entry'),plt.Rectangle((0,0),1,1,fc='#7fc27f',ec='#2f7d2f',label='park')]
fig.legend(handles=h,loc='lower center',ncol=5,fontsize=8,frameon=False)
plt.suptitle('Millvale, M3 to M6: the Panhandle version of B, and a rotary alternative (all at grade over the culverts)',fontsize=11)
plt.tight_layout(rect=(0,0.04,1,0.95)); plt.savefig(SP+'millvale/m3m6_BD.png',dpi=100)
print('oval park', round(parkD.area/1e4,2), 'legs', len(legs), 'ang', round(ang))
