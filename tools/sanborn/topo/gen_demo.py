import numpy as np, cv2
from pyproj import Transformer
from scipy import ndimage as ndi
D=np.load('dem2m.npy',mmap_mode='r'); X0=695000; Y1=4350000; R=2.0
T=Transformer.from_crs('EPSG:4326','EPSG:26916',always_xy=True)
def win(lon,lat,half=1500):
    e,n=T.transform(lon,lat); c=int((e-X0)/R); r=int((Y1-n)/R); h=int(half/R)
    return np.array(D[r-h:r+h,c-h:c+h],np.float32)/10
def hs(z,az=315,alt=45,ex=2.0):
    gy,gx=np.gradient(z*ex,R); slope=np.arctan(np.hypot(gx,gy)); asp=np.arctan2(-gx,gy)
    a=np.radians(az); b=np.radians(alt)
    s=np.sin(b)*np.cos(slope)+np.cos(b)*np.sin(slope)*np.cos(a-asp)
    return np.clip(s*255,0,255).astype(np.uint8)
def tsculpt(z,sig):
    # Terrain Sculptor style: low-pass, then restore ridges/valleys using curvature of a coarser surface
    lp=ndi.gaussian_filter(z,sig/R)
    big=ndi.gaussian_filter(z,4*sig/R)
    curv=ndi.laplace(big)
    w=np.clip(np.abs(curv)/np.percentile(np.abs(curv),95),0,1)
    return lp*(1-0.5*w)+ndi.gaussian_filter(z,sig/(2*R))*(0.5*w)
for name,lon,lat in [('westwood',-84.595,39.135),('ftwright',-84.535,39.050)]:
    z=win(lon,lat)
    z[z<-1000]=np.nan; z=np.where(np.isnan(z),np.nanmedian(z),z)
    panels=[hs(z),hs(ndi.gaussian_filter(z,6/R)),hs(ndi.gaussian_filter(z,15/R)),hs(tsculpt(z,15))]
    labs=['LiDAR 2 m','smooth 6 m','smooth 15 m','15 m + ridge restore']
    out=[]
    for p,l in zip(panels,labs):
        p=cv2.resize(p,(750,750),interpolation=cv2.INTER_AREA); p=cv2.cvtColor(p,cv2.COLOR_GRAY2BGR)
        cv2.rectangle(p,(0,0),(330,34),(255,255,255),-1); cv2.putText(p,l,(8,25),cv2.FONT_HERSHEY_SIMPLEX,0.8,(0,0,0),2); out.append(p)
    cv2.imwrite('demo_'+name+'.jpg',np.vstack([np.hstack(out[:2]),np.hstack(out[2:])]),[cv2.IMWRITE_JPEG_QUALITY,85])
print('ok')
