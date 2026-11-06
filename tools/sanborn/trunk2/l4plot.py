import sys,numpy as np, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
src=open('trunk2/ludlow4.py').read().split('best=[]')[0]; exec(src)
c,L=route(7,5450,1200,70,2000)
cur=np.array([pt(s) for s in np.arange(4900,7000,4.0)])
fig,ax=plt.subplots(figsize=(10,8)); ax.plot(cur[:,0],cur[:,1],'k',label='current'); ax.plot(c[:,0],c[:,1],'r',label='fit')
for g in pk:
    for q in getattr(g,'geoms',[g]): ax.fill(*q.exterior.xy,color='m',alpha=.2)
ax.set_aspect('equal'); ax.set_xlim(712400,714000); ax.set_ylim(4336500,4337800); ax.legend(); plt.savefig('trunk2/l4.png',dpi=80)
