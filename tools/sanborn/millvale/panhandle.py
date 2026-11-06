try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Option B, Panhandle version (Ben: Fell/Oak along the SF Panhandle): the boulevard splits into two one-way carriageways that run straight
# along its own line either side of a park from M3 to M6, then rejoin; Follett traffic shares them for the three blocks.
import json, sys, numpy as np, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MP
from shapely.geometry import shape, LineString, Polygon, box, Point
from shapely.ops import unary_union, polygonize, substring
SP=_ws.DATA
exec(open(_ws.CODE+'millvale/m3m6_options.py').read().split("fig,axs=plt.subplots")[0])      # shared data and helpers (ST, G, B, F, keep, blocks, draw, hull...)
D_PARK, CW = 27.0, 14.0             # carriageway centre lines 27 m either side of the boulevard line (a park about 40 m wide between them); 14 m each (3 one-way lanes + kerbs)
s2, s3, s6, s7 = [B.project(B.intersection(G[f'New street M{k}'][0])) for k in (2, 3, 6, 7)]
def sstep(t): t = np.clip(t, 0, 1); return t * t * (3 - 2 * t)
def doff(s): return D_PARK * (sstep((s - s2) / (s3 - s2)) if s < s3 else (1.0 if s <= s6 else sstep((s7 - s) / (s7 - s6))))
ss = np.linspace(s2 - 30, s7 + 30, 400)
def side(sign):
    pts = []
    for s in ss:
        p = np.array(B.interpolate(s).coords[0]); q = np.array(B.interpolate(min(s + 1, B.length)).coords[0]); tdir = (q - p) / np.linalg.norm(q - p)
        n = np.array([-tdir[1], tdir[0]])            # left of travel (travel runs NE -> SW, so left is south-east)
        pts.append(p + sign * n * doff(s))
    return LineString(pts)
cwE, cwW = side(+1), side(-1)                          # east (south-east) carriageway: north-east-bound; west: south-west-bound (keep right)
inner = [s for s in ss if doff(s) > CW / 2 + 1]
def edge(sign, s_list): return [ (np.array(B.interpolate(s).coords[0]) + sign * (lambda p, q: np.array([-(q - p)[1], (q - p)[0]]) / np.linalg.norm(q - p))(np.array(B.interpolate(s).coords[0]), np.array(B.interpolate(min(s + 1, B.length)).coords[0])) * (doff(s) - CW / 2)) for s in s_list]
park = Polygon(edge(+1, inner) + edge(-1, inner[::-1]))
corr = Polygon(list(cwE.coords) + list(cwW.coords)[::-1]).buffer(0)
SP2 = []
bfull = B
for n, g, w in ST:
    if n == 'Millvale Boulevard':
        # keep the boulevard outside the split; the two carriageways replace it between
        for q in (substring(g, 0, s2 - 30), substring(g, s7 + 30, g.length)): SP2.append((n, q, w))
        continue
    if n == 'Follett Avenue (carried south)':
        cut = g.difference(corr.buffer(0.5))
        parts = [q for q in getattr(cut, 'geoms', [cut]) if q.geom_type == 'LineString' and q.length > 3]
        for q in parts: SP2.append((n, q, w))
        continue
    if n in ('New street M4', 'New street M5'):
        cut = g.difference(corr.buffer(-CW / 2))
        for q in getattr(cut, 'geoms', [cut]):
            if q.geom_type == 'LineString' and q.length > 3: SP2.append((n, q, w))
        continue
    SP2.append((n, g, w))
SP2 += [('Millvale Boulevard (north-east-bound)', cwE, CW), ('Millvale Boulevard (south-west-bound)', cwW, CW)]
bP, bandsP = blocks(SP2, extra=park)
# Follett ends on the carriageways, junctions
fj = [q for n, q, w in SP2 if n.startswith('Follett')]
sig = [cwW.intersection(G['New street M3'][0]).coords[0], cwE.intersection(G['New street M3'][0]).coords[0], cwW.intersection(G['New street M6'][0]).coords[0], cwE.intersection(G['New street M6'][0]).coords[0]]
for q in fj:
    for e in (q.coords[0], q.coords[-1]):
        if corr.buffer(2).contains(Point(e)): sig.append(e)
if __name__ == '__main__' and '--plot' in sys.argv:
    fig, axs = plt.subplots(1, 2, figsize=(13.5, 7.8))
    # B as before
    SB=[]
    for n,g,w in ST:
        if n in ('Millvale Boulevard','Follett Avenue (carried south)'): g=g.difference(hull.buffer(0.5))
        elif n in ('New street M4','New street M5'): g=g.difference(hull.buffer(11))
        for q in getattr(g,'geoms',[g]):
            if q.geom_type=='LineString' and q.length>3: SB.append((n,q,w))
    eE=LineString([pB3.coords[0],pF6.coords[0]]); eW=LineString([pF3.coords[0],pB6.coords[0]])
    def outward(e,ref):
        a=e.parallel_offset(11,'left'); b=e.parallel_offset(11,'right'); return a if a.distance(ref)>b.distance(ref) else b
    SB+=[('edge E',LineString([pB3.coords[0]]+list(outward(eE,hull.centroid).coords)+[pF6.coords[0]]),22.0),('edge W',LineString([pF3.coords[0]]+list(outward(eW,hull.centroid).coords)+[pB6.coords[0]]),22.0)]
    bB,bandsB=blocks(SB,extra=hull)
    draw(axs[0],SB,bB,bandsB,'B as drawn: the boulevard turns twice',park=hull.difference(bandsB),signals=[pB3.coords[0],pF3.coords[0],pB6.coords[0],pF6.coords[0]],
         notes=['Boulevard traffic jogs to the park edge at one end and back at the other'])
    draw(axs[1],SP2,bP,bandsP,'B, Panhandle version (Fell/Oak)',park=park,signals=sig,
         notes=['The boulevard splits into two one-way carriageways on its own line, park between (%.2f ha)'%(park.area/1e4),
                'South-west-bound on the west side, north-east-bound on the east; they rejoin past M6',
                'Follett ends on them between M3 and M4 and resumes between M5 and M6; M4 and M5 end at them'])
    for ax in axs:
        for n,g,w in SP2:
            pass
    h=[plt.Line2D([],[],color='#2a6fd6',ls=(0,(4,3)),label='culverts'),plt.Rectangle((0,0),1,1,fc='none',ec='#c0392b',hatch='////',label='viaducts (no blocks under)'),
       plt.Line2D([],[],marker='o',ls='',mfc='#f1c40f',mec='k',label='signalled junction'),plt.Rectangle((0,0),1,1,fc='#7fc27f',ec='#2f7d2f',label='park')]
    fig.legend(handles=h,loc='lower center',ncol=4,fontsize=8,frameon=False)
    # arrows for one-way flow
    for line,lab in ((cwW,'SW-bound'),(cwE,'NE-bound')):
        a=line.interpolate(0.45,normalized=True); b=line.interpolate(0.52 if lab=='SW-bound' else 0.38,normalized=True)
        axs[1].annotate('',xy=(b.x,b.y),xytext=(a.x,a.y),arrowprops=dict(arrowstyle='-|>',color='k',lw=1.2))
    plt.suptitle('Millvale, M3 to M6: option B and its Panhandle version (all at grade over the culverts)',fontsize=11)
    plt.tight_layout(rect=(0,0.04,1,0.95)); plt.savefig(SP+'millvale/m3m6_panhandle.png',dpi=100)
    print('park ha', round(park.area/1e4,2), 'length', round(s6-s3), 'corridor width', round(2*D_PARK+CW))
