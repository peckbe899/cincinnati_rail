try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..', '..'))); import _ws
import json, sys, os, numpy as np, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from PIL import Image
Image.MAX_IMAGE_PIXELS=None
SP=_ws.DATA
TB=SP+'sbg/tiles_b/'; idx=json.load(open(TB+'index.json')); T=idx['size']; res=idx['res']
L=json.load(open(SP+'sbg/fit/basin_sanborn.json'))['features']
def mosaic(box, r=0.5):
    x0,y0,x1,y1=box; W=int((x1-x0)/r); H=int((y1-y0)/r); out=np.full((H,W,3),250,np.uint8)
    for tx,ty in idx['tiles']:
        if tx>x1 or tx+T<x0 or ty>y1 or ty+T<y0: continue
        im=Image.open(TB+f'{tx}_{ty}.webp').convert('RGBA'); k=int(T/r); im=np.asarray(im.resize((k,k),Image.BILINEAR))
        ox=int((tx-x0)/r); oy=int((y1-(ty+T))/r)
        a0,b0=max(0,oy),max(0,ox); a1,b1=min(H,oy+k),min(W,ox+k)
        if a1<=a0 or b1<=b0: continue
        sub=im[a0-oy:a1-oy,b0-ox:b1-ox]; al=sub[...,3:4]/255.
        out[a0:a1,b0:b1]=(sub[...,:3]*al+out[a0:a1,b0:b1]*(1-al)).astype(np.uint8)
    return out
def render(box,out,px=1600,r=0.5):
    x0,y0,x1,y1=box; img=mosaic(box,r); W=x1-x0; H=y1-y0; dpi=100
    fig=plt.figure(figsize=(px/dpi,px/dpi*H/W),dpi=dpi); ax=fig.add_axes([0,0,1,1])
    ax.imshow(img,extent=[x0,x1,y0,y1])
    for f in L:
        p=f['properties']
        if p['layer']!='street': continue
        c=np.array(f['geometry']['coordinates'])
        if c[:,0].max()<x0 or c[:,0].min()>x1 or c[:,1].max()<y0 or c[:,1].min()>y1: continue
        sc=px/W*72/dpi; w=p['width_m']*sc
        ax.plot(c[:,0],c[:,1],color='#0060ff',lw=w,alpha=0.18,solid_capstyle='butt')
        ax.plot(c[:,0],c[:,1],color='#e00000',lw=0.8)
    ax.set_xlim(x0,x1); ax.set_ylim(y0,y1); ax.set_xticks([]); ax.set_yticks([]); fig.savefig(out); plt.close(fig); print('saved',out)
if __name__=='__main__':
    b=[float(v) for v in sys.argv[1:5]]; render(b,sys.argv[5],int(sys.argv[6]) if len(sys.argv)>6 else 1600, float(sys.argv[7]) if len(sys.argv)>7 else 0.5)
