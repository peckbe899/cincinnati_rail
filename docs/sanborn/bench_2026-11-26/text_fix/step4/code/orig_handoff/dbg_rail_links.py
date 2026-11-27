"""dbg_rail_links.py (handoff, 26 Nov 2026): debug only. The railroad rule of ink_bins_text.py with its inner results exposed
(source patched in memory), before and after the mask, on one window; prints the ticks and links near a point."""
import sys, os, json, inspect, textwrap
import numpy as np, cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ink_bins_text as IB
src = inspect.getsource(IB.railroad)
a = "    info['carrow'] = info_car\n"; assert src.count(a) == 1
src = src.replace(a, a + "    info['dbg'] = dict(Tc=Tc, uc=uc, Lc_all=Lc_all, Ec=Ec, Tf=Tf, Lf=Lf, Ef=Ef, near61=near61, near=near, heavy=heavy, ori=ori, ori2=ori2, stub=stub, long_=long_)\n")
g = dict(IB.__dict__); exec(src, g); RR = g['railroad']
N = sys.argv[1]; x0, y0, x1, y1 = map(int, sys.argv[2:6]); px, py = map(float, sys.argv[6:8])
im = cv2.imread(f'cufp/22-{N}.jpg'); H, W = im.shape[:2]; im = im[y0:y1, x0:x1]; h, w = im.shape[:2]
L = cv2.cvtColor(im, cv2.COLOR_BGR2LAB)[..., 0]; al = np.load(f'cufp/{N}/png_alpha_s4.npy'); paper = cv2.resize(al, (W, H), interpolation=cv2.INTER_NEAREST)[y0:y1, x0:x1] > 0
ink = (L < IB.INK_L) & paper; closed = np.zeros((h, w), np.uint8)
if os.path.exists(f'streetmap/22-{N}.json'):
    for bl in json.load(open(f'streetmap/22-{N}.json', encoding='utf8'))['blocks']: cv2.fillPoly(closed, [np.round(np.array(bl['ring']) - [x0, y0]).astype(np.int32)], 1)
tc = cv2.imread(f'bench_2026-11-25/text_v1/handoff/masks/{N}_text.png', 0)[y0:y1, x0:x1]; T = np.isin(tc, (2, 3)) & ink
P0 = np.array([px - x0, py - y0]); R = {}
for name, ik in (('before', ink), ('after', ink & ~T)):
    rr, info = RR(ik, closed, paper); d = info['dbg']; R[name] = d
    Tc = d['Tc']; sel = np.nonzero(np.hypot(*(Tc - P0).T) < 200)[0]
    print(name, 'clear ticks near point:', len(sel), [tuple(np.round(Tc[i] + [x0, y0]).astype(int)) for i in sel])
    E = d['Lc_all']; es = [(i, j) for i, j in E if i in set(sel) or j in set(sel)]; print('  links near', len(es), ' rows near', sum(1 for i, j in d['Ec'] if i in set(sel)))
    print('  stub px', int(d['stub'].sum()), 'long_ px', int(d['long_'].sum()), 'near61 px', int(d['near61'].sum()), 'heavy px', int(d['heavy'].sum()))
for k in ('stub', 'long_', 'near61', 'near', 'ori', 'ori2'):
    a, b = R['before'][k], R['after'][k]; diff = (a != b); ys, xs = np.nonzero(diff)
    print(k, 'differs at', int(diff.sum()), 'px', '' if not len(ys) else f'bbox {xs.min() + x0},{ys.min() + y0}-{xs.max() + x0},{ys.max() + y0}')
# links in detail (debug)
for name in ('before', 'after'):
    d = R[name]; Tc = d['Tc']; sel = set(np.nonzero(np.hypot(*(Tc - P0).T) < 200)[0].tolist())
    E = d['Lc_all']; Ec = {(min(i, j), max(i, j)) for i, j in d['Ec']}
    print(name, 'links (plate px) and whether in a row:')
    for i, j in E:
        if i in sel or j in sel: print('   ', tuple(np.round(Tc[i] + [x0, y0]).astype(int).tolist()), '-', tuple(np.round(Tc[j] + [x0, y0]).astype(int).tolist()), 'row' if (min(i, j), max(i, j)) in Ec else '-')
# stub components near the point (debug)
Q = np.array([float(v) for v in os.environ.get('DBG_Q', '5650,5684').split(',')]) - [x0, y0]
for name in ('before', 'after'):
    d = R[name]; n, lb, st, cs = cv2.connectedComponentsWithStats(d['stub'], connectivity=8)
    near_ = [(tuple(np.round(cs[i] + [x0, y0]).astype(int).tolist()), int(st[i, 4])) for i in range(1, n) if np.hypot(*(cs[i] - Q)) < 30]
    qy, qx = int(round(Q[1])), int(round(Q[0]))
    print(name, 'stubs within 30 px of', tuple((Q + [x0, y0]).astype(int)), near_, '| ori', int(d['ori'][qy, qx]), 'ori2', int(d['ori2'][qy, qx]), '| long_ in 9px box', int(d['long_'][qy - 4:qy + 5, qx - 4:qx + 5].sum()))
