"""rail_compare.py (text/effect, 25 Nov 2026): what the text masks did to the rule's rail.
Plate 5: for each of the 23 railroad tracks Ben deleted (unet_data/5_rail_rule.json = runs/5_nets_base_tracks.json), its
class from diag/rail5 (groups.json and its by-eye reasons: house numbers 3-6, hook-mark lot lines 2, 7, 8, lot numbers
0-1) and whether a run still has railroad within 10 px of 20% or more of it ('kept'); plus the run's railroad tracks
lying near none of the 23 ('new'). No-ground runs are compared with 5_none_base (54 tracks, classes not known).
Plate 44: per Ben track, coverage at 10 px in each run (from the scorer's JSON), the tracks that lose 10 points or more.
    cd data/sanborn; python -B bench_2026-11-25/text/effect/code/rail_compare.py      -> scores/rail_compare.json"""
import json, os
import numpy as np, cv2
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); RU = os.path.join(ROOT, 'runs'); SC = os.path.join(ROOT, 'scores')
G5 = json.load(open(os.path.join(ROOT, '..', '..', 'diag', 'rail5', 'crops', 'groups.json')))
CLS = {0: 'lot numbers', 1: 'lot numbers', 2: 'hook-mark lot line', 3: 'house numbers', 4: 'house numbers', 5: 'house numbers', 6: 'house numbers', 7: 'hook-mark lot line', 8: 'hook-mark lot line'}
H5, W5 = 7150, 10076


def rr(f): return [np.array(t['pts'], float) for t in json.load(open(os.path.join(RU, f), encoding='utf8'))['tracks'] if t['kind'] == 'railroad']
def samp(p, step=2.0):
    S = [a + np.linspace(0, 1, max(2, int(np.hypot(*(b - a)) / step) + 1))[:-1, None] * (b - a) for a, b in zip(p[:-1], p[1:])]; S.append(p[-1:]); return np.vstack(S)
def plen(p): return float(np.hypot(*np.diff(p, axis=0).T).sum())
def dmap(T, H, W):
    m = np.zeros((H, W), np.uint8)
    for p in T: cv2.polylines(m, [np.round(p).astype(np.int32)], False, 1, 1)
    return cv2.distanceTransform((m == 0).astype(np.uint8), cv2.DIST_L2, 5)
def cover(p, D):
    q = samp(p).round().astype(int); q[:, 0] = q[:, 0].clip(0, D.shape[1] - 1); q[:, 1] = q[:, 1].clip(0, D.shape[0] - 1); return float((D[q[:, 1], q[:, 0]] <= 10).mean())


out = {'5_nets': {}, '5_none': {}, '44_map': {}}
base = rr('5_nets_base_tracks.json'); assert len(base) == 23
cls_of = {}
for g in G5:
    for i in g['tracks']: cls_of[i] = (g['group'], CLS[g['group']])
Db = dmap(base, H5, W5)
for run in ('base', 'tS0', 'tS1', 'tS1g2', 'tI', 'tInp', 'tI2'):
    T = rr(f'5_nets_{run}_tracks.json'); D = dmap(T, H5, W5); kept = {}
    for i, p in enumerate(base):
        c = cover(p, D); k = cls_of[i][1]; kept.setdefault(k, [0, 0, 0, 0.0]); kept[k][1] += 1; kept[k][3] += plen(p)
        if c >= 0.2: kept[k][0] += 1; kept[k][2] += plen(p)
    new = [round(plen(p)) for p in T if cover(p, Db) < 0.2]
    out['5_nets'][run] = dict(tracks=len(T), px=round(sum(plen(p) for p in T)), kept_of_23={k: f'{v[0]} of {v[1]} ({round(v[2])} of {round(v[3])} px)' for k, v in kept.items()},
                              kept_groups=sorted({cls_of[i][0] for i, p in enumerate(base) if cover(p, D) >= 0.2}), new_tracks_not_near_the_23=new)
    print('5 nets', run, out['5_nets'][run], flush=True)
nb = rr('5_none_base_tracks.json'); Dn = dmap(nb, H5, W5)
for run in ('base', 'tS1', 'tI', 'tI2'):
    T = rr(f'5_none_{run}_tracks.json'); D = dmap(T, H5, W5)
    out['5_none'][run] = dict(tracks=len(T), px=round(sum(plen(p) for p in T)), of_54_kept=sum(cover(p, D) >= 0.2 for p in nb), of_23_kept=sum(cover(p, D) >= 0.2 for p in base),
                              kept_groups_of_23=sorted({cls_of[i][0] for i, p in enumerate(base) if cover(p, D) >= 0.2}), new_not_near_54=[round(plen(p)) for p in T if cover(p, Dn) < 0.2])
    print('5 none', run, out['5_none'][run], flush=True)
S = {r: json.load(open(os.path.join(SC, f'44_map_{r}.json'))) for r in ('base', 'tS0', 'tS1', 'tS1g2', 'tI', 'tInp', 'tI2r')}
for r, s in S.items():
    tr = s['kinds']['railroad']['tol10']['tracks']; b = S['base']['kinds']['railroad']['tol10']['tracks']
    out['44_map'][r] = dict(recall10=s['kinds']['railroad']['tol10']['recall'], found_partial_missed=[s['kinds']['railroad']['tol10'][k] for k in ('found', 'partial', 'missed')],
                            streetcar_recall10=s['kinds']['streetcar']['tol10']['recall'], false_tracks=s['kinds']['railroad']['tol10']['false_tracks'],
                            lost_10pts=[dict(i=t['i'], len=t['len'], cov_base=bt['cov'], cov=t['cov'], a=t['a'], b=t['b']) for t, bt in zip(tr, b) if bt['cov'] - t['cov'] >= 0.1])
    print('44', r, out['44_map'][r], flush=True)
json.dump(out, open(os.path.join(SC, 'rail_compare.json'), 'w'), indent=1)
