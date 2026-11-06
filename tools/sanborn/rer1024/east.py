try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
exec(open((_ws.CODE + 'rer1024/geo.py')).read())
U=exist_union()
Gr=deck[::-1]; sDr=sD[::-1]
Wn=Wc[::-1]; Wn=Wn[(Wn[:,1]>4335300)&(Wn[:,1]<4336300)]
m=(sDr>1700)&(sDr<2500)
for k in (0.0,-4.0,-6.5):
    Gk=(Gr+normals(Gr)*(-k))[m]   # negative k = SW? (k>0 is NE / right of NW travel)
    for R in (150,200,300,400,500,700,1000,1500):
        for iJ,O,K in tangent_arc(Wn, Gk, R, +1, +1):
            J=Gk[int(iJ)]; arc=arc_pts(O,K,J,R,+1)
            fp=LineString(arc).buffer(4.2).difference(U)
            print('east k',k,'R',R,'leaves W pair at N',round(K[1]),'J at D s',round(sDr[m][int(iJ)]),'arc len',round(LineString(arc).length),'extra m2',round(fp.area),'max out',round(max(Point(p).distance(U) for p in arc),1))
