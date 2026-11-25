"""verify: independent track-level rescoring of the effect agent's rail runs, and the finder's masked runs (25 Nov 2026).

    cd data/sanborn; python -B bench_2026-11-25/text/verify/scripts/rail_recheck.py

My own scorer (not score_rail_bench.py). For each run: the rule's railroad and streetcar tracks; against Ben's rail_ben.json
(picks22_guided/22-N, read only):
  false track    a rule track with under 20% of its length (sampled every 2 px) within 10 px of a Ben track of the same kind
  recall10       share of Ben's length of that kind (every 2 px) within 10 px of a rule track of that kind
  found/partial/missed  Ben tracks covered >= 80% / 20-80% / < 20% at 10 px
Effect runs: their stored runs/N_*_tracks.json. Finder runs: tracks made here from finder/rail/N_{base,masked}_bins.png
with the repo's rail_tracks.py (imported read-only, byte-identical to effect/code/orig). Writes verify/out/rail_recheck.json."""
import json, os, sys, glob, importlib.util
import numpy as np, cv2
from scipy.spatial import cKDTree

SP = os.getcwd(); V = os.path.join(SP, 'bench_2026-11-25', 'text', 'verify'); E = os.path.join(SP, 'bench_2026-11-25', 'text', 'effect')
FD = os.path.join(SP, 'bench_2026-11-25', 'text', 'finder', 'rail')
spec = importlib.util.spec_from_file_location('rt', os.path.join(SP, '..', '..', 'tools', 'sanborn', 'unet', 'rail_tracks.py')); rt = importlib.util.module_from_spec(spec); spec.loader.exec_module(rt)


def samp(p, step=2.0):
    p = np.asarray(p, float); S = [p[:1]]
    for a, b in zip(p[:-1], p[1:]):
        n = max(1, int(np.ceil(np.hypot(*(b - a)) / step))); S.append(a + np.linspace(0, 1, n + 1)[1:, None] * (b - a))
    return np.vstack(S)


def score(tracks, N):
    B = json.load(open(f'picks22_guided/22-{N}/rail_ben.json', encoding='utf8'))['tracks']; r = {}
    for kind in ('railroad', 'streetcar'):
        bt = [samp(t['pts']) for t in B if t['kind'] == kind and len(t['pts']) > 1]
        rtk = [samp(t['pts']) for t in tracks if t['kind'] == kind and len(t['pts']) > 1]
        BT = cKDTree(np.vstack(bt)) if bt else None; RT = cKDTree(np.vstack(rtk)) if rtk else None
        false = 0; false_len = 0.0; tot = 0.0
        for s in rtk:
            L = len(s) * 2.0; tot += L
            near = (BT.query(s)[0] <= 10).mean() if BT is not None else 0.0
            if near < 0.2: false += 1; false_len += L
        cov = [(RT.query(s)[0] <= 10).mean() if RT is not None else 0.0 for s in bt]
        allb = np.vstack(bt) if bt else np.zeros((0, 2))
        rec = float((RT.query(allb)[0] <= 10).mean()) if (RT is not None and len(allb)) else (0.0 if len(allb) else None)
        r[kind] = dict(rule_tracks=len(rtk), false_tracks=false, false_len=round(false_len), rule_len=round(tot), ben_tracks=len(bt),
                       recall10=None if rec is None else round(rec, 4),
                       found_partial_missed=[int(sum(c >= 0.8 for c in cov)), int(sum(0.2 <= c < 0.8 for c in cov)), int(sum(c < 0.2 for c in cov))])
    return r


out = {}
for f in sorted(glob.glob(os.path.join(E, 'runs', '*_tracks.json'))):
    name = os.path.basename(f)[:-12]; N = name.split('_')[0]
    out['effect:' + name] = score(json.load(open(f, encoding='utf8'))['tracks'], N)
for N in ('44', '5'):
    for run in ('base', 'masked'):
        b = cv2.imread(os.path.join(FD, f'{N}_{run}_bins.png'), 0)
        rr = rt.railroad_tracks((b == 4).astype(np.uint8)); car = rt.streetcar_tracks((b == 5).astype(np.uint8))
        tr = [dict(kind=k, pts=[[float(x), float(y)] for x, y in p]) for k, P in (('railroad', rr), ('streetcar', car)) for p in P]
        json.dump(dict(plate=N, note='verify: tracks from finder/rail bins, not truth', tracks=tr), open(os.path.join(V, 'out', f'finder_{N}_{run}_tracks.json'), 'w'))
        out[f'finder:{N}_{run}'] = score(tr, N)
for k, v in out.items():
    print(f"{k:28s} RR tracks {v['railroad']['rule_tracks']:3d} false {v['railroad']['false_tracks']:3d} ({v['railroad']['false_len']:6d} px) recall {v['railroad']['recall10']} f/p/m {v['railroad']['found_partial_missed']} | SC tracks {v['streetcar']['rule_tracks']:3d} false {v['streetcar']['false_tracks']:2d} recall {v['streetcar']['recall10']} f/p/m {v['streetcar']['found_partial_missed']}")
json.dump(out, open(os.path.join(V, 'out', 'rail_recheck.json'), 'w'), indent=1)
