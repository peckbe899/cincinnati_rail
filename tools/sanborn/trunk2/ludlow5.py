import sys,json,numpy as np
exec(open('trunk2/ludlow.py').read().split('best=None')[0])
sys.path.insert(0,SP+'trunk'); from frames import chaikin, resample
def bl(s,s0,s1,a,b):
    t=np.clip((np.asarray(s)-s0)/(s1-s0),0,1); return a+(b-a)*(1-np.cos(np.pi*t))/2
def circ(P,h=25):
    R=np.full(len(P),1e9)
    for i in range(h,len(P)-h):
        a,b,c=P[i-h],P[i],P[i+h]; ab=np.hypot(*(b-a)); bc=np.hypot(*(c-b)); ca=np.hypot(*(a-c)); cr=abs((b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])); R[i]=ab*bc*ca/(2*cr) if cr>1e-9 else 1e9
    return R
for step,it,W,(w0,w1,w2,w3) in ((100,7,7.0,(4950,5300,5700,6300)),):
    ss=np.arange(4900,6950,2.0); base=np.array([pt(s) for s in ss])
    sm=resample(chaikin(resample(base,step),it),2.0)
    # keep ends tied: blend smoothed in between 4950 and 6850
    L=LineString(sm); P=np.array([L.interpolate(L.project(Point(q))).coords[0] for q in base])
    wgt=np.minimum(bl(ss,4900,5050,0,1),bl(ss,6750,6900,1,0))
    P=base*(1-wgt[:,None])+P*wgt[:,None]
    t=np.gradient(P,axis=0); t/=np.hypot(t[:,0],t[:,1])[:,None]; e=np.c_[t[:,1],-t[:,0]]
    w=np.minimum(bl(ss,w0,w1,0,W),bl(ss,w2,w3,W,0))
    P=P-e*w[:,None]
    R=circ(P); sel=(ss>4950)&(ss<6850)
    print(step,it,W,(w0,w1,w2,w3),'minR %.0f at s %.0f'%(R[sel].min(),ss[sel][np.argmin(R[sel])]),'east clear %.1f'%east_clear(P))
    np.save(SP+f'trunk2/lud_{step}.npy',np.c_[ss,P])
