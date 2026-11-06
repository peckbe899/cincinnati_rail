import numpy as np, json, sys
from corr import CSheet
from geo import S, FT
deg=None if sys.argv[1]=='none' else int(sys.argv[1])
ids=sorted(k for k in S if not k.startswith('_'))
C={sid:CSheet(sid,deg) for sid in ids}
out=[]
for A in ids:
    for B in ids:
        a,b=S[A],S[B]
        if a['x_e']==b['x_w']:   # vertical seam, A west of B
            y0,y1=max(a['y_s'],b['y_s']),min(a['y_n'],b['y_n'])
            if y1-y0<2000: continue
            gy=np.linspace(y0+300,y1-300,15); gx=np.full_like(gy,a['x_e'])
        elif a['y_s']==b['y_n']: # horizontal seam, A north of B
            x0,x1=max(a['x_w'],b['x_w']),min(a['x_e'],b['x_e'])
            if x1-x0<2000: continue
            gx=np.linspace(x0+300,x1-300,15); gy=np.full_like(gx,a['y_s'])
        else: continue
        pa=C[A].b.g2p(gx,gy); pb=C[B].b.g2p(gx,gy)
        ga=np.c_[C[A].p2g(*pa)]; gb=np.c_[C[B].p2g(*pb)]
        d=(ga-gb)*FT
        out.append((A,B,np.hypot(*d.T).mean(),d.mean(0)))
m=np.array([o[2] for o in out])
print('deg',deg,'seams',len(out),'mean |d| %.2f m  median %.2f  p90 %.2f  max %.2f'%(m.mean(),np.median(m),np.percentile(m,90),m.max()))
if len(sys.argv)>2:
    for o in sorted(out,key=lambda o:-o[2])[:12]: print(' ',o[0],o[1],'%.2f m'%o[2],o[3].round(2))
