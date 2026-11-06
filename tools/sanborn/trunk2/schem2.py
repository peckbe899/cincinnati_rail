import numpy as np, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
def bl(s,s0,s1,a,b):
    t=np.clip((s-s0)/(s1-s0),0,1); return a+(b-a)*(1-np.cos(np.pi*t))/2
def pw(s,segs,v0):
    out=np.full(s.shape,float(v0)); cur=v0
    for s0,s1,v in segs: out=np.where(s>=s0,bl(s,s0,s1,cur,v),out); cur=v
    return out
s=np.arange(2000,5000,2.0)
cen=pw(s,[(2460,2758,-20.25)],5.5)
bnb=np.where(s<2758,cen+2.25,pw(s,[(3200,3320,-27.0),(3944,4044,-18.0),(4430,4780,-9.0)],-18.0))
bsb=np.where(s<2758,cen-2.25,pw(s,[(2884,2964,-32.5),(3200,3320,-36.0),(3700,3900,-32.5),(4248,4348,-22.5),(4430,4780,-13.5)],-22.5))
w1=pw(s,[(2100,2500,-49.5),(4430,4780,-24.75)],-22.5); w2=pw(s,[(2100,2500,-45.0),(4430,4780,-20.25)],-18.0)
dsb=np.where((s<3200)|(s>3924),np.nan,pw(s,[(3200,3320,-31.5),(3480,3620,-22.5)],-32.5)); dnb=np.where((s<3200)|(s>3924),np.nan,-18.0)
fig,ax=plt.subplots(figsize=(9,17))
under=s<2758
for o in (bnb,bsb):
    a=o.copy(); a[~under]=np.nan; ax.plot(a,s,color='tab:orange',lw=1.6,ls=':')
    b=o.copy(); b[under]=np.nan; ax.plot(b,s,color='tab:orange',lw=2)
for o in (w1,w2): ax.plot(o,s,color='m',lw=1.6,ls='--')
for o in (dsb,dnb): ax.plot(o,s,color='red',lw=2.6)
for o,c in ((-11.25,'0.5'),(-6.75,'0.5'),(-2.25,'k'),(2.25,'k'),(6.75,'k'),(11.25,'k')):
    a=np.full(s.shape,o); 
    if c=='0.5': a[s>3924]=np.nan
    ax.plot(a,s,color=c,lw=2.6 if c=='0.5' else 1.8)
for o in (18.0,22.5): ax.plot(np.full(s.shape,o),s,color='m',lw=1.6,ls='--')
for y,t in ((2199,'Straight (B, D) under the deck, s 2,199-2,403'),(2460,'B/D box: heads west under the viaduct (below it)'),(2758,'B/D 6.8 m under the viaduct; open ramp up from here'),(2964,'Camp Washington island, s 2,964-3,168, on the viaduct'),(3200,'B/D junction'),(3644,'Indy starts up 2.5%'),(3924,'Indy + D turn west on one deck (upper level), R5 under it'),(4044,'Arlington island'),(4430,'B and the west pair move in (to s 4,780)')):
    ax.axhline(y,color='0.85',lw=0.6); ax.text(26,y,t,fontsize=8,va='bottom')
ax.axvspan(-60,60,ymin=0,ymax=0,alpha=0)
ax.text(-58,2300,'west pair moves out\nfirst (s 2,100-2,500),\nso B/D never runs\nunder or beside it\nat the same place',fontsize=7,color='m')
ax.text(-35,3340,'southbound D comes down\nover northbound B (7 m)\nand joins the B/D\nsouthbound track',fontsize=7,color='red')
ax.set_xlim(-60,60); ax.set_xlabel('offset from the trunk line, m (west is left)'); ax.set_ylabel('chainage from CUT, m (north is up)')
ax.set_title('B/D on the west, v2 (schematic; offsets to scale, stretched along)',fontsize=10)
ax.legend([Line2D([],[],color='m',ls='--'),Line2D([],[],color='tab:orange',ls=':'),Line2D([],[],color='tab:orange'),Line2D([],[],color='red',lw=2.6),Line2D([],[],color='0.5',lw=2.6),Line2D([],[],color='k')],
          ['ORR/TV pairs (viaduct level)','RER B/D in the box (below the viaduct)','RER B/D on the viaduct','RER D climbing to the upper level','APEx Indy climbing to the upper level','APEx Dayton, Norwood'],loc='lower right',fontsize=8)
plt.savefig('trunk2/junction_schematic_v2.png',dpi=90,bbox_inches='tight')
