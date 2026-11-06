import numpy as np, cv2, json, sys
from scipy import ndimage as ndi
name=sys.argv[1]; s=np.load(f'pilot_{name}_S1912.npz'); S=s['S']; X0=float(s['X0']); Y1=float(s['Y1']); R=float(s['R'])
DM=json.load(open('dem2m.json')); DEM=np.load('dem2m.npy',mmap_mode='r')
c0=int((X0-DM['x0'])/2); r0=int((DM['y1']-Y1)/2); n=S.shape[0]*2
L=np.asarray(DEM[r0:r0+n,c0:c0+n]).astype(np.float32)/10
def hs(z,res,ex=2.0):
    gy,gx=np.gradient(z*ex,res); sl=np.arctan(np.hypot(gx,gy)); asp=np.arctan2(-gx,gy); a=np.radians(315); b=np.radians(45)
    return np.clip((np.sin(b)*np.cos(sl)+np.cos(b)*np.sin(sl)*np.cos(a-asp))*255,0,255).astype(np.uint8)
Su=cv2.resize(S,(n,n),interpolation=cv2.INTER_CUBIC)
d=L-Su
dv=np.clip(d/6,-1,1); col=np.zeros((n,n,3),np.uint8); col[...,2]=(127+127*np.clip(dv,0,1)).astype(np.uint8); col[...,0]=(127+127*np.clip(-dv,0,1)).astype(np.uint8); col[...,1]=(127*(1-np.abs(dv))).astype(np.uint8)+64
out=[]
for im,lab in ((hs(L,2.0),'LiDAR 2026'),(hs(Su,2.0),'1912 surface from contours'),(col,'LiDAR minus 1912 (red up, blue down, +/-6 m)')):
    im=cv2.resize(im,(900,900),interpolation=cv2.INTER_AREA)
    if im.ndim==2: im=cv2.cvtColor(im,cv2.COLOR_GRAY2BGR)
    cv2.rectangle(im,(0,0),(900,34),(255,255,255),-1); cv2.putText(im,lab,(8,25),cv2.FONT_HERSHEY_SIMPLEX,0.8,(0,0,0),2); out.append(im)
cv2.imwrite(f'pilot_{name}_surface.jpg',np.hstack(out),[cv2.IMWRITE_JPEG_QUALITY,85])
print('diff stats m: p5 %.1f p50 %.1f p95 %.1f'%tuple(np.percentile(d,[5,50,95])))
