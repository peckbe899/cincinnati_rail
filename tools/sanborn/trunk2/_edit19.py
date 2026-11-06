s=open('lud19.py').read()
a=s.index("    for thA,dA in As:"); b=s.index("    print('best',best)")
s=s[:a]+'''    def maxR(A,C1,thC,dC,R3fix=None,R2fix=None):
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
'''+s[b:]
open('lud19.py','w').write(s)
