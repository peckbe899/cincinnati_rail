import numpy as np, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
def bl(s,s0,s1,a,b):
    t=np.clip((s-s0)/(s1-s0),0,1); return a+(b-a)*(1-np.cos(np.pi*t))/2
def pw(s,segs,v0):
    out=np.full(s.shape,float(v0)); cur=v0
    for s0,s1,v in segs: out=np.where(s>=s0,bl(s,s0,s1,cur,v),out); cur=v
    return out
s=np.arange(2500,5000,2.0)
L={}
# offsets east of the trunk (+ east). West is left in the drawing.
L['ORR/TV west pair, track 1']=('m',pw(s,[(2541,2964,-49.5),(4430,4780,-24.75)],-22.5),'lower deck')
L['ORR/TV west pair, track 2']=('m',pw(s,[(2541,2964,-45.0),(4430,4780,-20.25)],-18.0),'lower deck')
L['B SB']=('tab:orange',pw(s,[(2884,2964,-32.5),(3200,3320,-36.0),(3700,3900,-32.5),(4248,4348,-22.5),(4430,4780,-13.5)],-22.5),'')
L['B NB']=('tab:orange',pw(s,[(3200,3320,-27.0),(3944,4044,-18.0),(4430,4780,-9.0)],-18.0),'')
dsb=np.where(s<3200,np.nan,pw(s,[(3200,3320,-31.5),(3450,3600,-22.5)],-32.5))
dnb=np.where(s<3200,np.nan,np.full(s.shape,-18.0))
L['D SB']=('red',dsb,''); L['D NB']=('red',dnb,'')
for nm,o in (('APEx Indy',(-11.25,-6.75)),('APEx Dayton',(-2.25,2.25)),('APEx Norwood',(6.75,11.25))):
    for k in (0,1): L[f'{nm} {k+1}']=('k' if nm!='APEx Indy' else '0.5',np.full(s.shape,o[k]),'')
for k,o in enumerate((18.0,22.5)): L[f'ORR/TV east pair, track {k+1}']=('m',np.full(s.shape,o),'lower deck')
fig,ax=plt.subplots(figsize=(9,16))
for nm,(c,o,_) in L.items():
    oo=o.copy()
    if nm.startswith(('D ','APEx Indy')): oo[s>3924]=np.nan
    ax.plot(oo,s,color=c,lw=2 if 'pair' not in nm else 1.6,ls='--' if 'pair' in nm else '-')
for y,t in ((2964,'Camp Washington island (s 2,964-3,168)'),(3200,'B/D junction: turnouts'),(3644,'Indy starts up 2.5%'),(3924,'Indy + D turn west on one deck (constant radius)'),(4044,'Arlington island (s 4,044-4,248)'),(4430,'B and the west pair move in (to s 4,780)')):
    ax.axhline(y,color='0.8',lw=0.6); ax.text(26,y,t,fontsize=8,va='bottom')
ax.text(-34,3330,'D SB comes down over B NB\n(7 m) and merges into SB',fontsize=7,color='red')
ax.text(-16,3260,'D NB climbs from\nthe junction',fontsize=7,color='red')
ax.set_xlim(-55,60); ax.set_xlabel('offset from the trunk line, m (west is left)'); ax.set_ylabel('chainage from CUT, m (north is up)')
ax.set_title('B/D junction on the west (schematic, offsets to scale, stretched along)',fontsize=10)
from matplotlib.lines import Line2D
ax.legend([Line2D([],[],color=c,ls=l) for c,l in (('m','--'),('tab:orange','-'),('red','-'),('0.5','-'),('k','-'))],['ORR/TV pairs (lower)','RER B','RER D (climbing to 174.3 m)','APEx Indy (climbing)','APEx Dayton, Norwood'],loc='lower right',fontsize=8)
plt.savefig('trunk2/junction_schematic.png',dpi=90,bbox_inches='tight')
