try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import sys, json, time, multiprocessing as mp
sys.path.insert(0, (_ws.CODE + 'plots'))
from gen import block_plots, polys
from frontage import Faces
from common import Tiles, SP
F = T = None
def init():
    global F, T; F = Faces(); T = Tiles()
def work(i):
    b = F.blocks[i]
    try: pl = block_plots(F, T, b)
    except Exception as e: return b['id'], [], str(e)
    out = []
    for p in pl:
        for q in polys(p['g']):
            if q.area < 1: continue
            out.append(dict(kind=p['kind'], street=p.get('street'), w=p.get('w'), run=p.get('run', -1), s=p.get('s', 0.0), c=[[round(x, 1), round(y, 1)] for x, y in q.exterior.coords[:-1]], a=round(q.area, 1)))
    return b['id'], out, None
if __name__ == '__main__':
    t0 = time.time(); F0 = Faces(); n = len(F0.blocks)
    with mp.Pool(2, initializer=init) as pool: res = pool.map(work, range(n), chunksize=8)
    blocks = {b['id']: b for b in F0.blocks}; feats = []; errs = []
    for bid, pl, err in res:
        if err: errs.append((bid, err))
        pl.sort(key=lambda p: (p['run'], p['s']))
        for k, p in enumerate(pl):
            feats.append(dict(id='%s-%03d' % (bid, k + 1), block=bid, src=blocks[bid]['src'], kind=p['kind'], street=p['street'], w=p['w'], a=p['a'], c=p['c']))
    json.dump(dict(plots=feats), open(SP + 'plots/plots_all.json', 'w'))
    print('blocks', n, 'plots', len(feats), 'errors', len(errs), errs[:5], 'time', round(time.time() - t0, 1))
