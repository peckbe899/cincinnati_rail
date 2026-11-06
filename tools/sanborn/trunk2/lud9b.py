try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
exec(open((_ws.CODE + 'trunk2/lud9.py')).read().split('best=[]')[0])
for args in ((-5,1000,62,0),(-5,700,62,3),(-5,1200,63,-3)):
    c,TC,CT=route(*args); o=offsets(c)
    print(args,'TC',round(G.C.project(Point(TC))),'CT',round(G.C.project(Point(CT))))
    for s,oo,a,b in zip(ss[::5],o[::5],lo[::5],hi[::5]):
        if 5250<=s<=7300: print('  ',int(s),round(oo,1),round(a,1),round(b,1),'X' if not (a<=oo<=b) else '')
