import sys,json,numpy as np
exec(open('trunk2/ludlow.py').read().split('best=None')[0])
def U(b): r=np.radians(b); return np.array([np.sin(r),np.cos(r)])
A0=pt(5200); uA=U(34.2); eA=np.array([uA[1],-uA[0]])
B0=pt(6650); uB=U(62.0)
def build(d,R):
    a0=A0-eA*d
    t,v=np.linalg.solve(np.c_[uA,-uB],B0-a0); PI=a0+uA*t
    D=np.arccos(uA@uB); T=R*np.tan(D/2); TC=PI-uA*T; CT=PI+uB*T
    O=TC+eA*R  # right turn: centre to the right (east)
    a=np.arctan2(*(TC-O)[::-1]); b=np.arctan2(*(CT-O)[::-1]); da=(b-a+np.pi)%(2*np.pi)-np.pi
    arc=np.array([O+R*np.array([np.cos(a+da*f),np.sin(a+da*f)]) for f in np.linspace(0,1,400)])
    pre=np.array([a0+uA*x for x in np.arange(-300,(TC-a0)@uA,4)])
    post=np.array([CT+uB*x for x in np.arange(4,400,4)])
    return np.vstack([pre,arc,post]),TC,CT
cur=LineString([pt(s) for s in np.arange(4900,7000,2.0)])
for d in (0,4,6,8,10):
    for R in (600,800,1000,1200,1500,2000):
        c,TC,CT=build(d,R); cl=east_clear(c)
        # deviation from current between 5300 and 6700
        dev=[]
        for s in range(5300,6700,50):
            q=pt(s); j=int(np.argmin(np.hypot(*(c-q).T))); tt=c[min(j+1,len(c)-1)]-c[max(j-1,0)]; e=np.array([tt[1],-tt[0]])/np.hypot(*tt); dev.append(float((c[j]-q)@e))
        print(d,R,'clear %.1f'%cl,'TC s %d CT s %d'%(G.C.project(Point(TC)),G.C.project(Point(CT))),'dev east+ min %.0f max %.0f'%(min(dev),max(dev)))
