"""score_rail.py (text_fix/step4, 27 Nov 2026): copy of text_v1/handoff/code/score_rail.py with the mask set as a choice and
one more run kind. Same definitions, same numbers (checked against the hand-off's rail.json for SET f3).

    cd data/sanborn; python -B bench_2026-11-26/text_fix/step4/code/score_rail.py --set f3|f4
Reads step4/runs/bins/<SET>/<run>_{before,after,afterstrict}.png and _tracks.json (and _after_tracks_nojoin.json, scored as
'after_nojoin' on the after bins); writes step4/scores/<SET>/rail.json and rail.txt.
  before        no mask
  after         mask + both rules tuned on 44 (text bridges tick gaps; joins across lettering)
  after_nojoin  mask + the bridge only
  afterstrict   mask + neither rule: the fair number

TRACK LEVEL (samples every 2 px; per kind, railroad and streetcar):
  recall10       share of Ben's length of that kind within 10 px of a rule track of that kind
  precision10    share of the rule tracks' length within 10 px of a Ben track of that kind
  found/partial/missed  Ben tracks covered >= 80% / 20-80% / < 20% at 10 px
  false tracks   rule tracks with under 20% of their length within 10 px of a Ben track of the same kind
INK LEVEL (the bins):
  ink_found      share of Ben's length (every 5 px) with ink of that bin within 10 px (railroad) / 30 px (streetcar)
  ink_far_px     px of that bin more than 15 px (railroad) / 25 px (streetcar) from every Ben track of that kind
Plate 5 has no railroad of Ben's: every rule railroad track there is false. Plate 1A's tracks are not complete: only
recall is meaningful there."""
import json, os, glob, sys
import numpy as np, cv2
from scipy.spatial import cKDTree
SP = os.getcwd().replace('\\', '/') + '/'; ST = SP + 'bench_2026-11-26/text_fix/step4/'
S = sys.argv[sys.argv.index('--set') + 1]; assert S in ('f3', 'f4')
R = ST + f'runs/bins/{S}/'; OUT = ST + f'scores/{S}/'; os.makedirs(OUT, exist_ok=True)
WHENS = (('before', 'before', '_tracks.json'), ('after', 'after', '_tracks.json'), ('after_nojoin', 'after', '_tracks_nojoin.json'), ('afterstrict', 'afterstrict', '_tracks.json'))


def samp(p, step=2.0):
    p = np.asarray(p, float); S_ = [p[:1]]
    for a, b in zip(p[:-1], p[1:]):
        n = max(1, int(np.ceil(np.hypot(*(b - a)) / step))); S_.append(a + np.linspace(0, 1, n + 1)[1:, None] * (b - a))
    return np.vstack(S_)


def track_score(tracks, B):
    r = {}
    for kind in ('railroad', 'streetcar'):
        bt = [samp(t['pts']) for t in B if t['kind'] == kind and len(t['pts']) > 1]
        rtk = [samp(t['pts']) for t in tracks if t['kind'] == kind and len(t['pts']) > 1]
        BT = cKDTree(np.vstack(bt)) if bt else None; RT = cKDTree(np.vstack(rtk)) if rtk else None
        false = 0; false_len = 0.0; tot = 0.0; good = 0.0
        for s in rtk:
            L = len(s) * 2.0; tot += L; near = (BT.query(s)[0] <= 10) if BT is not None else np.zeros(len(s), bool); good += near.sum() * 2.0
            if near.mean() < 0.2: false += 1; false_len += L
        cov = [(RT.query(s)[0] <= 10).mean() if RT is not None else 0.0 for s in bt]
        allb = np.vstack(bt) if bt else np.zeros((0, 2))
        rec = float((RT.query(allb)[0] <= 10).mean()) if (RT is not None and len(allb)) else (0.0 if len(allb) else None)
        r[kind] = dict(rule_tracks=len(rtk), rule_len=round(tot), false_tracks=false, false_len=round(false_len), ben_tracks=len(bt), ben_len=round(len(allb) * 2.0),
                       recall10=None if rec is None else round(rec, 4), precision10=round(good / tot, 4) if tot else None,
                       found_partial_missed=[int(sum(c >= 0.8 for c in cov)), int(sum(0.2 <= c < 0.8 for c in cov)), int(sum(c < 0.2 for c in cov))],
                       per_ben_track=[round(float(c), 3) for c in cov])
    return r


def ink_score(b, B):
    H, W = b.shape; r = {}
    for kind, code, tol, far in (('railroad', 4, 10, 15), ('streetcar', 5, 30, 25)):
        m = np.zeros((H, W), np.uint8); S_ = []
        for t in B:
            if t['kind'] != kind: continue
            p = np.array(t['pts'], float); cv2.polylines(m, [np.round(p).astype(np.int32)], False, 1, 1)
            for q0, q1 in zip(p[:-1], p[1:]): S_.append(q0[None] + np.linspace(0, 1, max(2, int(np.hypot(*(q1 - q0)) / 5) + 1))[:, None] * (q1 - q0)[None])
        d = cv2.distanceTransform((m == 0).astype(np.uint8), cv2.DIST_L2, 5); ink = b == code
        dk = cv2.distanceTransform((~ink).astype(np.uint8), cv2.DIST_L2, 5)
        if S_:
            q = np.vstack(S_).round().astype(int); q = q[(q[:, 0] >= 0) & (q[:, 0] < W) & (q[:, 1] >= 0) & (q[:, 1] < H)]; got = round(float((dk[q[:, 1], q[:, 0]] <= tol).mean()), 4)
        else: got = None
        r[kind] = dict(bin_px=int(ink.sum()), ink_found=got, ink_far_px=int((ink & (d > far)).sum()))
    return r


out = {}
for f in sorted(glob.glob(R + '*_before_tracks.json')):
    run = os.path.basename(f)[:-len('_before_tracks.json')]; N = run.split('_')[0]
    BJ = json.load(open(f'picks22_guided/22-{N}/rail_ben.json', encoding='utf8')); B = BJ['tracks']; out[run] = dict(plate=N, ben_complete=bool(BJ.get('complete')))
    for when, bins, suf in WHENS:
        if not os.path.exists(R + f'{run}_{bins}{suf}'): continue
        tr = json.load(open(R + f'{run}_{bins}{suf}', encoding='utf8'))['tracks']; b = cv2.imread(R + f'{run}_{bins}.png', 0)
        out[run][when] = dict(tracks=track_score(tr, B), ink=ink_score(b, B))
json.dump(out, open(OUT + 'rail.json', 'w', encoding='utf8', newline='\n'), indent=1)
L = [f'mask set {S}']
for run, v in out.items():
    L.append(f"== {run} (Ben's rail complete: {v['ben_complete']})")
    for kind in ('railroad', 'streetcar'):
        for when in [w for w, _, _ in WHENS if w in v]:
            t = v[when]['tracks'][kind]; i = v[when]['ink'][kind]
            L.append(f"  {kind:9s} {when:12s} rule tracks {t['rule_tracks']:3d} ({t['rule_len']:6d} px) | false {t['false_tracks']:3d} ({t['false_len']:6d} px) | recall10 {t['recall10']} precision10 {t['precision10']} | "
                     f"Ben {t['ben_tracks']} found/partial/missed {t['found_partial_missed']} | ink: found {i['ink_found']} far {i['ink_far_px']} px, bin {i['bin_px']} px")
open(OUT + 'rail.txt', 'w', encoding='utf8', newline='\n').write('\n'.join(L) + '\n'); print('\n'.join(L))
