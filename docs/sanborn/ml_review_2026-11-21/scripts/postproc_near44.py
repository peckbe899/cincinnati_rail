"""Plate 44: perpendicular distance from each outline side to the nearest parallel Ben line (overlapping along it)"""
import json, numpy as np
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
sm = json.load(open(SP + 'streetmap/22-44.json', encoding='utf8'))
BL = [(np.array(l['a'], float), np.array(l['b'], float)) for l in sm['lines']]
o = json.load(open(SP + 'picks22_guided/22-44/outlines.json', encoding='utf8'))
def dist(a, b):
    d = (b - a) / np.hypot(*(b - a)); m = (a + b) / 2; best = 1e9
    for p, q in BL:
        e = q - p; Le = np.hypot(*e); en = e / Le
        if abs(en @ d) < np.cos(np.radians(6)): continue
        t = (m - p) @ en
        if t < -20 or t > Le + 20: continue
        best = min(best, abs((m - p) @ np.array([-en[1], en[0]])))
    return best
for cat in ('on print', 'not on a line', 'short'):
    S = [(np.array(s['a']), np.array(s['b'])) for p in o for s in p if s['state'] == cat and not s.get('paper_edge') and np.hypot(*np.subtract(s['b'], s['a'])) >= (28 if cat == 'short' else 0)]
    D = np.array([dist(a, b) for a, b in S]); W = np.array([np.hypot(*(b - a)) for a, b in S])
    bins = [0, 4, 8, 12, 20, 30, 45, 80, 1e10]
    h = [W[(D >= bins[i]) & (D < bins[i + 1])].sum() / W.sum() for i in range(len(bins) - 1)]
    print(f'{cat:14s} n={len(S):4d}: share of length by distance to nearest parallel Ben line ' + ', '.join(f'{bins[i]}-{bins[i + 1] if bins[i + 1] < 1e9 else "inf"}: {100 * h[i]:.0f}%' for i in range(len(h))))
