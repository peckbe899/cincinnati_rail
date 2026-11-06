"""Blend finished I4 tiles into one 2 m surface (tent weights over the 400 m overlaps), plus the 1912 survey cover mask,
a GeoTIFF (decimetres, EPSG:26916) and an 8 m hillshade preview."""
import numpy as np, json, glob, cv2, rasterio
from rasterio.transform import from_origin
from pilot_common import hs
tiles=json.load(open('tiles.json')); DM=json.load(open('dem2m.json'))
done=[k for k in sorted(tiles) if glob.glob(f'iter_{k}_I4.npy')]
cx=np.array([tiles[k]['cx'] for k in done]); cy=np.array([tiles[k]['cy'] for k in done])
X0=float(np.floor((cx.min()-1700)/2)*2); X1=float(np.ceil((cx.max()+1700)/2)*2)
Y0=float(np.floor((cy.min()-1700)/2)*2); Y1=float(np.ceil((cy.max()+1700)/2)*2)
W=int((X1-X0)/2); H=int((Y1-Y0)/2)
acc=np.zeros((H,W),np.float32); wsum=np.zeros((H,W),np.float32); cov=np.zeros((H,W),bool)
ramp=np.clip((np.minimum(np.arange(1700),np.arange(1700)[::-1])-20)/180.0,0.0,1.0).astype(np.float32)   # drop 40 m of filter edge, blend over 360 m
w2=np.outer(ramp,ramp)
for k in done:
    T=np.load(f'iter_{k}_I4.npy'); s=np.load(f'pilot_{k}_S1912.npz')
    c=cv2.resize(s['cov'].astype(np.uint8),(1700,1700),interpolation=cv2.INTER_NEAREST).astype(bool)
    c0=int(round((tiles[k]['cx']-1700-X0)/2)); r0=int(round((Y1-(tiles[k]['cy']+1700))/2))
    acc[r0:r0+1700,c0:c0+1700]+=w2*T; wsum[r0:r0+1700,c0:c0+1700]+=w2; cov[r0:r0+1700,c0:c0+1700]|=c
from scipy import ndimage as ndi
cov=ndi.binary_fill_holes(ndi.binary_closing(cov,iterations=10))
lab_,nl=ndi.label(cov); sz=np.bincount(lab_.ravel()); cov=sz[lab_]>=25000; cov&=lab_>0   # drop specks under 0.1 km2
M=np.where(wsum>0,acc/np.maximum(wsum,1e-6),np.nan).astype(np.float32)
np.save('I4_mosaic.npy',M); np.save('I4_cover.npy',cov)
out=np.where(np.isfinite(M),np.round(M*10),-32768).astype(np.int16)
with rasterio.open('I4_1912_ground_dm.tif','w',driver='GTiff',height=H,width=W,count=1,dtype='int16',crs='EPSG:26916',
                   transform=from_origin(X0,Y1,2.0,2.0),compress='deflate',tiled=True,nodata=-32768) as ds: ds.write(out,1)
with rasterio.open('I4_1912_cover.tif','w',driver='GTiff',height=H,width=W,count=1,dtype='uint8',crs='EPSG:26916',
                   transform=from_origin(X0,Y1,2.0,2.0),compress='deflate',tiled=True) as ds: ds.write(cov.astype(np.uint8),1)
# preview: I4 inside the 1912 survey, LiDAR outside, survey edge outlined
DEM=np.load('dem2m.npy',mmap_mode='r'); r0=int((DM['y1']-Y1)/2); c0=int((X0-DM['x0'])/2)
L=np.asarray(DEM[r0:r0+H,c0:c0+W]).astype(np.float32)/10
P=np.where(cov&np.isfinite(M),M,L)[::4,::4]
im=cv2.cvtColor(hs(P,8.0,2.0),cv2.COLOR_GRAY2BGR)
cs,_=cv2.findContours(cov[::4,::4].astype(np.uint8),cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE); cv2.drawContours(im,cs,-1,(0,0,220),2)
cv2.imwrite('I4_preview.jpg',im,[cv2.IMWRITE_JPEG_QUALITY,82])
print('tiles',len(done),'grid',W,H,'cover km2 %.0f'%(cov.sum()*4/1e6))
