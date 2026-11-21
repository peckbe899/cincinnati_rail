"""Plate 44: how many of the sides outlines.py calls 'on print' lie on Ben's street-map lines (streetmap/22-44.json),
and what ink the others lie on (44_bins.png: block line = Ben's lines; the other bins are ink_bins.py's rule-based guess).
Uses the outlines.json that is there (guided networks edge_v1 + lines_v2), since lines_ng1 was never run on 44."""
import json, sys
import numpy as np, cv2
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; U = SP + 'unet_data/'
TOL = float(sys.argv[1]) if len(sys.argv) > 1 else 6.0; ANG = np.cos(np.radians(4))
sm = json.load(open(SP + 'streetmap/22-44.json', encoding='utf8'))
BL = [(np.array(l['a'], float), np.array(l['b'], float), l['kind']) for l in sm['lines']]
BA = np.array([a for a, b, k in BL]); BB = np.array([b for a, b, k in BL]); BD = BB - BA; BLn = np.hypot(*BD.T); BDn = BD / BLn[:, None]
def onben(p, d):
    """points p (k,2) with direction d: within TOL of a Ben line of similar direction"""
    t = np.clip(((p[:, None, :] - BA[None]) * BD[None]).sum(-1) / BLn[None] ** 2, 0, 1)
    q = BA[None] + t[..., None] * BD[None]; dist = np.hypot(*(p[:, None, :] - q).transpose(2, 0, 1))
    ok = (dist < TOL) & (np.abs(BDn @ d) > ANG)[None]
    return ok.any(1)
def pts(a, b, step=4):
    L = np.hypot(*(b - a)); n = max(2, int(L / step)); return a + np.outer(np.linspace(0, 1, n), b - a)
bins = cv2.imread(U + '44_bins.png', 0); names = {int(k): v['name'] for k, v in json.load(open(U + '44_bins.json', encoding='utf8'))['bins'].items()}
print('bins png', bins.shape)
o = json.load(open(SP + 'picks22_guided/22-44/outlines.json', encoding='utf8'))
agg = {}; under = {}
for p in o:
    for s in p:
        a, b = np.array(s['a'], float), np.array(s['b'], float); L = np.hypot(*(b - a))
        if L < 1: continue
        cat = 'short' if s['state'] == 'short' else ('paper_edge' if s.get('paper_edge') else s['state'])
        P = pts(a, b); f = onben(P, (b - a) / L).mean()
        g = agg.setdefault(cat, [0.0, 0.0, 0]); g[0] += L; g[1] += L * f; g[2] += 1
        if cat == 'on print' and f < 0.5:   # a green side mostly off Ben's lines: what ink is under it (nearest ink within 2 px)
            nrm = np.array([-(b - a)[1], (b - a)[0]]) / L; cnt = {}
            for q in P:
                for sft in (0, -1, 1, -2, 2):
                    x, y = (q + nrm * sft).round().astype(int)
                    if 0 <= y < bins.shape[0] and 0 <= x < bins.shape[1] and bins[y, x]:
                        cnt[bins[y, x]] = cnt.get(bins[y, x], 0) + 1; break
            k = max(cnt, key=cnt.get) if cnt else 0
            under.setdefault(names.get(k, 'no ink'), [0, 0.0]); under[names.get(k, 'no ink')][0] += 1; under[names.get(k, 'no ink')][1] += L
print(f'tolerance {TOL} px, 4 deg')
for k, (L, Lon, n) in agg.items(): print(f'  {k:22s} n={n:5d} length {L:8.0f} px, on Ben\'s lines {100 * Lon / L:5.1f}% by length')
print('  green sides mostly off Ben\'s lines, by the ink bin under them:', {k: (v[0], round(v[1])) for k, v in sorted(under.items(), key=lambda x: -x[1][1])})
# recall: Ben's lines covered by sides that blocks_noguide.py would export (not short, not paper edge), and by any side
SA = []; SB = []; SAll_A = []; SAll_B = []
for p in o:
    for s in p:
        a, b = np.array(s['a'], float), np.array(s['b'], float)
        if np.hypot(*(b - a)) < 1: continue
        SAll_A.append(a); SAll_B.append(b)
        if s['state'] != 'short' and not s.get('paper_edge'): SA.append(a); SB.append(b)
def cover(SA, SB, kinds):
    SA = np.array(SA); SB = np.array(SB); SD = SB - SA; SL = np.hypot(*SD.T); SDn = SD / SL[:, None]; tot = 0; got = 0
    for a, b, k in BL:
        if k not in kinds: continue
        L = np.hypot(*(b - a)); d = (b - a) / L; P = pts(a, b)
        t = np.clip(((P[:, None, :] - SA[None]) * SD[None]).sum(-1) / SL[None] ** 2, 0, 1); q = SA[None] + t[..., None] * SD[None]
        dist = np.hypot(*(P[:, None, :] - q).transpose(2, 0, 1)); ok = ((dist < TOL) & (np.abs(SDn @ d) > ANG)[None]).any(1)
        tot += L; got += L * ok.mean()
    return got / tot
for kinds in (('printed',), ('drawn',), ('sheet_edge',), ('printed', 'drawn')):
    print(f"  Ben's {'+'.join(kinds):15s} length covered: by exported sides {100 * cover(SA, SB, kinds):.1f}%, by all sides incl. short/paper edge {100 * cover(SAll_A, SAll_B, kinds):.1f}%")
