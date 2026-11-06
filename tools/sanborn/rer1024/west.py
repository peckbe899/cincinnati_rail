try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
exec(open((_ws.CODE + 'rer1024/geo.py')).read())
U=exist_union()
Gr=deck[::-1]; sDr=sD[::-1]
tr=trunk[(ts>4700)&(ts<5400)]
m=(sDr>1450)&(sDr<2000)
for k in (0.0, 4.0, 6.5):
    Gk=(Gr+normals(Gr)*(-k))[m]
    for R in (100,150,200,250,300,400):
        sols=tangent_arc(tr, Gk, R, -1, -1)
        for iJ,O,K in sols:
            sk=LineString(trunk).project(Point(K)); J=Gk[int(iJ)]
            arc=arc_pts(O,J,K,R,-1)
            fp=LineString(arc).buffer(4.2).difference(U)
            print('west k',k,'R',R,'J at D s',round(sDr[m][int(iJ)]),'joins trunk s',round(sk),'extra structure m2',round(fp.area), 'max out', round(max(Point(p).distance(U) for p in arc),1))
