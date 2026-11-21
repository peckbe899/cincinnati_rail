"""Verifier: score_rail.py's bin recall (rule ink of that kind within TOL px of a track's sample points), split by
track src, and rail_tracks polylines from rules-only bins vs Ben's tracks. Read-only on repo; cwd = data/sanborn.
argv: N RULE_PNG"""
import sys, os, json, numpy as np, cv2
sys.path.insert(0, os.path.abspath('../../tools/sanborn/unet'))
import rail_tracks as rt
N, rp = sys.argv[1:3]
R = cv2.imread(rp, 0); H, W = R.shape
BJ = json.load(open(f'picks22_guided/22-{N}/rail_ben.json', encoding='utf8')); T = BJ['tracks']
dist = lambda m: cv2.distanceTransform((~m).astype(np.uint8), cv2.DIST_L2, 5)
D = {'railroad': dist(R == 4), 'streetcar': dist(R == 5)}; TOL = {'railroad': 10, 'streetcar': 30}
def samp(p, step=4):
    p = np.asarray(p, float); S = []
    for q0, q1 in zip(p[:-1], p[1:]):
        L = np.hypot(*(q1 - q0)); S.append(q0[None] + np.linspace(0, 1, max(2, int(L / step) + 1))[:, None] * (q1 - q0)[None])
    return np.vstack(S)
def plen(p): p = np.asarray(p, float); return float(np.hypot(*np.diff(p, axis=0).T).sum())
print('plate', N, W, H, 'complete', BJ.get('complete'), 'bins px rr', int((R == 4).sum()), 'car', int((R == 5).sum()))
for k in ('railroad', 'streetcar'):
    for lab, sel in (('all', lambda t: True), ('checked', lambda t: t.get('src') != 'rule'), ('src:rule', lambda t: t.get('src') == 'rule')):
        tr = [t for t in T if t['kind'] == k and sel(t)]
        if not tr: continue
        Lt = 0; F = 0
        for t in tr:
            p = np.array(t['pts'], float); q = samp(p).round().astype(int); ok = (q[:, 0] >= 0) & (q[:, 0] < W) & (q[:, 1] >= 0) & (q[:, 1] < H); q = q[ok]
            L = plen(p); f = (D[k][q[:, 1], q[:, 0]] <= TOL[k]).mean(); Lt += L; F += L * f
        print(f'  {k} {lab:8s}: {len(tr)} tracks {Lt:.0f} px, bin recall within {TOL[k]} px = {100 * F / Lt:.1f}%')
    # rules' far ink as score_rail does (band 51 px around ALL tracks of that kind)
    band = np.zeros((H, W), np.uint8)
    for t in T:
        if t['kind'] == k: cv2.polylines(band, [np.round(np.array(t['pts'])).astype(np.int32)], False, 1, 51)
    far = (R == (4 if k == 'railroad' else 5)) & (band == 0); print(f'  {k}: rule ink far from all tracks {int(far.sum())} px')
# rule polylines from rules-only bins
rr = rt.railroad_tracks((R == 4).astype(np.uint8)); car = rt.streetcar_tracks((R == 5).astype(np.uint8))
rule = {'railroad': rr, 'streetcar': car}
def draw(tracks):
    m = np.zeros((H, W), np.uint8)
    for p in tracks: cv2.polylines(m, [np.round(np.asarray(p)).astype(np.int32)], False, 1, 1)
    return m
for k in ('railroad', 'streetcar'):
    ben = [t['pts'] for t in T if t['kind'] == k and t.get('src') != 'rule']
    lens = sorted(round(plen(p)) for p in rule[k]); print(f'\n{k}: rule polylines {len(rule[k])}, lengths {lens}')
    if not ben or not rule[k]: continue
    Db = dist(draw(ben) > 0); Dr = dist(draw(rule[k]) > 0)
    for tol in (5, 10, 30):
        sb = np.vstack([samp(p) for p in ben]).round().astype(int); sb = sb[(sb[:, 0] >= 0) & (sb[:, 0] < W) & (sb[:, 1] >= 0) & (sb[:, 1] < H)]
        sr = np.vstack([samp(p) for p in rule[k]]).round().astype(int); sr = sr[(sr[:, 0] >= 0) & (sr[:, 0] < W) & (sr[:, 1] >= 0) & (sr[:, 1] < H)]
        print(f'  within {tol} px: recall {100 * (Dr[sb[:, 1], sb[:, 0]] <= tol).mean():.1f}%  precision {100 * (Db[sr[:, 1], sr[:, 0]] <= tol).mean():.1f}%')
# rail_rule.json in unet_data vs Ben (mixed-bin output)
rrj = json.load(open(f'unet_data/{N}_rail_rule.json', encoding='utf8'))['tracks']
for k in ('railroad', 'streetcar'):
    ben = [t['pts'] for t in T if t['kind'] == k and t.get('src') != 'rule']; rk = [t['pts'] for t in rrj if t['kind'] == k]
    if not ben or not rk: print(f'unet_data rail_rule {k}: {len(rk)} tracks'); continue
    Dr = dist(draw(rk) > 0); sb = np.vstack([samp(p) for p in ben]).round().astype(int); sb = sb[(sb[:, 0] >= 0) & (sb[:, 0] < W) & (sb[:, 1] >= 0) & (sb[:, 1] < H)]
    print(f'unet_data rail_rule {k}: {len(rk)} tracks, recall within 5 px {100 * (Dr[sb[:, 1], sb[:, 0]] <= 5).mean():.1f}%, within 30 px {100 * (Dr[sb[:, 1], sb[:, 0]] <= 30).mean():.1f}%')
