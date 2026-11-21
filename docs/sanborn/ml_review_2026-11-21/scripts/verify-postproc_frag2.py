"""Split the reviewer's 'broken pairs' (N_edges.json after clean(): <3 deg, offset <12 px, gap <150 px) into pairs whose two
lines come from the SAME block polygon (a notch splitting one side) and pairs from DIFFERENT polygons (e.g. two blocks on
one street line with an alley or street between them). Reads only."""
import json, sys
import numpy as np
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; U = SP + 'unet_data/'
src = open('C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/tools/sanborn/unet/edit_server.py', encoding='utf8').read()
ns = dict(np=np); exec(src[src.index('def clean('):src.index('def plates(')], ns); clean = ns['clean']
COS = np.cos(np.radians(3))
for N in sys.argv[1:]:
    raw = json.load(open(U + f'{N}_edges.json', encoding='utf8')); e = clean(raw)
    pol = json.load(open(SP + f'picks22_guided/22-{N}/outlines.json', encoding='utf8'))
    sides = [(np.array(s['a']), np.array(s['b']), pi) for pi, p in enumerate(pol) for s in p if s['state'] != 'short' and not s.get('paper_edge')]
    A = np.array([l['a'] for l in e], float); B = np.array([l['b'] for l in e], float); D = B - A; Ln = np.hypot(*D.T); Dn = D / Ln[:, None]
    owner = []
    for i in range(len(e)):
        n = np.array([-Dn[i][1], Dn[i][0]]); ps = set()
        for a, b, pi in sides:
            if abs(((b - a) / np.hypot(*(b - a))) @ Dn[i]) < np.cos(np.radians(4)): continue
            if max(abs((a - A[i]) @ n), abs((b - A[i]) @ n)) > 6: continue
            t = sorted(((a - A[i]) @ Dn[i], (b - A[i]) @ Dn[i]))
            if t[1] > 2 and t[0] < Ln[i] - 2: ps.add(pi)
        owner.append(ps)
    same, diff, unk = [], [], []
    for i in range(len(e)):
        for j in range(i + 1, len(e)):
            if abs(Dn[i] @ Dn[j]) < COS: continue
            n = np.array([-Dn[i][1], Dn[i][0]]); o = max(abs((A[j] - A[i]) @ n), abs((B[j] - A[i]) @ n))
            if o > 12: continue
            tj = sorted(((A[j] - A[i]) @ Dn[i], (B[j] - A[i]) @ Dn[i])); gap = max(tj[0] - Ln[i], -tj[1])
            if gap >= 150: continue
            if not owner[i] or not owner[j]: unk.append(gap)
            elif owner[i] & owner[j]: same.append(gap)
            else: diff.append(gap)
    f = lambda g: f'n={len(g):3d} gap median {np.median(g) if g else 0:5.0f} px, >25 px {np.mean(np.array(g) > 25) if g else 0:.2f}, >5 px offset n/a'
    print(f'plate {N}: {len(e)} lines; pairs same polygon {f(same)} | different polygons {f(diff)} | unmatched {len(unk)}')
