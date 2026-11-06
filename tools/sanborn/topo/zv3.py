import numpy as np, json, cv2
from pyproj import Transformer
DM=json.load(open('dem2m.json')); X0=DM['x0']; Y1=DM['y1']
D=np.load('dem2m.npy'); C=np.load('canon_hw_carve.npz'); D[C['rows'],C['cols']]=C['new']
f=4  # 8 m
z=D[::f,::f].astype(np.float32)/10; z[z<-1000]=np.nan; z=np.where(np.isnan(z),140,z)
gy,gx=np.gradient(z,2.0*f); hs=np.clip(0.62+(-gx+gy)*0.7/np.sqrt(1+gx**2+gy**2)*1.6,0,1)
img=(np.dstack([hs]*3)*235).astype(np.float32)
Zr=np.load('Z_real.npy')[::2,::2]; Zr=Zr[:img.shape[0],:img.shape[1]]
img[Zr]=img[Zr]*0.35+np.array((0,0,230))*0.65
img=img.astype(np.uint8)
T=Transformer.from_crs('EPSG:4326','EPSG:26916',always_xy=True)
col={'existing':(150,150,150),'grade':(176,108,43),'trench':(33,86,192),'bridge':(90,133,47),'tunnel':(193,70,107)}
P=json.load(open('canon_hw_profiles.json'))
for nm,v in P.items():
    e,n=T.transform(np.array(v['lon']),np.array(v['lat'])); xy=np.c_[(e-X0)/(2.0*f),(Y1-n)/(2.0*f)].astype(np.int32); ty=v['type']
    for i in range(len(ty)-1): cv2.line(img,tuple(xy[i]),tuple(xy[i+1]),col[ty[i]],4 if ty[i]!='existing' else 2,cv2.LINE_AA)
y=40
for k,c in col.items(): cv2.rectangle(img,(30,y-22),(62,y+4),c,-1); cv2.putText(img,k if k!='existing' else 'canon on existing freeway',(72,y),cv2.FONT_HERSHEY_SIMPLEX,0.9,(0,0,0),2); y+=40
cv2.rectangle(img,(30,y-22),(62,y+4),(0,0,230),-1); cv2.putText(img,'real-only zone (rebuilt to pre-work ground)',(72,y),cv2.FONT_HERSHEY_SIMPLEX,0.9,(0,0,0),2)
cv2.imwrite('preview_map3_v2.jpg',img,[cv2.IMWRITE_JPEG_QUALITY,80]); print(img.shape)
