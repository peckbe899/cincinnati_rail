"""v-code: what ink_bins.block_ground makes of an outline run's polygons, against the watershed blocks it came from
(DIR/N_blockinst.png, half size), and how much of each street-hole polygon lies on watershed block ground (read only)."""
import json, sys
import numpy as np, cv2
sys.path.insert(0, 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-21/merge/staged/tools/sanborn/unet'); import ink_bins as IB  # noqa
D, N = sys.argv[1], sys.argv[2]
P = json.load(open(D + '/outlines.json', encoding='utf8')); inst = cv2.imread(D + f'/{N}_blockinst.png', cv2.IMREAD_UNCHANGED).astype(np.int32); h, w = inst.shape
half = [[dict(s, a=[v / 2 for v in s['a']], b=[v / 2 for v in s['b']]) for s in p] for p in P]
G = IB.block_ground(half, h, w); ws = inst > 0
res = dict(plate=N, polys=len(P), holes=sum(1 for p in P if p[0].get('hole')), ws_block_px=int(ws.sum()), ground_px=int(G.sum()),
           ws_block_not_ground=int((ws & (G == 0)).sum()), ground_not_ws_block=int(((G > 0) & ~ws).sum()))
per = []
for p in half:
    if not p[0].get('hole'): continue
    m = np.zeros((h, w), np.uint8); cv2.fillPoly(m, [np.round(np.array([s['a'] for s in p])).astype(np.int32)], 1); m = m > 0
    per.append(dict(hole_px=int(m.sum()), on_ws_block=round(float((m & ws).sum() / max(1, m.sum())), 3), blocks_touched=int(len(np.unique(inst[m & ws])))))
res['holes_detail'] = per
print(json.dumps(res))
