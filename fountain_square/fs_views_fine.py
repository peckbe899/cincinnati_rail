"""5-degree and 2-degree check round the leading facing (229 true at 20 to 32), scaled on the main grid's ranges -> views_fine.csv."""
import numpy as np, pandas as pd
from fs_views import score
g = pd.read_csv('views_scored.csv')
import sys
FC = int(sys.argv[1]) if len(sys.argv) > 1 else 229
ELS = [int(x) for x in sys.argv[2].split(',')] if len(sys.argv) > 2 else [20, 22, 24, 26, 28, 30, 32]
OUTF = sys.argv[3] if len(sys.argv) > 3 else 'views_fine.csv'
rows = [score(f, e) for e in ELS for f in (FC - 10, FC - 5, FC, FC + 5, FC + 10)]
d = pd.DataFrame(rows)
d['crowd'] = 1 / d['overlap']; d['sheet'] = np.exp(-np.abs(np.log(d['aspect'] / 1.6)))
d['rises'] = d['height']; d['levels'] = np.log(d['spread'])
nzg = lambda s, k: (s - g[k].min()) / (g[k].max() - g[k].min())
d['heights'] = 0.5 * nzg(d['rises'], 'rises') + 0.5 * nzg(d['levels'], 'levels')
W = dict(platforms=0.24, connections=0.10, stairs_read=0.12, heights=0.20, deep=0.14, crowd=0.09, court=0.07, sheet=0.04)
for k in W:
    d[k + '_n'] = nzg(d[k], k)                     # heights rescaled on the grid's range, as fs_views_score.py does
d['raw'] = sum(d[k + '_n'] * w for k, w in W.items())
d.to_csv(OUTF, index=False)
for c in ('raw', 'stairs_read', 'aspect'):
    print(c); print(d.pivot(index='elev', columns='facing', values=c).round(3).to_string())
