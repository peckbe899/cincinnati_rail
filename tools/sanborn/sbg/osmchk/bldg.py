"""Fraction of each street centreline that runs over building fill on the warped 1904 sheets."""
try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..', '..'))); import _ws
import json, sys, os, collections, numpy as np
from PIL import Image
from shapely.geometry import shape
SB=(_ws.DATA + 'sbg/')
TB=SB+'tiles_b/'; idx=json.load(open(TB+'index.json')); T=idx['size']; res=idx['res']; NP=int(T/res)
def run(path, out):
    L=json.load(open(path))['features']; ST=[f for f in L if f['properties']['layer']=='street']
    pts=[]; owner=[]
    for i,f in enumerate(ST):
        g=shape(f['geometry'])
        for d in np.arange(1.0, g.length-0.99, 1.0):
            p=g.interpolate(d); pts.append((p.x,p.y)); owner.append((i,d))
    pts=np.array(pts); owner=np.array(owner)
    val=np.full(len(pts),-1.0)   # -1 no sheet, else 1 building / 0 not
    tiles={(tx,ty) for tx,ty in idx['tiles']}
    key=np.c_[np.floor(pts[:,0]/T)*T, np.floor(pts[:,1]/T)*T].astype(int)
    groups=collections.defaultdict(list)
    for k,(a,b) in enumerate(key): groups[(a,b)].append(k)
    for (tx,ty),ks in groups.items():
        if (tx,ty) not in tiles: continue
        im=np.asarray(Image.open(TB+f'{tx}_{ty}.webp').convert('RGBA')).astype(np.float32)/255
        ks=np.array(ks); c=((pts[ks,0]-tx)/res).astype(int).clip(0,NP-1); r=((ty+T-pts[ks,1])/res).astype(int).clip(0,NP-1)
        px=im[r,c]; a=px[:,3]; rgb=px[:,:3]
        mx=rgb.max(1); mn=rgb.min(1); sat=(mx-mn)/np.maximum(mx,1e-6)
        bld=(sat>0.30)&(mx>0.45)
        v=np.where(a>0.5, bld.astype(float), -1.0); val[ks]=v
    rows=[]
    for i,f in enumerate(ST):
        m=owner[:,0]==i; v=val[m]; d=owner[m,1]; cov=v>=0
        if cov.sum()<5: continue
        b=v[cov]; frac=b.mean()
        # longest run of building pixels (allow 1 m gaps)
        run_=0; best=0; bs=None; cur_s=None; gap=0
        for dd,vv in zip(d[cov],b):
            if vv>0.5:
                if run_==0: cur_s=dd
                run_+=1+gap; gap=0
                if run_>best: best=run_; bs=(cur_s,dd)
            else:
                if run_>0 and gap<1: gap+=1
                else: run_=0; gap=0
        p=f['properties']; rows.append(dict(id=p['id'],name=p['name'],kind=p['kind'],L=round(shape(f['geometry']).length),frac=round(float(frac),3),run=int(best),span=bs))
    json.dump(rows,open(out,'w'),indent=0)
    return rows
if __name__=='__main__':
    rows=run(sys.argv[1], sys.argv[2])
    bad=[r for r in rows if r['run']>=12]
    print(len(rows),'pieces;',len(bad),'with a 12 m+ run over building fill')
    for r in sorted(bad,key=lambda r:-r['run'])[:60]: print(f"  {r['id']} {r['name'][:30]:30s} {r['kind']:9s} L{r['L']:5d} frac {r['frac']:.2f} run {r['run']} m at {r['span']}")
