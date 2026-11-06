"""Warp each 1912 sheet into EPSG:26916 at 0.5 m using the final model; clip to the sheet's own neatline."""
try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import numpy as np, cv2, json, sys, os, rasterio
from rasterio.transform import from_origin
from scipy.ndimage import map_coordinates
from final_model import Final
from geo import S
base=_ws.ext("/mnt/user-data/uploads/_Cincinnati Rail/Historic_Topo/1912_City_Topographic_Survey/")
RES=0.5; STEP=32
F=Final()
def run(sid):
    out=f'warped/Sheet_{sid}_1912_EPSG26916.tif'
    if os.path.exists(out): return sid,'kept'
    s=S[sid]; c=s['corners']; sh=F._s(sid)
    # neatline polygon in pixels (traced curves) -> ground bbox
    P=np.array([c['TL'],c['TR'],c['BR'],c['BL']],float)
    t=np.linspace(0,1,50); edge=[]
    for a,b in ((0,1),(1,2),(2,3),(3,0)): edge.append(P[a]+(P[b]-P[a])*t[:,None])
    edge=np.vstack(edge); E,N=F.p2utm(sid,edge[:,0],edge[:,1])
    e0=np.floor(E.min()/RES)*RES-5; e1=np.ceil(E.max()/RES)*RES+5; n0=np.floor(N.min()/RES)*RES-5; n1=np.ceil(N.max()/RES)*RES+5
    W=int(round((e1-e0)/RES)); H=int(round((n1-n0)/RES))
    # coarse lattice of source px
    cu=np.arange(0,W+STEP,STEP); cv=np.arange(0,H+STEP,STEP); CU,CV=np.meshgrid(cu,cv)
    u,v=F.utm2p(sid,e0+(CU.ravel()+0.5)*RES,n1-(CV.ravel()+0.5)*RES); U=u.reshape(CU.shape); V=v.reshape(CU.shape)
    im=cv2.imread(base+s['file'])
    # neatline mask in source image (Coons grid coords inside bounds)
    gx,gy=sh.p2g(U.ravel(),V.ravel()); 
    GXc=gx.reshape(CU.shape); GYc=gy.reshape(CU.shape)
    rgb=np.zeros((H,W,3),np.uint8); mask=np.zeros((H,W),np.uint8)
    for y in range(0,H,1024):
        yy,xx=np.mgrid[y:min(H,y+1024),0:W].astype(np.float32)
        mu=map_coordinates(U,[yy/STEP,xx/STEP],order=1).astype(np.float32); mv=map_coordinates(V,[yy/STEP,xx/STEP],order=1).astype(np.float32)
        rgb[y:y+1024]=cv2.remap(im,mu,mv,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT,borderValue=(255,255,255))[...,::-1]
        gxf=map_coordinates(GXc,[yy/STEP,xx/STEP],order=1); gyf=map_coordinates(GYc,[yy/STEP,xx/STEP],order=1)
        mask[y:y+1024]=((gxf>=s['x_w'])&(gxf<=s['x_e'])&(gyf>=s['y_s'])&(gyf<=s['y_n']))*255
    prof=dict(driver='GTiff',width=W,height=H,count=3,dtype='uint8',crs='EPSG:26916',transform=from_origin(e0,n1,RES,RES),
              tiled=True,blockxsize=512,blockysize=512,compress='JPEG',photometric='YCBCR',jpeg_quality=85)
    with rasterio.Env(GDAL_TIFF_INTERNAL_MASK=True):
        with rasterio.open(out,'w',**prof) as dst:
            for i in range(3): dst.write(rgb[...,i],i+1)
            dst.write_mask(mask)
            dst.update_tags(SOURCE=s['file'],MODEL='georef_1912.json (neatline Coons + regional field + per-sheet shape, LiDAR-matched)',DATUM_NOTE='1912 elevations ~ NAVD88 (offset 0 +/- 0.5 ft)')
    return sid,f'{W}x{H} {os.path.getsize(out)/1e6:.1f} MB'
if __name__=='__main__':
    from multiprocessing import Pool
    ids=sys.argv[1:] or sorted(k for k in S if not k.startswith('_'))
    with Pool(2) as p:
        for r in p.imap_unordered(run,ids): print(*r,flush=True)
