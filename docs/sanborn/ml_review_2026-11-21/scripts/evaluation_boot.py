"""Tile bootstrap (1024 px tiles of plate 44) for line recall / precision: how wide is the uncertainty from one plate?"""
import json, sys, numpy as np, evallib as E
def per_sample(pred, tru, tol=4.0, ang=20.0, step=2.0):
    P, Pd, _ = E.sample(pred, step); Q, Qd, _ = E.sample(tru, step)
    return P, E.matched(P, Pd, Q, Qd, tol, ang), Q, E.matched(Q, Qd, P, Pd, tol, ang)
def editor_lines(OJ):
    polys = json.load(open(OJ)); edges = [dict(src='read', name='', a=s['a'], b=s['b'], state='green' if s['state'] == 'on print' else 'orange') for p in polys for s in p if s['state'] != 'short' and not s.get('paper_edge')]
    return [(e['a'], e['b']) for e in E.clean(edges)]
T = E.truth('44'); ben_all = [(l['a'], l['b']) for l in T['lines']]; ben_in = [(l['a'], l['b']) for l in T['lines'] if l['kind'] != 'sheet_edge']
runs = {k: editor_lines(v) for k, v in (a.split('=') for a in sys.argv[1:])}
tile = lambda X: (X[:, 0] // 1024).astype(int) * 100 + (X[:, 1] // 1024).astype(int)
data = {}
for k, segs in runs.items():
    P, pm, _, _ = per_sample(segs, ben_all); _, _, Q, qm = per_sample(segs, ben_in)
    data[k] = (tile(P), pm, tile(Q), qm)
tiles = sorted(set(np.concatenate([d[0] for d in data.values()] + [d[2] for d in data.values()])))
rng = np.random.default_rng(0); B = 2000; out = {}
S = [rng.choice(tiles, len(tiles)) for _ in range(B)]          # the same tile draws for every run: a paired comparison
draws = {}
for k, (tp, pm, tq, qm) in data.items():
    sp = {t: (pm[tp == t].sum(), (tp == t).sum()) for t in tiles}; sq = {t: (qm[tq == t].sum(), (tq == t).sum()) for t in tiles}
    pr, rc = [], []
    for s in S:
        a = np.array([sp[t] for t in s]).sum(0); b = np.array([sq[t] for t in s]).sum(0)
        pr.append(a[0] / max(1, a[1])); rc.append(b[0] / max(1, b[1]))
    draws[k] = (np.array(pr), np.array(rc))
    out[k] = dict(precision=round(float(pm.mean()), 3), precision_95=[round(float(np.percentile(pr, 2.5)), 3), round(float(np.percentile(pr, 97.5)), 3)],
                  recall_interior=round(float(qm.mean()), 3), recall_95=[round(float(np.percentile(rc, 2.5)), 3), round(float(np.percentile(rc, 97.5)), 3)], tiles=len(tiles))
ks = list(draws)
for i in range(len(ks)):
    for j in range(i + 1, len(ks)):
        dp = draws[ks[j]][0] - draws[ks[i]][0]; dr = draws[ks[j]][1] - draws[ks[i]][1]
        out[f'{ks[j]}_minus_{ks[i]}'] = dict(precision_95=[round(float(np.percentile(dp, 2.5)), 3), round(float(np.percentile(dp, 97.5)), 3)], recall_95=[round(float(np.percentile(dr, 2.5)), 3), round(float(np.percentile(dr, 97.5)), 3)])
print(json.dumps(out, indent=1))
