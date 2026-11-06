"""1912 survey tiles (0.5 m, 250 m) over the West End AOI for the page underlay."""
import numpy as np, json, os
from PIL import Image
from shapely.geometry import shape, box
a=np.load('m12.npy',mmap_mode='r'); E0,N1=712300,4334200
_A=json.load(open('aoi.json')); aoi=shape(_A['aoi']).union(shape(_A['aoi_east'])).buffer(150)
os.makedirs('tiles12',exist_ok=True)
T=250; out=[]
x0,y0,x1,y1=aoi.bounds
for tx in range(int(x0//T*T),int(x1)+1,T):
    for ty in range(int(y0//T*T),int(y1)+1,T):
        if not aoi.intersects(box(tx,ty,tx+T,ty+T)): continue
        c0,r0=int((tx-E0)/0.5),int((N1-(ty+T))/0.5)
        if c0<0 or r0<0 or c0+500>a.shape[1] or r0+500>a.shape[0]: continue
        im=Image.fromarray(np.array(a[r0:r0+500,c0:c0+500]))
        im.save(f'tiles12/{tx}_{ty}.webp',quality=58,method=6)
        out.append([tx,ty])
json.dump(dict(size=T,res=0.5,tiles=out),open('tiles12/index.json','w'))
tot=sum(os.path.getsize('tiles12/'+f) for f in os.listdir('tiles12'))
print('tiles',len(out),'MB',round(tot/1e6,1))
