import sys, numpy as np, pickle
from win import windows
from geo import Sheet
sid=sys.argv[1]; res=windows(sid,coons=True)
pickle.dump(res,open(f'boldx/win_{sid}.pkl','wb'))
ok=[w for w in res if not w['edge'] and (w['c0']-w['cmin'])>0.2 and w['n']>800]
d=np.array([[w['dx'],w['dy']] for w in ok])
# convert sheet-px shift to grid-ft direction (approx: px ~ 1.0997 ft, v axis = south)
print(sid,'windows',len(res),'used',len(ok),'median shift px',np.median(d,0).round(1),'IQR dx',np.percentile(d[:,0],[25,75]).round(1),'dy',np.percentile(d[:,1],[25,75]).round(1),
      'zres med',round(float(np.median([w['zres'] for w in ok])),2))
