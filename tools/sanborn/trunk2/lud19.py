try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Trunk north of Arlington: Arlington straight -> curve 1 -> straight A (today's line through Ludlow and Northside) -> curve 2 (right)
# -> straight C -> curve 3 (left, forced by the open creek bend and the bridge line) -> straight B (today's line to the Mill Creek bridge).
import sys, json, numpy as np
_src=open((_ws.CODE + 'trunk2/lud18.py')).read()
exec(_src.split("def path(")[0]); exec('def offsets'+_src.split('def offsets')[1].split("if __name__")[0])
def fitline(s0,s1):
    m=(RS>=s0)&(RS<=s1); P=RP[m]; c=P.mean(axis=0); u=np.linalg.svd(P-c)[2][0]
    if u@(P[-1]-P[0])<0: u=-u
    return c,u,np.abs((P-c)@np.array([u[1],-u[0]])).max()
LA=(ref(4200.0),tan_at(4200.0))
cA,uA,eA=fitline(4950,5450); cB,uB,eB=fitline(6550,7300)
print('straight A bearing %.2f (today within %.2f m), straight B bearing %.2f (within %.2f m)'%(np.degrees(np.arctan2(*uA)),eA,np.degrees(np.arctan2(*uB)),eB))
def corner(p1,u1,p2,u2,R):
    tt_,v=np.linalg.solve(np.c_[u1,-u2],p2-p1); PI=p1+u1*tt_; th=np.arccos(np.clip(u1@u2,-1,1)); T=R*np.tan(th/2)
    a=PI-u1*T; b=PI+u2*T; cr=u1[0]*u2[1]-u1[1]*u2[0]; nr=np.array([u1[1],-u1[0]]) if cr<0 else np.array([-u1[1],u1[0]]); O=a+nr*R
    a0=np.arctan2(*(a-O)[::-1]); a1=np.arctan2(*(b-O)[::-1]); da=(a1-a0+np.pi)%(2*np.pi)-np.pi
    n=max(3,int(R*abs(da)/2)); f=np.linspace(0,1,n); return a,b,np.c_[O[0]+R*np.cos(a0+da*f),O[1]+R*np.sin(a0+da*f)],PI
def sof(p): d,i=KD.query(p); return RS[i]
def seg(p,u,x0,x1): return np.array([p+u*x for x in np.arange(x0,x1,2.0)]) if x1>x0+2 else np.zeros((0,2))
def mkA(thA,dA):
    r=np.radians(thA); u=np.array([np.sin(r),np.cos(r)]); p=ref(5300.0)+RE[int(np.searchsorted(RS,5300.0))]*dA; return p,u
def curve1(pA,uA_):
    for R1 in np.arange(3000,300,-5.0):
        a1,b1,arc1,_=corner(LA[0],LA[1],pA,uA_,R1)
        if sof(a1)>=4260: return R1,a1,b1,arc1
MINC=40.0
def build(A,C1,thC,dC,R2,R3):
    pA,uA_=A; R1,a1,b1,arc1=C1
    r=np.radians(thC); uC=np.array([np.sin(r),np.cos(r)]); pC=ref(6050.0)+RE[int(np.searchsorted(RS,6050.0))]*dC
    a2,b2,arc2,_=corner(pA,uA_,pC,uC,R2); a3,b3,arc3,_=corner(pC,uC,cB,uB,R3)
    if (a2-b1)@uA_<0 or (a3-b2)@uC<MINC or (cB-b3)@uB<-400: return None
    c=np.vstack([seg(LA[0],LA[1],-250,(a1-LA[0])@LA[1]),arc1,seg(b1,uA_,2,(a2-b1)@uA_),arc2,seg(b2,uC,2,(a3-b2)@uC),arc3,seg(b3,uB,2,1500)])
    return c,(a1,b1,a2,b2,a3,b3)
if __name__=='__main__':
    best=None
    # straight A first: must pass the culvert (west) and OH-75 (east) pinch on its own
    As=[]
    for thA in np.arange(31.5,34.61,0.1):
        for dA in np.arange(-6.0,0.01,0.25):
            A=mkA(thA,dA); c=np.array([A[0]+A[1]*x for x in np.arange(-400,350,5.0)]); s_,o_=offsets(c)
            m=(SB>=5000)&(SB<=5600); oo=np.interp(SB[m],s_,o_)
            if ((oo>=LO[m])&(oo<=HI[m])).all(): As.append((thA,dA))
    print(len(As),'straight A options', As[:3], As[-3:])
    def maxR(A,C1,thC,dC,R3fix=None,R2fix=None):
        for R in range(1500,499,-25):
            r=build(A,C1,thC,dC,R if R2fix is None else R2fix,R3fix if R3fix is not None else R)
            if r is not None and ok(r[0])[0]: return R
        return 0
    for thA,dA in As[::2]:
        A=mkA(thA,dA); C1=curve1(*A)
        for thC in np.arange(66.0,82.1,2.0):
            for dC in np.arange(12.0,28.1,2.0):
                R2=maxR(A,C1,thC,dC,R3fix=500)
                if R2==0 or (best and R2<best[0]): continue
                R3=maxR(A,C1,thC,dC,R2fix=R2)
                while R3<R2 and R2>500:
                    R2b=R2-25; R3b=maxR(A,C1,thC,dC,R2fix=R2b)
                    if min(R2b,R3b)<=min(R2,R3): break
                    R2,R3=R2b,R3b
                if R3==0: continue
                sc=(min(R2,R3),R2+R3,C1[0])
                if best is None or sc>tuple(best[:3]):
                    best=[sc[0],sc[1],C1[0],thA,dA,thC,dC,R2,R3]; r=build(A,C1,thC,dC,R2,R3); print('candidate',best,[round(sof(p)) for p in r[1]],flush=True)
    print('best',best); json.dump(dict(best=[float(x) for x in best] if best else None),open(SP+'trunk2/lud19_best.json','w'))
