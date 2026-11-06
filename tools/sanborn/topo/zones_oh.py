"""Candidate change zones on the 1912 survey area.
A: index (25 ft) contours whose LiDAR elevation is off the 25 ft lattice (ground changed under them).
B: steep LiDAR ground where the 1912 sheets show no contours nearby (new cuts and fills on ground that was flat or unmapped)."""
import numpy as np, json, glob, cv2
from scipy import ndimage as ndi
from geo import S
DM=json.load(open('dem2m.json')); DEM=np.load('dem2m.npy',mmap_mode='r'); FT=1200/3937
R=4.0; X0=DM['x0']; Y1=DM['y1']; NX=int(DM['w']*DM['res']/R); NY=int(DM['h']*DM['res']/R)
cnt=np.zeros((NY,NX),np.float32); bad=np.zeros((NY,NX),np.float32); anyc=np.zeros((NY,NX),bool)
for f in sorted(glob.glob('lab/*_seg.npz')):
    d=np.load(f); E=d['E']; N=d['N']; z=d['z'].astype(float); b=d['bold']
    ix=((E-X0)/R).astype(int); iy=((Y1-N)/R).astype(int); ok=(ix>=0)&(ix<NX)&(iy>=0)&(iy<NY)&np.isfinite(z)
    anyc[iy[ok],ix[ok]]=True
    k=ok&b; res=z[k]-25*np.round(z[k]/25)
    np.add.at(cnt,(iy[k],ix[k]),1); np.add.at(bad,(iy[k],ix[k]),(np.abs(res)>6).astype(np.float32))
cov=np.zeros((NY,NX),bool); c_old=np.load('cov4m.npy'); cov[:c_old.shape[0],:c_old.shape[1]]=c_old
K=15
cs=ndi.uniform_filter(cnt,K)*K*K; bs=ndi.uniform_filter(bad,K)*K*K
fracA=np.where(cs>=20,bs/np.maximum(cs,1),np.nan)
zoneA=(fracA>0.6)&cov
# B: LiDAR slope on 4 m grid
z4=np.asarray(DEM[::2,::2]).astype(np.float32)[:NY,:NX]; nod=z4==DM['nodata']; z4=np.where(nod,np.nan,z4/10)  # metres
z4s=ndi.gaussian_filter(np.nan_to_num(z4,nan=np.nanmean(z4)),1.0)
gy,gx=np.gradient(z4s,R); slope=np.hypot(gx,gy)
near=ndi.binary_dilation(anyc,iterations=5)          # contour within 20 m
steep=(slope>0.25)&~near&cov&~nod
steep=ndi.binary_opening(steep,iterations=1)
lab_,n=ndi.label(steep); area=ndi.sum(steep,lab_,np.arange(1,n+1))*R*R
zoneB=np.isin(lab_,np.nonzero(area>1500)[0]+1)
zone=ndi.binary_closing(zoneA|zoneB,iterations=3); zone=ndi.binary_opening(zone,iterations=2)
lab_,n=ndi.label(zone); area=ndi.sum(zone,lab_,np.arange(1,n+1))*R*R
zone=np.isin(lab_,np.nonzero(area>8000)[0]+1)
np.save('zoneA4m.npy',zoneA); np.save('zoneB4m.npy',zoneB); np.save('zone4m.npy',zone); np.save('fracA4m.npy',fracA.astype(np.float32)); np.save('slope4m.npy',slope.astype(np.float32))
print('survey cells',cov.sum(),' A cells',zoneA.sum(),' B cells',zoneB.sum(),' zones',ndi.label(zone)[1],' zone area km2 %.2f'%(zone.sum()*R*R/1e6),' coverage km2 %.1f'%(cov.sum()*R*R/1e6))
