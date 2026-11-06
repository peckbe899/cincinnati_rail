import pickle, json, numpy as np, collections
D=pickle.load(open('osmchk/samples.pkl','rb')); A=D['SAMP']; B=D['OSMS']
def runs(seq, bad, minlen=6, gap=1):
    out=[]; cur=[]; miss=0
    for s in seq:
        if bad(s): cur.append(s); miss=0
        else:
            if cur:
                miss+=1
                if miss>gap:
                    if len(cur)>=minlen: out.append(cur)
                    cur=[]; miss=0
    if len(cur)>=minlen: out.append(cur)
    return out
# A: offset runs on same-name streets
bysi=collections.defaultdict(list)
for s in A: bysi[s['si']].append(s)
RA=[]
for si,seq in bysi.items():
    for r in runs(seq, lambda s: s['st']=='same' and s['d']>3.0):
        d=np.array([s['d'] for s in r]); sd=np.array([s['sd'] for s in r])
        RA.append(dict(name=r[0]['name'], osm=r[0]['osm'], L=len(r)*4, med=float(np.median(d)), sgn=float(np.mean(np.sign(sd)==np.sign(np.median(sd)))), x=float(np.mean([s['x'] for s in r])), y=float(np.mean([s['y'] for s in r])), pts=[(s['x'],s['y']) for s in r]))
# B: missing OSM runs
byoi=collections.defaultdict(list)
for s in B: byoi[s['oi']].append(s)
RB=[]
for oi,seq in byoi.items():
    for r in runs(seq, lambda s: not s['hit']):
        RB.append(dict(name=r[0]['name'], hw=r[0]['hw'], L=len(r)*4, x=float(np.mean([s['x'] for s in r])), y=float(np.mean([s['y'] for s in r])), pts=[(s['x'],s['y']) for s in r]))
# merge B runs of same name within 30 m
def merge(R):
    R=sorted(R,key=lambda r:-r['L']); out=[]
    for r in R:
        for o in out:
            if o['name']==r['name'] and min(np.hypot(px-qx,py-qy) for px,py in r['pts'][::3] for qx,qy in o['pts'][::3])<30:
                o['pts']+=r['pts']; o['L']+=r['L']; break
        else: out.append(dict(r))
    for o in out: o['x']=float(np.mean([p[0] for p in o['pts']])); o['y']=float(np.mean([p[1] for p in o['pts']]))
    return out
RB=merge(RB); RA=merge(RA)
print('A offset runs',len(RA),'total m',sum(r['L'] for r in RA)); print('B missing runs',len(RB),'total m',sum(r['L'] for r in RB))
pickle.dump(dict(RA=RA,RB=RB),open('osmchk/runs.pkl','wb'))
for r in sorted(RA,key=lambda r:-r['L'])[:60]: print(f"A {r['name'][:28]:28s} L{r['L']:5d} med {r['med']:5.1f} sgn {r['sgn']:.2f} @ {r['x']:.0f},{r['y']:.0f}")
