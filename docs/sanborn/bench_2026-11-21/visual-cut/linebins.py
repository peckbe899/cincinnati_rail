"""Which ink each editor line lies on, by the rule bins of the same batch (N_bins.png), and how much outline the export
drops as short pieces (visual-cut, 21 Nov 2026). Reads only; writes audit/N_linebins.json and prints a summary.

    python linebins.py N [N ...]

For each editor line (vlib.load: clean(N_edges.json)) the bin met first within 3 px across the line at each sample is
taken, and the line gets its majority bin: 0 no ink, 3 building outline, 4 railroad, 5 streetcar, 8 text and numbers,
9 not sorted (on unplaced plates the rules have no street map, so a true block line shows as 3 or 9, never 1).
Dropped outline: total length of outlines.json 'short' sides, and of paper-edge sides, against the exported length.
"""
import json, os, sys
import numpy as np, cv2
from vlib import load, U, HERE

for n in sys.argv[1:]:
    D = load(n); bins = cv2.imread(U + f'{n}_bins.png', cv2.IMREAD_UNCHANGED); H, W = bins.shape; res = []
    for s in D['shown']:
        a, b = np.array(s['a'], float), np.array(s['b'], float); L = float(np.hypot(*(b - a))); d = (b - a) / L; nrm = np.array([-d[1], d[0]])
        q = a + np.outer(np.linspace(0.1, 0.9, max(5, int(L / 4))), b - a); v = []
        for qq in q:
            best = 0
            for o in (0, -1, 1, -2, 2, -3, 3):
                x, y = (qq + nrm * o).round().astype(int)
                if 0 <= x < W and 0 <= y < H and bins[y, x]: best = int(bins[y, x]); break
            v.append(best)
        h = np.bincount(v, minlength=10) / len(v); res.append(dict(a=s['a'], b=s['b'], L=round(L, 1), maj=int(h.argmax()), share={k: round(float(h[k]), 2) for k in (0, 3, 4, 5, 8, 9) if h[k] > 0}))
    sl = lambda st: sum(float(np.hypot(*(np.array(x['b']) - np.array(x['a'])))) for p in D['polys'] for x in p if st(x))
    short = sl(lambda x: x['state'] == 'short'); pe = sl(lambda x: x['state'] != 'short' and x.get('paper_edge')); ex = sl(lambda x: x['state'] != 'short' and not x.get('paper_edge'))
    by = {}
    for r in res: e = by.setdefault(r['maj'], [0, 0.0]); e[0] += 1; e[1] += r['L']
    summ = dict(plate=n, by_bin={k: [v[0], round(v[1])] for k, v in sorted(by.items())}, exported_len=round(ex), short_len=round(short), paper_edge_len=round(pe), short_share_of_outline=round(short / (short + ex + pe), 3))
    json.dump(dict(summary=summ, lines=res), open(os.path.join(HERE, 'audit', f'{n}_linebins.json'), 'w'))
    print(json.dumps(summ), flush=True)
