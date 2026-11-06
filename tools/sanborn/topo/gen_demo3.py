import numpy as np, cv2, rasterio
from rasterio.windows import from_bounds
from scipy import ndimage as ndi
exec(open('gen_demo.py').read().split('for name,lon,lat')[0])
lon,lat=-84.512,39.115; half=1500
z=win(lon,lat,half); z=np.where(z<-1000,np.nanmedian(z),z)
e,n=T.transform(lon,lat)
with rasterio.open('warped/1912_Survey_Mosaic.vrt') as ds:
    w=from_bounds(e-half,n-half,e+half,n+half,ds.transform)
    img=ds.read(window=w,out_shape=(ds.count,1500,1500),boundless=True,fill_value=255)
img=np.transpose(img[:3],(1,2,0))[:,:,::-1].copy()
m26=ndi.gaussian_filter(ndi.median_filter(z,size=13),3/R)
panels=[hs(z),hs(ndi.gaussian_filter(z,15/R)),hs(m26),img]
labs=['LiDAR 2 m','smooth 15 m','median 26 m','1912 survey, same area']
out=[]
for p,l in zip(panels,labs):
    p=cv2.resize(p,(750,750),interpolation=cv2.INTER_AREA)
    if p.ndim==2: p=cv2.cvtColor(p,cv2.COLOR_GRAY2BGR)
    cv2.rectangle(p,(0,0),(390,34),(255,255,255),-1); cv2.putText(p,l,(8,25),cv2.FONT_HERSHEY_SIMPLEX,0.8,(0,0,0),2); out.append(p)
cv2.imwrite('demo3_otr.jpg',np.vstack([np.hstack(out[:2]),np.hstack(out[2:])]),[cv2.IMWRITE_JPEG_QUALITY,85])
