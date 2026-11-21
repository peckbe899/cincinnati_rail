"""Notches: where one straight block side is interrupted by a run of dropped short pieces that dips into the block
(visual-cut, 21 Nov 2026). Reads only; writes audit/N_notches.json and prints a summary.

    python notches.py N [N ...]

In outlines.json each polygon is a ring of sides. A notch is a run of 'short' sides between two 'line' sides that lie on
one straight line (angle < 5 deg, both ends of the second within 15 px of the first's line). gap = distance between the
two line ends; depth = how far the dropped run goes in from that line. Shallow notches (depth < 30 px) are mostly the
area network's edge dipping at house numbers or a lot line (the 'broken side' of the review, pp-3). Deep notches
(depth >= 30 px) are mostly where the area network saw a street or alley entering the block but the outline step did
not cut it through (an alley or a stub street that ends up merged).
Plate 44: each notch is checked against Ben's street map: 'ben_mouth' = 2 or more of Ben's line ends within 60 px of the
notch's middle (a street or alley mouth on his map).
"""
import json, os, sys
import numpy as np
from vlib import SP, HERE


def notches(polys):
    out = []
    for pi, p in enumerate(polys):
        n = len(p)
        if n < 4: continue
        # signed area of the ring, to know which side is inside
        ring = np.array([s['a'] for s in p], float); A = 0.5 * np.sum(ring[:, 0] * np.roll(ring[:, 1], -1) - np.roll(ring[:, 0], -1) * ring[:, 1])
        isline = [s['state'] != 'short' for s in p]
        for i in range(n):
            if not isline[i]: continue
            j = (i + 1) % n; run = []
            while not isline[j] and len(run) < n: run.append(j); j = (j + 1) % n
            if not run or j == i: continue
            a1, b1 = np.array(p[i]['a'], float), np.array(p[i]['b'], float); a2, b2 = np.array(p[j]['a'], float), np.array(p[j]['b'], float)
            d1 = (b1 - a1) / (np.hypot(*(b1 - a1)) or 1); d2 = (b2 - a2) / (np.hypot(*(b2 - a2)) or 1)
            if d1 @ d2 < np.cos(np.radians(5)): continue
            nrm = np.array([-d1[1], d1[0]])
            if max(abs((a2 - b1) @ nrm), abs((b2 - b1) @ nrm)) > 15: continue
            gap = float(np.hypot(*(a2 - b1)))
            if gap < 5: continue
            pts = np.array([p[k]['a'] for k in run] + [p[k]['b'] for k in run], float)
            # inside is to the left of travel for a counter-clockwise ring (A > 0 in image coords means clockwise on screen)
            sgn = 1 if A > 0 else -1
            depth = float(max(0.0, np.max(((pts - b1) @ nrm) * sgn)))
            depth_out = float(max(0.0, np.max(-((pts - b1) @ nrm) * sgn)))
            out.append(dict(poly=pi, at=((b1 + a2) / 2).round(1).tolist(), gap=round(gap, 1), depth=round(max(depth, depth_out), 1), inward=round(depth, 1), outward=round(depth_out, 1),
                            paper_edge=bool(p[i].get('paper_edge') or p[j].get('paper_edge'))))
    return out


if __name__ == '__main__':
    for n in sys.argv[1:]:
        if n == '44': polys = json.load(open(os.path.join(HERE, 'out44', '44_outlines_poly.json')))
        else: polys = json.load(open(SP + f'picks22_guided/22-{n}/outlines.json', encoding='utf8'))
        N = [x for x in notches(polys) if not x['paper_edge']]
        if n == '44':
            sm = json.load(open(SP + 'streetmap/22-44.json', encoding='utf8')); E = np.array([e for l in sm['lines'] if l['kind'] != 'sheet_edge' for e in (l['a'], l['b'])], float)
            for x in N: x['ben_mouth'] = int((np.hypot(*(E - np.array(x['at'])).T) < 60).sum())
        deep = [x for x in N if x['depth'] >= 30]; shallow = [x for x in N if x['depth'] < 30]
        s = dict(plate=n, notches=len(N), deep=len(deep), deep_gap_med=float(np.median([x['gap'] for x in deep])) if deep else 0, shallow=len(shallow), shallow_gap_sum=round(sum(x['gap'] for x in shallow)))
        if n == '44':
            s.update(deep_at_ben_mouth=sum(x['ben_mouth'] >= 2 for x in deep), shallow_at_ben_mouth=sum(x['ben_mouth'] >= 2 for x in shallow))
        json.dump(dict(summary=s, notches=N), open(os.path.join(HERE, 'audit', f'{n}_notches.json'), 'w'))
        print(json.dumps(s), flush=True)
