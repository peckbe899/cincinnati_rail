"""Read-only review check: score the rules' rail as the line editor shows it (rail_tracks.py polylines made from the
rules' bins WITHOUT Ben's tracks) against Ben's tracks, and measure target statistics for a rail network.
Run with cwd = data/sanborn. Writes only into the scratch folder given as argv[2]."""
import sys, os, json, numpy as np, cv2
S = sys.argv[2]; sys.path.insert(0, S)
import rt_copy as rt
N = sys.argv[1]
R = cv2.imread(os.path.join(S, f'{N}_rule.png'), 0); H, W = R.shape
BJ = json.load(open(f'picks22_guided/22-{N}/rail_ben.json', encoding='utf8')); T = BJ['tracks']
print('plate', N, 'size', W, H, 'complete', BJ.get('complete'))

def samples(p, step=4):
    p = np.asarray(p, float); S_ = []
    for q0, q1 in zip(p[:-1], p[1:]):
        L = np.hypot(*(q1 - q0)); S_.append(q0[None] + np.linspace(0, 1, max(2, int(L / step) + 1))[:, None] * (q1 - q0)[None])
    return np.vstack(S_)
def plen(p): p = np.asarray(p, float); return float(np.hypot(*np.diff(p, axis=0).T).sum())
def draw(tracks, wd):
    m = np.zeros((H, W), np.uint8)
    for p in tracks: cv2.polylines(m, [np.round(np.asarray(p)).astype(np.int32)], False, 1, wd)
    return m
def dist(m): return cv2.distanceTransform((m == 0).astype(np.uint8), cv2.DIST_L2, 5)

rr = rt.railroad_tracks((R == 4).astype(np.uint8)); car = rt.streetcar_tracks((R == 5).astype(np.uint8))
rule = {'railroad': rr, 'streetcar': car}
TOL = {'railroad': 10, 'streetcar': 30}
for k in ('railroad', 'streetcar'):
    ben = [t['pts'] for t in T if t['kind'] == k and t.get('src') != 'rule']; unk = [t['pts'] for t in T if t['kind'] == k and t.get('src') == 'rule']
    Lb = sum(plen(p) for p in ben); Lr = sum(plen(p) for p in rule[k])
    print(f'\n{k}: Ben (checked) {len(ben)} tracks {Lb:.0f} px; still src:rule in his file {len(unk)} tracks {sum(plen(p) for p in unk):.0f} px; rule polylines (no-ben bins) {len(rule[k])} tracks {Lr:.0f} px')
    if not ben or not rule[k]: continue
    Db = dist(draw(ben, 1)); Dr = dist(draw(rule[k], 1))
    for tol in (5, TOL[k]):
        sb = np.vstack([samples(p) for p in ben]).round().astype(int); sb = sb[(sb[:, 0] >= 0) & (sb[:, 0] < W) & (sb[:, 1] >= 0) & (sb[:, 1] < H)]
        sr = np.vstack([samples(p) for p in rule[k]]).round().astype(int); sr = sr[(sr[:, 0] >= 0) & (sr[:, 0] < W) & (sr[:, 1] >= 0) & (sr[:, 1] < H)]
        rec = (Dr[sb[:, 1], sb[:, 0]] <= tol).mean(); pre = (Db[sr[:, 1], sr[:, 0]] <= tol).mean()
        print(f'  within {tol:2d} px: recall of Ben length {100 * rec:.1f}%   precision of rule-track length {100 * pre:.1f}%' + ('' if BJ.get('complete') else '  (plate not complete: precision is a lower bound)'))
    # fragmentation: how many rule pieces cover each of Ben's tracks
    lab = np.zeros((H, W), np.int32)
    for i, p in enumerate(rule[k]): cv2.polylines(lab, [np.round(np.asarray(p)).astype(np.int32)], False, i + 1, 2 * TOL[k] + 1)
    pieces = []
    for p in ben:
        s = samples(p).round().astype(int); s = s[(s[:, 0] >= 0) & (s[:, 0] < W) & (s[:, 1] >= 0) & (s[:, 1] < H)]
        ids = lab[s[:, 1], s[:, 0]]; pieces.append(len(set(ids[ids > 0].tolist())))
    print(f'  rule pieces touching each Ben track: median {np.median(pieces):.0f}, max {max(pieces)}, total {sum(pieces)} for {len(ben)} tracks')
    lens = np.array([plen(p) for p in rule[k]]); print(f'  rule track lengths: n {len(lens)}, under 300 px {int((lens < 300).sum())}, median {np.median(lens):.0f}')

# target statistics for a rail network: positive share at different widths, ink in the BEN_RAIL band away from the centre
im = cv2.imread(f'cufp/22-{N}.jpg'); ink = cv2.cvtColor(im, cv2.COLOR_BGR2LAB)[..., 0] < 140
al = np.load(f'cufp/{N}/png_alpha_s4.npy'); paper = cv2.resize(al, (W, H), interpolation=cv2.INTER_NEAREST) > 0; ink &= paper
print(f'\npaper px {paper.sum():,}  ink px {ink.sum():,}')
for k in ('railroad', 'streetcar'):
    ben = [t['pts'] for t in T if t['kind'] == k]
    if not ben: continue
    for wd in (3, 5, 7, 21):
        m = draw(ben, wd) > 0; print(f'  {k}: polyline drawn {wd:2d} px wide = {m.sum():,} px = {100 * m.sum() / paper.sum():.3f}% of paper; ink in it {(m & ink).sum():,} ({100 * (m & ink).sum() / max(1, m.sum()):.0f}% of the band is ink)')
    band = draw(ben, 21) > 0; core = draw(ben, 7) > 0
    print(f'  {k}: ink within 10 px of a track (ink_bins BEN_RAIL band) {(band & ink).sum():,} px, of which {((band & ~core) & ink).sum():,} px lies 4-10 px off the centre line (ticks, neighbours)')
# overlap with Ben's street map lines (block lines), where there is one
smf = f'streetmap/22-{N}.json'
if os.path.exists(smf):
    SM = json.load(open(smf, encoding='utf8')); bl = np.zeros((H, W), np.uint8)
    for l in SM['lines']: cv2.line(bl, tuple(np.round(l['a']).astype(int).tolist()), tuple(np.round(l['b']).astype(int).tolist()), 1, 5)
    for k in ('railroad', 'streetcar'):
        ben = [t['pts'] for t in T if t['kind'] == k]; m = draw(ben, 5) > 0
        print(f'  {k} 5 px target overlapping a 5 px block-line target: {(m & (bl > 0)).sum():,} px = {100 * (m & (bl > 0)).sum() / max(1, m.sum()):.1f}% of the rail target; block-line target {int((bl > 0).sum()):,} px')
# how many 448 px crops contain rail (for sampling)
for k in ('railroad', 'streetcar'):
    ben = [t['pts'] for t in T if t['kind'] == k]
    if not ben: continue
    m = draw(ben, 3); cnt = 0; tot = 0
    for y in range(0, H - 448, 448):
        for x in range(0, W - 448, 448):
            if paper[y:y + 448, x:x + 448].mean() < 0.5: continue
            tot += 1; cnt += m[y:y + 448, x:x + 448].sum() >= 60
    print(f'  {k}: of {tot} paper 448 px tiles, {cnt} ({100 * cnt / max(1, tot):.0f}%) hold 60+ px of the 3 px target')
