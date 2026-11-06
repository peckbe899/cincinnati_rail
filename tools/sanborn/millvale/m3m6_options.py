try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, numpy as np, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MP
from shapely.geometry import shape, LineString, Polygon, MultiPoint, box, Point
from shapely.ops import unary_union, polygonize
SP=_ws.DATA
X0,Y0,X1,Y1=711860,4335960,712300,4336440; W=box(X0,Y0,X1,Y1)
d=json.load(open(SP+'millvale/ext_mv.json')); t=json.load(open(SP+'deckpage/tracks.json')); c=json.load(open(SP+'deckpage/context.json'))
ST=[(f['properties']['name'],shape(f['geometry']),f['properties']['width_m']) for f in d['features'] if f['properties']['layer']=='street' and shape(f['geometry']).intersects(W.buffer(200))]
G={n:(g,w) for n,g,w in ST}
B,bw=G['Millvale Boulevard']; F,fw=G['Follett Avenue (carried south)']; M3=G['New street M3'][0]; M6=G['New street M6'][0]
trk=lambda nm:[shape(f['geometry']) for f in t['features'] if f['properties'].get('name')==nm][0]
rails=[trk('APEx north approach 5 of 6'),trk('APEx north approach 6 of 6'),trk('R5 to the Cumminsville Spur (west track)'),trk('R5 to the Cumminsville Spur (east track)')]+[LineString(f['c']) for f in c['tracks'] if f.get('sys')=='rer' and f.get('line') in ('D','A')]
keep=unary_union([r.buffer(6) for r in rails]).buffer(10).buffer(-10)
pB3,pF3,pB6,pF6=B.intersection(M3),F.intersection(M3),B.intersection(M6),F.intersection(M6)
hull=Polygon([pF3.coords[0],pB3.coords[0],pF6.coords[0],pB6.coords[0]]).convex_hull
def blocks(streets, extra=None):
    net=unary_union([g for n,g,w in streets]+[W.exterior])
    bands=unary_union([g.buffer(w/2,cap_style=2,join_style=2) for n,g,w in streets])
    out=[]
    for q in polygonize(net):
        r=q.intersection(W).difference(bands).difference(keep)
        if extra is not None: r=r.difference(extra)
        for p in getattr(r,'geoms',[r]):
            if p.geom_type=='Polygon' and p.area>120: out.append(p)
    return out,bands
def draw(ax,streets,blks,bands,title,square=None,plazas=(),park=None,signals=(),notes=()):
    ax.set_aspect('equal'); ax.add_patch(MP(np.array(W.exterior.coords),fc='white',ec='none'))
    for g in getattr(bands,'geoms',[bands]):
        if g.geom_type=='Polygon': ax.add_patch(MP(np.array(g.exterior.coords),fc='#d9d9d9',ec='#a0a0a0',lw=0.4))
    if square is not None:
        for g in getattr(square,'geoms',[square]): ax.add_patch(MP(np.array(g.exterior.coords),fc='#c4c4c4',ec='k',lw=1.2,ls='--'))
    for b in blks: ax.add_patch(MP(np.array(b.exterior.coords),fc='#e8c9a0',ec='#9a6a3a',lw=0.6))
    for p in plazas: ax.add_patch(MP(np.array(p.exterior.coords),fc='#9fd39f',ec='#2f7d2f',lw=0.8))
    if park is not None: ax.add_patch(MP(np.array(park.exterior.coords),fc='#7fc27f',ec='#2f7d2f',lw=1.2))
    # culverts
    x,y=B.xy; ax.plot(x,y,color='#2a6fd6',ls=(0,(4,3)),lw=1.4)
    wf=unary_union(rails[:2]).centroid
    for r in rails[:1]: x,y=r.xy; ax.plot(x,y,color='#2a6fd6',ls=(0,(4,3)),lw=1.4)
    # viaduct outline
    for g in getattr(keep.intersection(W),'geoms',[keep.intersection(W)]):
        if g.geom_type=='Polygon': ax.add_patch(MP(np.array(g.exterior.coords),fc='none',ec='#c0392b',lw=1.0,hatch='////',alpha=0.55))
    for s in signals: ax.plot(*s,'o',ms=7,mfc='#f1c40f',mec='k')
    for n,g,w in streets:
        if n.startswith('New street M') and g.intersects(W):
            p=g.intersection(W); p=p.interpolate(0.08,normalized=True) if p.length else None
            if p: ax.text(p.x,p.y+3,n.replace('New street ',''),fontsize=7,color='0.25')
    ax.text(712063,4336425,'Follett',fontsize=7,rotation=87,color='0.25'); ax.text(712150,4336400,'Boulevard',fontsize=7,rotation=58,color='0.25')
    ax.set_xlim(X0,X1); ax.set_ylim(Y0,Y1); ax.set_xticks([]); ax.set_yticks([]); ax.set_title(title,fontsize=10,loc='left')
    for i,nt in enumerate(notes): ax.text(X0+5,Y0+8+14*(len(notes)-1-i),nt,fontsize=7.2,va='bottom',bbox=dict(fc='white',ec='none',alpha=0.8,pad=1))
fig,axs=plt.subplots(1,3,figsize=(18,7.6))
# A: bowtie
SA=ST; bA,bandsA=blocks(SA)
sqA=unary_union([B.buffer(bw/2,cap_style=2),F.buffer(fw/2,cap_style=2)]).intersection(hull.buffer(28))
plA=[b for b in bA if b.area<2000 and b.distance(hull)<40]; bA=[b for b in bA if b not in plA]
draw(axs[0],SA,bA,bandsA,'A. Times Square bowtie',square=sqA,plazas=plA,signals=[pB3.coords[0],pF3.coords[0],B.intersection(F).coords[0],pB6.coords[0],pF6.coords[0]],
     notes=['Both roads run through; the overlap (dashed) is one paved, signalled square','The three leftover wedges become small plazas (green)','About 250 m of crossing traffic under the viaduct'])
# B: Union Square park
off=11.0
eE=LineString([pB3.coords[0],pF6.coords[0]]); eW=LineString([pF3.coords[0],pB6.coords[0]])
def outward(e,ref):
    a=e.parallel_offset(off,'left'); b=e.parallel_offset(off,'right'); return a if a.distance(ref)>b.distance(ref) else b
ce=hull.centroid; eE2=outward(eE,ce); eW2=outward(eW,ce)
def cut_out(g): return g.difference(hull.buffer(0.5))
SB=[]
for n,g,w in ST:
    if n in ('Millvale Boulevard','Follett Avenue (carried south)'): g=cut_out(g)
    elif n in ('New street M4','New street M5'): g=g.difference(hull.buffer(off))
    for q in getattr(g,'geoms',[g]):
        if q.geom_type=='LineString' and q.length>3: SB.append((n,q,w))
# links from the cut road ends to the edge roads
SB+=[('edge E',LineString([pB3.coords[0]]+list(eE2.coords)+[pF6.coords[0]]),22.0),('edge W',LineString([pF3.coords[0]]+list(eW2.coords)+[pB6.coords[0]]),22.0)]
parkB=hull.buffer(-0.01)
bB,bandsB=blocks(SB,extra=hull)
draw(axs[1],SB,bB,bandsB,'B. Union Square park',park=hull.difference(bandsB),signals=[pB3.coords[0],pF3.coords[0],pB6.coords[0],pF6.coords[0]],
     notes=['The ground between the roads from M3 to M6 is a park, about %.1f ha,'%(hull.difference(bandsB).area/1e4),'over both culverts and under the viaduct','Traffic runs one way along each edge; M4 and M5 end at the park'])
# C: Follett stops at the boulevard
SC=[]
for n,g,w in ST:
    if n=='Follett Avenue (carried south)': g=g.difference(B.buffer(bw/2+0.5,cap_style=2))
    for q in getattr(g,'geoms',[g]):
        if q.geom_type=='LineString' and q.length>3: SC.append((n,q,w))
bC,bandsC=blocks(SC)
fp=[p for p in getattr(F.intersection(B.buffer(bw/2+0.5,cap_style=2).boundary),'geoms',[])]
draw(axs[2],SC,bC,bandsC,'C. Follett stops at the boulevard',signals=[q.coords[0] for q in fp][:2]+[pB3.coords[0],pB6.coords[0]],
     notes=['Follett ends at the boulevard between M3 and M4 and starts again between M5 and M6','The boulevard carries the avenue traffic for those blocks','The Follett strip goes to the blocks beside it; no square'])
h=[plt.Line2D([],[],color='#2a6fd6',ls=(0,(4,3)),label='culverts (Mill Creek, West Fork)'),plt.Rectangle((0,0),1,1,fc='none',ec='#c0392b',hatch='////',label='APEx Indianapolis + RER D deck, R5, RER A (no blocks under)'),
   plt.Line2D([],[],marker='o',ls='',mfc='#f1c40f',mec='k',label='signalled junction'),plt.Rectangle((0,0),1,1,fc='#e8c9a0',ec='#9a6a3a',label='blocks')]
fig.legend(handles=h,loc='lower center',ncol=4,fontsize=8,frameon=False)
plt.suptitle('Millvale, M3 to M6: where Follett and the boulevard cross at 21 degrees under the viaduct (all at grade: the culverts are below)',fontsize=11)
plt.tight_layout(rect=(0,0.04,1,0.95)); plt.savefig(SP+'millvale/m3m6_options.png',dpi=100)
print('park ha', round(hull.difference(bandsB).area/1e4,2))
