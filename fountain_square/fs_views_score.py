"""Scores views.csv. Weights in Ben's order of importance (2026-10-05): platforms, stairs, heights, TRI, uncrowded,
sunken court, fits sheet; heights much heavier than before. 'Stairs' is two tests: flights seen at all, and flights
wide enough on the page to read as stairs."""
import sys, numpy as np, pandas as pd
d = pd.read_csv('views.csv')
d['crowd'] = 1 / d['overlap']; d['sheet'] = np.exp(-np.abs(np.log(d['aspect'] / 1.6)))
# heights, in two halves from Ben's two complaints: rises read true (11-14 looked taller than 17/18), and levels read apart
# (the -1 level looked wrong higher up). Levels apart is a ratio, so it is scaled on a log.
d['rises'] = d['height']; d['levels'] = np.log(d['spread'])
nz = lambda s: (s - s.min()) / (s.max() - s.min())
d['heights'] = 0.5 * nz(d['rises']) + 0.5 * nz(d['levels'])
W = dict(platforms=0.24, connections=0.10, stairs_read=0.12, heights=0.20, deep=0.14, crowd=0.09, court=0.07, sheet=0.04)
assert abs(sum(W.values()) - 1) < 1e-9
for k in list(W) + ['rises', 'levels']:
    d[k + '_n'] = nz(d[k])
d['raw'] = sum(d[k + '_n'] * w for k, w in W.items())
F = sorted(d.facing.unique()); E = sorted(d.elev.unique())
g = d.pivot(index='elev', columns='facing', values='raw').loc[E, F].values
S = np.zeros_like(g)
for i in range(len(E)):
    for j in range(len(F)):
        rows = [r for r in (i - 1, i, i + 1) if 0 <= r < len(E)]
        S[i, j] = np.mean([g[r, (j + k) % len(F)] for r in rows for k in (-1, 0, 1)])
sm = pd.DataFrame(S, index=E, columns=F).stack().rename('score').reset_index().rename(columns={'level_0': 'elev', 'level_1': 'facing'})
d = d.merge(sm.rename(columns={'score': 'smooth'}), on=['elev', 'facing'])
d['score'] = d['raw']   # unsmoothed: robustness is now checked directly at 5-degree steps (views_fine.csv)
d.to_csv('views_scored.csv', index=False)
cols = ['facing', 'elev', 'score', 'raw', 'platforms', 'stairs_read', 'connections', 'rises', 'levels_n', 'deep', 'overlap', 'court', 'aspect']
print(d.sort_values('score', ascending=False)[cols].head(15).round(3).to_string(index=False))
print('\nbest facing at each elevation:')
for e in E:
    r = d[d.elev == e].sort_values('score', ascending=False).iloc[0]
    print(int(e), int(r.facing), round(r.score, 3), 'aspect', round(r.aspect, 2))
print('\nnamed views:')
for f, e in ((229, 28), (229, 32), (139, 12), (199, 28), (19, 20), (19, 36)):
    r = d[(d.facing == f) & (d.elev == e)].iloc[0]; print(f, e, round(r.score, 3), 'rank', int((d.score > r.score).sum()) + 1)
