import numpy as np, sys
sid=sys.argv[1]
d=np.load(f'lab/{sid}_seg.npz'); ids=d['id']; z=d['z'].astype(float); bold=d['bold']
u,inv=np.unique(ids,return_inverse=True); n=len(u); cnt=np.bincount(inv)
srt=np.argsort(inv,kind='stable'); zs=z[srt]; bounds=np.r_[0,np.cumsum(cnt)]
share=np.zeros(n); lab=np.full(n,np.nan); med=np.full(n,np.nan)
for k in range(n):
    a=zs[bounds[k]:bounds[k+1]]; a=a[np.isfinite(a)]
    if len(a)==0: continue
    med[k]=np.median(a); l=5*np.round(a/5); vals,c=np.unique(l,return_counts=True); j=np.argmax(c); lab[k]=vals[j]; share[k]=c[j]/len(a)
bf=np.bincount(inv,weights=bold)/cnt
b=bf>0.7; t=bf<0.1; w=cnt
print(sid,'segments',n,'| share>0.8: %.2f'%(share>0.8).mean(),'| bold segs',b.sum(),'label mult25 (len-wtd) %.2f'%np.average(lab[b]%25==0,weights=w[b]),'| thin segs mult25 %.2f'%np.average(lab[t]%25==0,weights=w[t]))
np.savez(f'lab/{sid}_vote.npz',u=u,cnt=cnt,share=share,lab=lab,med=med,bf=bf)
