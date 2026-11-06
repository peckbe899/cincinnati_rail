import numpy as np, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from scipy import ndimage as ndi
bed=np.load('bathy/work/bed_real4.npy'); m=~np.isnan(bed)
# fill tiny nans inside domain by nearest
P=np.load('bathy/work/pts.npy')
r0,r1,c0,c1=3300,5900,3200,7600   # Cincinnati reach crop (4 m)
b=bed[r0:r1,c0:c1]
fig,ax=plt.subplots(figsize=(14,8.5),dpi=110)
ax.set_facecolor('#e8e4dc')
im=ax.imshow(138.68-b,cmap='Blues',vmin=0,vmax=18,extent=[695000+c0*4,695000+c1*4,4350000-r1*4,4350000-r0*4])
sel=(P[:,0]>695000+c0*4)&(P[:,0]<695000+c1*4)&(P[:,1]<4350000-r0*4)&(P[:,1]>4350000-r1*4)
ax.scatter(P[sel,0][::12],P[sel,1][::12],s=0.2,c='k',alpha=0.3)
cs=ax.contour(np.linspace(695000+c0*4,695000+c1*4,b.shape[1]),np.linspace(4350000-r0*4,4350000-r1*4,b.shape[0]),138.68-b,levels=[3,6,9,12,15],colors='#123',linewidths=0.4)
ax.clabel(cs,fontsize=6,fmt='%d m')
plt.colorbar(im,ax=ax,shrink=0.7,label='depth below normal pool (m)')
ax.set_title('Ohio and Licking bed from the Corps surveys (2022, Licking 2024), inside the canon outline; dots = soundings')
ax.set_aspect('equal'); plt.tight_layout(); plt.savefig('bathy/work/bed_real_preview.jpg',dpi=110)
