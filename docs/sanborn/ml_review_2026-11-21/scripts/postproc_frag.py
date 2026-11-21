"""How broken are the lines Ben is shown? For N_edges.json after edit_server.clean(): pairs of lines that are nearly
collinear (< 3 deg, perpendicular offset < OFF px) with a gap < 150 px between their ends (one straight side shown as
several pieces). Also the offsets between consecutive collinear kept sides in outlines.json (why clean() does not join them)."""
import json, sys, os
import numpy as np
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; U = SP + 'unet_data/'
src = open('C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/tools/sanborn/unet/edit_server.py', encoding='utf8').read()
ns = dict(np=np); exec(src[src.index('def clean('):src.index('def plates(')], ns); clean = ns['clean']
COS = np.cos(np.radians(3))
for N in sys.argv[1:]:
    e = clean(json.load(open(U + f'{N}_edges.json', encoding='utf8')))
    A = np.array([l['a'] for l in e], float); B = np.array([l['b'] for l in e], float); D = B - A; Ln = np.hypot(*D.T); Dn = D / Ln[:, None]
    pairs = []; offs = []
    for i in range(len(e)):
        for j in range(i + 1, len(e)):
            if abs(Dn[i] @ Dn[j]) < COS: continue
            n = np.array([-Dn[i][1], Dn[i][0]]); o = max(abs((A[j] - A[i]) @ n), abs((B[j] - A[i]) @ n))
            if o > 12: continue
            ti = sorted((0, Ln[i])); tj = sorted(((A[j] - A[i]) @ Dn[i], (B[j] - A[i]) @ Dn[i]))
            gap = max(tj[0] - ti[1], ti[0] - tj[1])
            if gap < 150: pairs.append((i, j, o, gap)); offs.append(o)
    offs = np.array(offs) if offs else np.zeros(1)
    gaps = np.array([p[3] for p in pairs]) if pairs else np.zeros(1)
    overl = sum(1 for p in pairs if p[3] < 0)
    print(f'plate {N}: {len(e)} lines after clean(), median length {np.median(Ln):.0f} px; {len(pairs)} near-collinear neighbour pairs within 12 px offset and 150 px gap '
          f'(offset median {np.median(offs):.1f} px, {np.mean(offs > 5):.2f} over clean()\'s 5 px; gap median {np.median(gaps):.0f} px, {overl} overlapping, {np.mean((gaps > 25)):.2f} over clean()\'s 25 px gap)')
    st = {}
    for l in e: st[l['state']] = st.get(l['state'], 0) + 1
    print('   states after clean:', st, ' lines < 60 px:', int((Ln < 60).sum()), ' < 130 px:', int((Ln < 130).sum()))
