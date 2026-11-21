"""Gaps in Ben's own tracks: pairs of track ends of the same kind, 60-800 px apart, that face each other along one line
(each end's direction points at the other within 20 degrees). Read-only.  python bench_2026-11-21/rail/truth_gaps.py TRUTH.json"""
import sys, json, numpy as np
T = [t for t in json.load(open(sys.argv[1], encoding='utf8'))['tracks'] if t.get('src') != 'rule']
E = []
for i, t in enumerate(T):
    p = np.asarray(t['pts'], float)
    for end, q, r in ((0, p[0], p[min(1, len(p) - 1)]), (1, p[-1], p[max(-2, -len(p))])):
        d = q - r; E.append((i, end, q, d / max(1e-6, np.hypot(*d)), t['kind']))
tot = {}
for a in range(len(E)):
    for b in range(a + 1, len(E)):
        i, _, qa, da, ka = E[a]; j, _, qb, db, kb = E[b]
        if i == j or ka != kb: continue
        v = qb - qa; L = np.hypot(*v)
        if not 60 <= L <= 800: continue
        u = v / L
        if da @ u > np.cos(np.radians(20)) and db @ -u > np.cos(np.radians(20)):
            print(f'{ka:9s} gap {L:4.0f} px between track {i} ({qa[0]:.0f},{qa[1]:.0f}) and track {j} ({qb[0]:.0f},{qb[1]:.0f})'); tot[ka] = tot.get(ka, 0) + L
print('total', {k: round(v) for k, v in tot.items()})
