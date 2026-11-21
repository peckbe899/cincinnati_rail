import json, sys, numpy as np, cv2
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; U = SP + 'unet_data/'
src = open('C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/tools/sanborn/unet/edit_server.py', encoding='utf8').read()
ns = dict(np=np); exec(src[src.index('def clean('):src.index('def plates(')], ns); clean = ns['clean']
for N in sys.argv[1:]:
    a4 = np.load(SP + f'cufp/{N}/png_alpha_s4.npy').astype(np.uint8)
    d4 = cv2.distanceTransform((a4 > 0).astype(np.uint8), cv2.DIST_L2, 3) * 4   # px (full size) to the paper's edge, from quarter size
    e = clean(json.load(open(U + f'{N}_edges.json', encoding='utf8')))
    near = []; 
    for l in e:
        a, b = np.array(l['a']), np.array(l['b']); P = a + np.outer(np.linspace(0, 1, 20), b - a)
        dd = d4[np.clip((P[:, 1] / 4).astype(int), 0, a4.shape[0] - 1), np.clip((P[:, 0] / 4).astype(int), 0, a4.shape[1] - 1)]
        if np.median(dd) < 60: near.append((np.hypot(*(b - a)), np.median(dd), l['state']))
    # overlapping near-duplicates after clean: parallel < 3 deg, offset <= 12 px, overlapping > 30 px
    A = np.array([l['a'] for l in e], float); B = np.array([l['b'] for l in e], float); L = np.hypot(*(B - A).T); D = (B - A) / L[:, None]; dup = []
    for i in range(len(e)):
        for j in range(i + 1, len(e)):
            if abs(D[i] @ D[j]) < np.cos(np.radians(3)): continue
            n = np.array([-D[i][1], D[i][0]]); o = max(abs((A[j] - A[i]) @ n), abs((B[j] - A[i]) @ n))
            if o > 12: continue
            tj = sorted(((A[j] - A[i]) @ D[i], (B[j] - A[i]) @ D[i])); ov = min(L[i], tj[1]) - max(0, tj[0])
            if ov > 30: dup.append((round(o, 1), round(ov), e[i]['state'], e[j]['state']))
    # block polygon areas (outlines.json, all sides chained)
    o_ = json.load(open(SP + f'picks22_guided/22-{N}/outlines.json', encoding='utf8')); ar = []
    for p in o_:
        pts = np.array([s['a'] for s in p], np.float32)
        if len(pts) >= 3: ar.append(abs(cv2.contourArea(pts)))
    ar = np.array(ar)
    print(f'plate {N}: {len(e)} lines; {len(near)} lines within 60 px of the paper edge (15-60 px band; sheet() adds its own line there) length {sum(x[0] for x in near):.0f} px; '
          f'{len(dup)} overlapping parallel pairs <=12 px apart left by clean() {dup[:6]}; blocks {len(ar)}, area px median {np.median(ar):.0f}, < 40000 px: {(ar < 40000).sum()}')
