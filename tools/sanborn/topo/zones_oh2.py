import numpy as np, json, glob
from scipy import ndimage as ndi
DM=json.load(open('dem2m.json')); R=4.0; X0=DM['x0']; Y1=DM['y1']; NX=int(DM['w']*DM['res']/R); NY=int(DM['h']*DM['res']/R)
segc=np.zeros((NY,NX),np.float32); segb=np.zeros((NY,NX),np.float32)
for f in sorted(glob.glob('lab/*_seg.npz')):
    d=np.load(f); inv=np.unique(d['id'],return_inverse=True)[1]; n=inv.max()+1; cnt=np.bincount(inv)
    b=np.bincount(inv,weights=d['bold'])/cnt; z=d['z'].astype(float)
    o=np.argsort(inv,kind='stable'); bd=np.r_[0,np.cumsum(cnt)]
    zm=np.array([np.nanmedian(z[o[bd[k]:bd[k+1]]]) for k in range(n)])
    E=np.bincount(inv,weights=d['E'])/cnt; N=np.bincount(inv,weights=d['N'])/cnt
    k=(b>0.6)&(cnt>=10)&np.isfinite(zm)
    res=zm[k]-25*np.round(zm[k]/25)
    ix=((E[k]-X0)/R).astype(int); iy=((Y1-N[k])/R).astype(int); ok=(ix>=0)&(ix<NX)&(iy>=0)&(iy<NY)
    np.add.at(segc,(iy[ok],ix[ok]),1); np.add.at(segb,(iy[ok],ix[ok]),(np.abs(res[ok])>6).astype(np.float32))
K=31
cs=ndi.uniform_filter(segc,K)*K*K; bs=ndi.uniform_filter(segb,K)*K*K
frac=np.where(cs>=6,bs/np.maximum(cs,1),np.nan)
print('segments total',segc.sum(),' bad frac overall %.3f'%(segb.sum()/segc.sum()))
zA=(frac>0.6)
cov=np.zeros((NY,NX),bool); c_old=np.load('cov4m.npy'); cov[:c_old.shape[0],:c_old.shape[1]]=c_old
zA&=cov
np.save('zoneA4m.npy',zA); np.save('fracA4m.npy',frac.astype(np.float32))
print('A cells',zA.sum(),' km2 %.2f'%(zA.sum()*16/1e6))
