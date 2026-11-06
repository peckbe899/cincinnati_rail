import numpy as np, pickle, glob
from pyproj import Transformer
T=Transformer.from_crs(2246,26916,always_xy=True)
out=[]
for f in sorted(glob.glob('bathy/raw/*/*_A.XYZ')):
    a=np.loadtxt(f); x,y=T.transform(a[:,0],a[:,1]); z=(455.0-a[:,2])*0.3048
    src=0 if 'LR_' in f else 1
    out.append(np.c_[x,y,z,np.full(len(z),src)])
P=np.vstack(out)
m=(P[:,0]>695000)&(P[:,0]<735000)&(P[:,1]>4315000)&(P[:,1]<4350000)
P=P[m]; np.save('bathy/work/pts.npy',P)
print(len(P), 'z range', np.percentile(P[:,2],[0,1,50,99,100]))
O,Lk=pickle.load(open('topo/canon_river.pkl','rb')); print(type(O),O.geom_type,O.bounds, type(Lk), Lk.geom_type, Lk.bounds)
from shapely.geometry import MultiPoint
from shapely import points, contains
inO=contains(O,points(P[:,0],P[:,1])); inL=contains(Lk,points(P[:,0],P[:,1]))
print('in Ohio outline',inO.sum(),'in Licking',inL.sum(),'neither',(~inO&~inL).sum())
