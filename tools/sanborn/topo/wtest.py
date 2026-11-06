import sys,numpy as np
from win import windows
sid='29'
for cap,wexp,smin in ((20,0,0.08),(8,0,0.08),(8,1,0.08),(6,1,0.12)):
    res=windows(sid,coons=True,cap=cap,wexp=wexp,smin=smin)
    ok=[w for w in res if not w['edge'] and w['n']>800]
    d=np.array([[w['dx'],w['dy']] for w in ok])
    # spatial coherence: median abs diff between 4-neighbour windows
    pos=np.array([[w['u'],w['v']] for w in ok]); diffs=[]
    for i in range(len(ok)):
        for j in range(i+1,len(ok)):
            if np.hypot(*(pos[i]-pos[j]))<1300: diffs.append(np.hypot(*(d[i]-d[j])))
    print(cap,wexp,smin,len(ok),'median',np.median(d,0).round(1),'std',d.std(0).round(1),'nbr diff',round(float(np.median(diffs)),1),flush=True)
