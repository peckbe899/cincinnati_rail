import sys, json
from icp import run2
deg=int(sys.argv[1])
for sid in sys.argv[2:]:
    r=run2(sid,deg=deg); json.dump(r,open(f'boldx/r2_{deg}_{sid}.json','w'))
    print(sid,deg,'R %.3f->%.3f rms %.2f->%.2f edge %.2f zres %.2f it %d'%(r['R0'],r['R'],r['rms0'],r['rms'],r['edge_rms'],r['zres'],r['iters']),flush=True)
