import numpy as np, cv2
from scipy import ndimage as ndi
from skimage.morphology import area_opening, area_closing
from pilot_common import hs
W3=np.load('map3_window_ground.npy')
def proc(G, steep_med=13):
    zi=np.round(G*100).astype(np.int32)
    B=area_closing(area_opening(zi,12000),12000)/100.0
    C=ndi.gaussian_filter(ndi.median_filter(B,size=13),1.5)
    gy,gx=np.gradient(ndi.gaussian_filter(G,8),2); sl=np.hypot(gx,gy)
    w=np.clip((0.22-sl)/0.10,0,1)
    S=ndi.gaussian_filter(ndi.median_filter(G,size=steep_med),1.0)
    return w*C+(1-w)*S
def tile(im,nm):
    t=cv2.cvtColor(hs(im,6,2),cv2.COLOR_GRAY2BGR); cv2.putText(t,nm,(10,40),cv2.FONT_HERSHEY_SIMPLEX,1.1,(0,0,0),3); return t
rows=[]
for (r0,r1,c0,c1,nm) in ((1400,2100,2900,3800,'OTR hillside'),(2300,3000,300,1200,'Price Hill bluff'),(900,1600,5600,6500,'East Walnut Hills')):
    G=W3[r0-100:r1+100,c0-100:c1+100].astype(np.float64)
    a=G[100:-100,100:-100]; b=proc(G,13)[100:-100,100:-100]; c=proc(G,9)[100:-100,100:-100]
    rows.append(np.hstack([tile(a,nm+' LiDAR'),tile(c,'steep median 18 m'),tile(b,'steep median 26 m')]))
cv2.imwrite('m3/basin_combo3.jpg',cv2.resize(np.vstack(rows),(1800,1400),interpolation=cv2.INTER_AREA))
