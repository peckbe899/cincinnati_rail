import numpy as np, networkx as nx, json
from skimage.morphology import skeletonize
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
C=np.load('topo/canon_river_8m.npy')
lab,n=ndi.label(C); C=lab==np.argmax(np.bincount(lab.ravel())[1:])+1
sk=skeletonize(ndi.binary_opening(C,iterations=3)); ys,xs=np.nonzero(sk)
idx={(y,x):i for i,(y,x) in enumerate(zip(ys,xs))}; G=nx.Graph()
for (y,x),i in idx.items():
    for dy in(-1,0,1):
        for dx in(-1,0,1):
            j=idx.get((y+dy,x+dx))
            if j is not None and j!=i: G.add_edge(i,j,weight=np.hypot(dy,dx))
G=G.subgraph(max(nx.connected_components(G),key=len)); a=next(iter(G.nodes))
d=nx.single_source_dijkstra_path_length(G,a); b=max(d,key=d.get); d=nx.single_source_dijkstra_path_length(G,b); c=max(d,key=d.get)
P=np.array([(ys[i],xs[i]) for i in nx.dijkstra_path(G,b,c)],float); P=ndi.gaussian_filter1d(P,10,axis=0,mode='nearest')
ch=np.r_[0,np.cumsum(np.hypot(*np.diff(P,axis=0).T))]*8; t=cKDTree(P)
FR=np.load('bathy/work/flood_real8b.npy'); FC=np.load('bathy/work/flood_canon8b.npy')
def area_per_point(M):
    yy,xx=np.nonzero(M); dd,k=t.query(np.c_[yy,xx]); k=k[dd*8<900]; return np.bincount(k,minlength=len(P))*64.0
step=np.gradient(ch)
ar=area_per_point(FR); ac=area_per_point(FC)
# running 1 km window
def run(v,L=1000):
    cs=np.r_[0,np.cumsum(v)]; out=np.empty(len(ch))
    lo=np.searchsorted(ch,ch-L/2); hi=np.searchsorted(ch,ch+L/2)
    return (cs[hi]-cs[lo])
wr=run(ar)/np.maximum(run(step),1); wc=run(ac)/np.maximum(run(step),1)
ratio=np.maximum(wr/np.maximum(wc,1),1.0); f=ratio**0.64
np.save('bathy/work/cl.npy',np.c_[P,ch,wr,wc,f])
for s in range(0,int(ch[-1]),1000):
    i=np.searchsorted(ch,s); E=695000+P[i,1]*8; N=4350000-P[i,0]*8
    print(f'{s/1000:4.0f} km E{E:.0f} N{N:.0f}  flood width real {wr[i]:5.0f}  canon {wc[i]:5.0f}  ratio {ratio[i]:.2f}  depth x{f[i]:.2f}')
