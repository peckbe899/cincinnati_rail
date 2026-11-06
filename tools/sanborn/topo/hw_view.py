import numpy as np, cv2, json
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
exec(open('gen_demo.py').read().split('def tsculpt')[0])
C=np.load('canon_hw_carve.npz'); Dn=np.array(D)  # copy of LiDAR
Dn[C['rows'],C['cols']]=C['new']
def winD(A,lon,lat,half):
    e,n=T.transform(lon,lat); c=int((e-X0)/R); r=int((Y1-n)/R); h=int(half/R)
    return np.array(A[r-h:r+h,c-h:c+h],np.float32)/10
P=json.load(open('canon_hw_profiles.json'))
views=[('Price Hill trench',-84.592,39.103,2000),('Delhi - Villa Hills crossing',-84.598,39.073,2000),
       ('Columbia-Tusculum - Fort Thomas',-84.438,39.095,2200),('Climb out of Mill Creek',-84.553,39.142,2000)]
tiles=[]
for t,lon,lat,half in views:
    a=winD(D,lon,lat,half); b=winD(Dn,lon,lat,half)
    row=[]
    for z,l in ((a,'LiDAR'),(b,'with canon interstate')):
        p=cv2.resize(hs(z),(700,700),interpolation=cv2.INTER_AREA); p=cv2.cvtColor(p,cv2.COLOR_GRAY2BGR)
        cv2.rectangle(p,(0,0),(700,32),(255,255,255),-1); cv2.putText(p,t+': '+l,(8,23),cv2.FONT_HERSHEY_SIMPLEX,0.62,(0,0,0),2); row.append(p)
    tiles.append(np.hstack(row))
cv2.imwrite('hw_views.jpg',np.vstack(tiles),[cv2.IMWRITE_JPEG_QUALITY,82])
col={'existing':'#bbbbbb','grade':'#2b6cb0','trench':'#c05621','bridge':'#2f855a','tunnel':'#6b46c1'}
fig,axs=plt.subplots(len(P),1,figsize=(13,3.2*len(P)))
for ax,(nm,v) in zip(np.atleast_1d(axs),P.items()):
    s=np.array(v['s'])/1000; g=np.array(v['ground_ctr']); z=np.array(v['z']); ty=np.array(v['type'])
    ax.plot(s,g,color='#8a6d3b',lw=0.8,label='ground (LiDAR)')
    for k,c in col.items():
        m=np.where(ty==k,z,np.nan); ax.plot(s,m,color=c,lw=2,label=k)
    ax.set_title(nm); ax.set_ylabel('m NAVD88'); ax.grid(alpha=.3)
np.atleast_1d(axs)[0].legend(ncol=6,fontsize=8); np.atleast_1d(axs)[-1].set_xlabel('km along alignment (from north / start of line in the extent)')
plt.tight_layout(); plt.savefig('hw_profiles.png',dpi=90)
