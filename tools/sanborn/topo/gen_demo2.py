import numpy as np, cv2
from scipy import ndimage as ndi
exec(open('gen_demo.py').read().split('for name,lon,lat')[0])
for name,lon,lat in [('westwood',-84.595,39.135),('ftwright',-84.535,39.050)]:
    z=win(lon,lat); z=np.where(z<-1000,np.nanmedian(z),z)
    m25=ndi.median_filter(z,size=13); m41=ndi.median_filter(z,size=21)
    # median then light smoothing (removes the median's terracing)
    m41s=ndi.gaussian_filter(m41,3/R)
    panels=[hs(z),hs(ndi.gaussian_filter(z,15/R)),hs(ndi.gaussian_filter(m25,3/R)),hs(m41s)]
    labs=['LiDAR 2 m','smooth 15 m','median 26 m','median 42 m']
    out=[]
    for p,l in zip(panels,labs):
        p=cv2.resize(p,(750,750),interpolation=cv2.INTER_AREA); p=cv2.cvtColor(p,cv2.COLOR_GRAY2BGR)
        cv2.rectangle(p,(0,0),(330,34),(255,255,255),-1); cv2.putText(p,l,(8,25),cv2.FONT_HERSHEY_SIMPLEX,0.8,(0,0,0),2); out.append(p)
    cv2.imwrite('demo2_'+name+'.jpg',np.vstack([np.hstack(out[:2]),np.hstack(out[2:])]),[cv2.IMWRITE_JPEG_QUALITY,85])
    print(name,'max change m: s15 %.1f med42 %.1f'%(np.abs(ndi.gaussian_filter(z,15/R)-z).max(),np.abs(m41s-z).max()))
