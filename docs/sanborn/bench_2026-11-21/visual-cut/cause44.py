"""Plate 44: for each of Ben's street sides the batch did NOT give Ben, which step lost it (visual-cut, 21 Nov 2026).
Reads only; writes audit/44_cause.json and prints a summary.

Ben's printed and drawn lines (streetmap/22-44.json; sheet-edge lines left out) are sampled every 4 px. A sample is
'found' when an editor line (clean() of the batch's exported sides, out44/) lies within 6 px and 10 deg. For the samples
not found:
  line net drew it     P(line) > 0.5 within 3 px (44_lines_lines_ng1.png)
  area net: street     P(block) <= 0.5 at 10 px into the street side (44_pred_area_ng1.png); the street side is the
                       side not inside one of Ben's closed blocks (if both or neither are, 'unknown')
  in the block mask    the outline step's block mask (out44/44_blockmask.png) at 10 px into the street side: 1 means the
                       street was swallowed by a block (merge or spill); 0 means the street is there but the side was
                       not exported (dropped short piece, paper edge, or never fitted)
Lost-at classes: 'networks' (neither net saw it), 'area only' / 'line only' (one did), 'both nets, outline lost it'.
"""
import json, os
import numpy as np, cv2
from shapely.geometry import Polygon, Point
from shapely.prepared import prep
from vlib import load, SP, HERE

D = load('44'); W, H = D['W'], D['H']
sm = json.load(open(SP + 'streetmap/22-44.json', encoding='utf8'))
rings = [prep(Polygon(b['ring']).buffer(0)) for b in sm['blocks']]
pl = D['pl']; pa = cv2.resize(D['pa'], (W, H), interpolation=cv2.INTER_LINEAR); bm = cv2.resize(D['bm'], (W, H), interpolation=cv2.INTER_NEAREST) > 127
plmax = cv2.dilate(pl, np.ones((7, 7), np.uint8))
E = [(np.array(s['a'], float), np.array(s['b'], float)) for s in D['shown']]
EA = np.array([a for a, b in E]); EB = np.array([b for a, b in E])


def found(q, d):
    dd = EB - EA; L = np.hypot(*dd.T); u = dd / L[:, None]; ok = np.abs(u @ d) >= np.cos(np.radians(10))
    t = np.clip(((q[:, None, :] - EA[None]) * dd[None]).sum(2) / (L ** 2)[None], 0, 1)
    dist = np.hypot(*(q[:, None, :] - (EA[None] + t[..., None] * dd[None])).transpose(2, 0, 1))
    return ((dist <= 6) & ok[None]).any(1)


inb = lambda x, y: any(r.contains(Point(x, y)) for r in rings)
tot = dict(len=0.0, found=0.0); lost = {}; per_kind = {}
for l in sm['lines']:
    if l['kind'] == 'sheet_edge': continue
    a, b = np.array(l['a'], float), np.array(l['b'], float); L = float(np.hypot(*(b - a)))
    if L < 8: continue
    d = (b - a) / L; nrm = np.array([-d[1], d[0]]); q = a + np.outer(np.linspace(0, 1, max(3, int(L / 4))), b - a)
    f = found(q, d); step = L / len(q); tot['len'] += L; tot['found'] += f.sum() * step
    pk = per_kind.setdefault(l['kind'], [0.0, 0.0]); pk[0] += L; pk[1] += f.sum() * step
    for qq in q[~f]:
        x, y = int(round(qq[0])), int(round(qq[1]))
        if not (0 <= x < W and 0 <= y < H): continue
        side = None
        p1, p2 = qq + nrm * 10, qq - nrm * 10
        i1, i2 = inb(*p1), inb(*p2)
        if i1 != i2: side = p2 if i1 else p1
        ln = plmax[y, x] > 127
        if side is None: ar = 'unknown'; mk = 'unknown'
        else:
            sx, sy = int(np.clip(round(side[0]), 0, W - 1)), int(np.clip(round(side[1]), 0, H - 1))
            ar = 'street' if pa[sy, sx] <= 127 else 'block'; mk = 'swallowed' if bm[sy, sx] else 'street kept'
        cls = ('both nets' if ln and ar == 'street' else 'line only' if ln else 'area only' if ar == 'street' else 'networks' if ar == 'block' else 'line net missed, area unknown')
        key = f'{cls} | mask: {mk}'; lost[key] = lost.get(key, 0.0) + step
out = dict(ben_len=round(tot['len']), found_len=round(tot['found']), recall=round(tot['found'] / tot['len'], 3),
           recall_by_kind={k: round(v[1] / v[0], 3) for k, v in per_kind.items()}, lost_len_by_class={k: round(v) for k, v in sorted(lost.items(), key=lambda kv: -kv[1])})
json.dump(out, open(os.path.join(HERE, 'audit', '44_cause.json'), 'w'), indent=1); print(json.dumps(out, indent=1))
