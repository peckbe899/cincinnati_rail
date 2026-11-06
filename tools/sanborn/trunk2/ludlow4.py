import sys,json,numpy as np
exec(open('trunk2/ludlow.py').read().split('best=None')[0])
def U(b): r=np.radians(b); return np.array([np.sin(r),np.cos(r)])
bA=34.2; uA=U(bA); eA=np.array([uA[1],-uA[0]]); A0=pt(5200)
pB=pt(6750); bB=np.degrees(np.arctan2(*(pt(6750)-pt(6450))))
uB=U(bB); eB=np.array([uB[1],-uB[0]])
print('tangent B bearing %.2f'%bB)
def arc(P,b0,b1,R,n=None):
    # from point P heading b0, turn to b1 with radius R (right turn if b1>b0)
    sgn=1 if b1>b0 else -1; u=U(b0); e=np.array([u[1],-u[0]])*sgn; O=P+e*R
    a0=np.arctan2(*(P-O)[::-1]); d=np.radians(abs(b1-b0))*(-sgn)
    n=n or max(4,int(R*abs(d)/2))
    return np.array([O+R*np.array([np.cos(a0+d*f),np.sin(a0+d*f)]) for f in np.linspace(0,1,n)])
def route(d,sa,R1,beta,R2):
    a0=A0-eA*d+uA*(sa-5200)
    a1=arc(a0,bA,beta,R1); p=a1[-1]; ub=U(beta)
    # straight L then arc2 to bB; end line must coincide with tangent B: solve L
    def endoff(L):
        q=p+ub*L; a2=arc(q,beta,bB,R2); return float((a2[-1]-pB)@eB), a2
    lo,hi=0.0,1500.0; flo=endoff(lo)[0]; fhi=endoff(hi)[0]
    if flo*fhi>0: return None
    for _ in range(50):
        m=(lo+hi)/2; fm=endoff(m)[0]
        if fm*flo>0: lo,flo=m,fm
        else: hi=m
    L=(lo+hi)/2; _,a2=endoff(L)
    pre=np.array([A0-eA*d+uA*x for x in np.arange(-400,sa-5200,4)])
    st=np.array([p+ub*x for x in np.arange(0,L,4)])
    post=np.array([a2[-1]+uB*x for x in np.arange(4,max((pB-a2[-1])@uB,0)+300,4)])
    if len(st)==0: st=np.zeros((0,2))
    return np.vstack([pre,a1,st,a2,post]),L
def devs(c):
    out=[]
    for s in range(5300,6800,25):
        q=pt(s); j=int(np.argmin(np.hypot(*(c-q).T))); tt=c[min(j+1,len(c)-1)]-c[max(j-1,0)]; e=np.array([tt[1],-tt[0]])/np.hypot(*tt); out.append(float((c[j]-q)@e))
    return np.array(out)
best=[]
for d in (5,6,7,8):
  for sa in (5350,5400,5450,5500):
    for R1 in (600,700,800,900,1000,1200):
      for beta in (66,68,70,72,74):
        for R2 in (800,1000,1500,2000,3000):
          r=route(d,sa,R1,beta,R2)
          if r is None: continue
          c,L=r; cl=east_clear(c)
          if cl<3: continue
          dv=devs(c); best.append((min(R1,R2),round(cl,1),round(dv.min(),1),round(dv.max(),1),d,sa,R1,beta,R2,round(L)))
best.sort(key=lambda r:(-r[0],abs(r[2])+abs(r[3])))
for b in best[:12]: print(b)
