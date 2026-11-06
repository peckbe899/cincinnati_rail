try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Ben 2026-10-19: sheet 168 refit (lph/refit168.py, affine) plus a thin-plate spline on its residuals, so the sheet lands exactly on
# its fixed control: the Reading/Elsinore crossing (fixed sheets 159/160), the Gilbert/Elsinore corner and Gilbert's centre near the
# top of the sheet (OSM; Gilbert unchanged along Eden Park), and the four crossings of the 167/168 match line read on both sheets.
# Writes the affine into lph/tf_ext2.json and lph/tf_all_ma.json and the spline into lph/tps.pkl (frame '168', no taper).
import json, pickle, numpy as np, runpy, io, contextlib
SP=_ws.DATA
with contextlib.redirect_stdout(io.StringIO()): g = runpy.run_path(_ws.CODE+'lph/refit168.py')
P = np.array(g['P'], float); O = g['O']
pts=[]; vec=[]
for x,y,E,N,w in O:
    e=P[0]*x+P[1]*y+P[4]; n=P[2]*x+P[3]*y+P[5]; pts.append((e,n)); vec.append((E-e,N-n))
pts=np.array(pts); vec=np.array(vec)
M=pickle.load(open(SP+'lph/tps.pkl','rb')); M['168']=dict(pts=pts,vec=vec,smooth=np.full(len(pts),0.01),notaper=True)
pickle.dump(M,open(SP+'lph/tps.pkl','wb'))
for fn in ('lph/tf_ext2.json','lph/tf_all_ma.json'):
    T=json.load(open(SP+fn)); T['168']=[float(v) for v in P]; json.dump(T,open(SP+fn,'w'))
print('residual moves (m):',np.round(np.hypot(*vec.T),2))
import sys; sys.path.insert(0,_ws.CODE+'lph'); import tps
dE,dN=tps.disp('168',pts[:,0],pts[:,1],M); print('spline check (m):',np.round(np.hypot(dE-vec[:,0],dN-vec[:,1]),2))
