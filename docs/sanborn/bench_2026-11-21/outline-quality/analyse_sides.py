"""outline-quality: precision of exported sides by kind (fitted side or bridge), state and length, for one setting.
    python analyse_sides.py '{"rings": true}'
Exported = what step 4 keeps (not short, not paper edge). A side's share on Ben's lines at 5 px / 20 deg, by length.
Prints a table; writes nothing."""
import json, sys
import numpy as np
sys.dont_write_bytecode = True
import sweep as S  # noqa: E402
B, O = S.B, S.O
P = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {}
S.init(B.U + '44_pred_area_ng1.png', B.U + '44_lines_lines_ng1.png')
polys, rep, _, block, inst = O.outline(S.G['D'], P, vis_out=False)
items = [(s['a'], s['b'], ('bridge:' + str(s['bridge']) if s.get('bridge') else 'side') + '|' + s['state']) for p in polys for s in p if s['state'] != 'short' and not s.get('paper_edge')]
ls = B.LineSet(items, 20.0); dp = ls.dist_to(S.G['ben']); ok = dp <= 5
L = np.array([np.hypot(*(np.array(b) - np.array(a))) for a, b, _ in items]); lab = np.array([k for _, _, k in items])
print(rep)
for k in sorted(set(lab)):
    sel = np.isin(ls.ix, np.nonzero(lab == k)[0])
    print(f'{k:40s} n={int((lab == k).sum()):5d} len={int(sel.sum()):7d} on Ben {ok[sel].mean():.3f}')
for lo, hi in ((0, 28), (28, 60), (60, 130), (130, 300), (300, 1e9)):
    for kind in ('side', 'bridge'):
        idx = np.nonzero((L >= lo) & (L < hi) & np.char.startswith(lab.astype(str), kind))[0]; sel = np.isin(ls.ix, idx)
        if sel.any(): print(f'{kind:6s} length {lo:4.0f}-{hi:5.0f}: n={len(idx):4d} len={int(sel.sum()):7d} on Ben {ok[sel].mean():.3f}')
