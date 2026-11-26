"""Gate scorer's own track scorer (26 Nov 2026), written from the definitions in text/verify rail_recheck.py and
handoff score_rail.py, not from their code. Ben's tracks picks22_guided/22-N/rail_ben.json (read only).
    cd data/sanborn; python -B bench_2026-11-25/text_v1/gate/scripts/my_rail.py OUT.json RUNDIR [RUNDIR ...]
Each RUNDIR holds <run>_{before,after,afterstrict}_tracks.json (rail_tracks_text.py output); run name starts with the plate.
Per kind: points every 2 px along each polyline. recall10 = Ben points within 10 px of a rule point of that kind;
precision10 = rule points within 10 px of a Ben point; Ben track found >= 80% covered, partial 20-80%, missed < 20%;
false track = rule track with under 20% of its points within 10 px of Ben's."""
import glob, json, os, re, sys
import numpy as np
from scipy.spatial import cKDTree


def pts(p, step=2.0):
    p = np.asarray(p, float); out = [p[:1]]
    for a, b in zip(p[:-1], p[1:]):
        n = max(1, int(np.ceil(np.hypot(*(b - a)) / step))); out.append(a + (np.arange(1, n + 1) / n)[:, None] * (b - a))
    return np.vstack(out)


def score(tracks, ben):
    r = {}
    for k in ('railroad', 'streetcar'):
        B = [pts(t['pts']) for t in ben if t['kind'] == k and len(t['pts']) > 1]
        T = [pts(t['pts']) for t in tracks if t['kind'] == k and len(t['pts']) > 1]
        if T: tT = cKDTree(np.vstack(T))
        if B: tB = cKDTree(np.vstack(B))
        cov = [float(np.mean(tT.query(b, distance_upper_bound=10.0)[0] <= 10)) if T else 0.0 for b in B]
        tp = [float(np.mean(tB.query(t, distance_upper_bound=10.0)[0] <= 10)) if B else 0.0 for t in T]
        nb = sum(len(b) for b in B); nt = sum(len(t) for t in T)
        r[k] = dict(ben_tracks=len(B), rule_tracks=len(T),
                    recall10=round(sum(c * len(b) for c, b in zip(cov, B)) / nb, 4) if nb else None,
                    precision10=round(sum(c * len(t) for c, t in zip(tp, T)) / nt, 4) if nt else None,
                    found=sum(c >= 0.8 for c in cov), partial=sum(0.2 <= c < 0.8 for c in cov), missed=sum(c < 0.2 for c in cov),
                    false=sum(c < 0.2 for c in tp), false_len=int(sum(2 * len(t) for c, t in zip(tp, T) if c < 0.2)),
                    per_ben=[round(c, 3) for c in cov])
    return r


out = {}
for D in sys.argv[2:]:
    for f in sorted(glob.glob(os.path.join(D, '*_tracks.json'))):
        run = os.path.basename(f)[:-len('_tracks.json')]
        if run.endswith('_nojoin'): continue
        N = run.split('_')[0]; bf = f'picks22_guided/22-{N}/rail_ben.json'
        if not os.path.exists(bf): continue
        bj = json.load(open(bf, encoding='utf8')); r = score(json.load(open(f))['tracks'], bj['tracks'])
        out[f'{os.path.basename(os.path.normpath(D))}/{run}'] = r
        print(f'{os.path.basename(os.path.normpath(D)):6s} {run:24s} complete={bj.get("complete")} ' + ' | '.join(
            f"{k} R10 {v['recall10']} P10 {v['precision10']} f/p/m {v['found']}/{v['partial']}/{v['missed']} false {v['false']} ({v['false_len']} px)" for k, v in r.items()))
json.dump(out, open(sys.argv[1], 'w'), indent=1)
