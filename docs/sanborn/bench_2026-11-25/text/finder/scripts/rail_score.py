"""Score the railroad bin of rail_with_mask.py runs against Ben's tracks (picks22_guided/22-N/rail_ben.json), as
ink_bins.py itself does when his tracks are on: share of his railroad length (sampled every 5 px) with railroad-bin ink
within 10 px, and railroad-bin px more than 15 px from every railroad track of his (false). Same for streetcar (30 px / 25 px).
    cd data/sanborn; python -B <this> RAIL_DIR N [N ...]"""
import sys, os, json
sys.dont_write_bytecode = True
import numpy as np, cv2
D = sys.argv[1]; out = {}
for N in sys.argv[2:]:
    B = json.load(open(f'picks22_guided/22-{N}/rail_ben.json', encoding='utf8')); r = dict(complete=B.get('complete'))
    for run in ('base', 'masked'):
        b = cv2.imread(os.path.join(D, f'{N}_{run}_bins.png'), 0); H, W = b.shape; rr = {}
        for kind, code, tol, far in (('railroad', 4, 10, 15), ('streetcar', 5, 30, 25)):
            m = np.zeros((H, W), np.uint8); S = []
            for t in B['tracks']:
                if t['kind'] != kind: continue
                p = np.array(t['pts'], float); cv2.polylines(m, [np.round(p).astype(np.int32)], False, 1, 1)
                for q0, q1 in zip(p[:-1], p[1:]): S.append(q0[None] + np.linspace(0, 1, max(2, int(np.hypot(*(q1 - q0)) / 5) + 1))[:, None] * (q1 - q0)[None])
            d = cv2.distanceTransform((m == 0).astype(np.uint8), cv2.DIST_L2, 5); ink = b == code
            dk = cv2.distanceTransform((~ink).astype(np.uint8), cv2.DIST_L2, 5)
            if S:
                q = np.vstack(S).round().astype(int); q = q[(q[:, 0] >= 0) & (q[:, 0] < W) & (q[:, 1] >= 0) & (q[:, 1] < H)]; got = float((dk[q[:, 1], q[:, 0]] <= tol).mean())
            else: got = None
            rr[kind] = dict(bin_px=int(ink.sum()), ben_len_found=None if got is None else round(got, 4), false_px=int((ink & (d > far)).sum()), ben_tracks=sum(t['kind'] == kind for t in B['tracks']))
        r[run] = rr
    out[N] = r; print(N, json.dumps(r))
json.dump(out, open(os.path.join(D, 'rail_score.json'), 'w', encoding='utf8', newline='\n'), indent=1)
