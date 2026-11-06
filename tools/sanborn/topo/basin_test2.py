import numpy as np, cv2
from scipy import ndimage as ndi
from pilot_common import hs
G=np.load('map3_window_ground.npy')[1400:3000,2000:4400].astype(np.float64)
v=np.load('m3/basin_variants.npz'); B=v['area_4.8_ha'].astype(np.float64)
C=ndi.median_filter(B,size=13)
gy,gx=np.gradient(ndi.gaussian_filter(G,8),2); sl=np.hypot(gx,gy)
w=np.clip((0.22-sl)/0.10,0,1)
R=w*ndi.gaussian_filter(C,1.5)+(1-w)*G
R2=w*ndi.gaussian_filter(C,1.5)+(1-w)*ndi.median_filter(G,size=7)
np.save('m3/basin_R.npy',R.astype(np.float32))
def tile(im,sl_,nm):
    t=cv2.cvtColor(hs(im[sl_],6,2),cv2.COLOR_GRAY2BGR); cv2.putText(t,nm,(10,40),cv2.FONT_HERSHEY_SIMPLEX,1.1,(0,0,0),3); return t
rows=[]
for s_ in ((slice(700,1400),slice(0,900)),(slice(0,700),slice(900,1800))):
    rows.append(np.hstack([tile(G,s_,'LiDAR'),tile(R,s_,'area + median, flat/gentle only'),tile(R2,s_,'same + 14 m median on steep')]))
cv2.imwrite('m3/basin_combo.jpg',cv2.resize(np.vstack(rows),(1800,933),interpolation=cv2.INTER_AREA))
