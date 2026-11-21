"""outline-quality scratch probe: geometry of the 'parallel' bridges (angle, offset, overlap of the two sides). Prints."""
import json, sys
import numpy as np
sys.dont_write_bytecode = True
import sweep as S
B, O = S.B, S.O
S.init(B.U + '44_pred_area_ng1.png', B.U + '44_lines_lines_ng1.png')
P = json.loads(sys.argv[1])
polys, rep, _, block, inst = O.outline(S.G['D'], P, vis_out=False)
ben = S.G['ben']
rows = []
for p in polys:
    n = len(p)
    for k, s in enumerate(p):
        if s.get('bridge') != 'parallel': continue
        a, b = p[(k - 1) % n], p[(k + 1) % n]
        u1 = np.subtract(a['b'], a['a']); u2 = np.subtract(b['b'], b['a']); L1, L2 = np.hypot(*u1), np.hypot(*u2); u1 = u1 / L1; u2 = u2 / L2
        cos = float(u1 @ u2); n1 = np.array([-u1[1], u1[0]])
        off = float(abs((np.array(b['a']) - np.array(a['a'])) @ n1)); gap = float((np.array(b['a']) - np.array(a['b'])) @ u1)
        Lb = float(np.hypot(*np.subtract(s['b'], s['a'])))
        ls = B.LineSet([(s['a'], s['b'], 'x')], 20.0); okb = float((ls.dist_to(ben) <= 5).mean()) if len(ls.P) else 0
        rows.append((cos, off, gap, Lb, okb, s['state'], L1, L2))
R = np.array([r[:5] for r in rows])
print('n', len(R)); print('antiparallel (cos<0):', int((R[:, 0] < 0).sum()))
for lo, hi in ((0, 6), (6, 12), (12, 25), (25, 50), (50, 1e9)):
    m = (R[:, 0] > 0) & (R[:, 1] >= lo) & (R[:, 1] < hi)
    print(f'same direction, offset {lo}-{hi}: n={int(m.sum())}, bridge len {R[m, 3].sum():.0f}, on Ben {np.average(R[m, 4], weights=R[m, 3]) if m.any() else 0:.2f}, median gap {np.median(R[m, 2]) if m.any() else 0:.0f}')
m = R[:, 0] < 0; print(f'antiparallel: n={int(m.sum())}, len {R[m, 3].sum():.0f}, on Ben {np.average(R[m, 4], weights=R[m, 3]) if m.any() else 0:.2f}, median off {np.median(R[m, 1]) if m.any() else 0:.0f}')
