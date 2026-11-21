"""Verifier stats (read-only on repo, cwd = data/sanborn): 86 KEY box, source.json, run_plates.json counts,
rail target statistics on 44, piece sizes of mixed bins on 1A."""
import json, os, glob, numpy as np, cv2
from scipy.spatial import cKDTree
def plen(p): p = np.asarray(p, float); return float(np.hypot(*np.diff(p, axis=0).T).sum())
def samp(p, step=2):
    p = np.asarray(p, float); S = []
    for q0, q1 in zip(p[:-1], p[1:]):
        L = np.hypot(*(q1 - q0)); S.append(q0[None] + np.linspace(0, 1, max(2, int(L / step) + 1))[:, None] * (q1 - q0)[None])
    return np.vstack(S)
# --- 86 KEY box
B = cv2.imread('unet_data/86_bins.png', 0); x0, y0, x1, y1 = 9650, 1100, 10550, 1500
print('86 bins', B.shape, 'KEY box railroad px', int((B[y0:y1, x0:x1] == 4).sum()), 'streetcar px', int((B[y0:y1, x0:x1] == 5).sum()))
rr = json.load(open('unet_data/86_rail_rule.json', encoding='utf8'))['tracks']
inside = [t for t in rr if all(x0 <= p[0] <= x1 and y0 <= p[1] <= y1 for p in t['pts'])]
print('  86 rail_rule tracks entirely inside KEY box:', [(t['kind'], round(plen(t['pts']))) for t in inside])
for n in ('19', '86', '44'):
    f = f'cufp/{n}/source.json'; print(n, json.load(open(f)) if os.path.exists(f) else 'no source.json', cv2.imread(f'cufp/22-{n}.jpg', cv2.IMREAD_REDUCED_COLOR_8).shape)
# --- run_plates.json
st = json.load(open('unet_data/run_plates.json', encoding='utf8'))
done = {k: v for k, v in st.items() if v.get('state') == 'done'}
rrp = np.array([v.get('railroad_px', 0) for v in done.values()])
print('run_plates.json entries', len(st), 'done', len(done), '>50k railroad', int((rrp > 50000).sum()), 'zero railroad', int((rrp == 0).sum()))
print('  3:', st.get('3', {}).get('railroad_px'), '1B:', st.get('1B', {}).get('railroad_px'), '44:', st.get('44'), '1A:', {k: st.get('1A', {}).get(k) for k in ('railroad_px', 'streetcar_px', 'ben_rail')})
print('  rail_ben files:', glob.glob('picks22_guided/*/rail_ben*.json'))
# --- target stats on 44
N = '44'; BJ = json.load(open(f'picks22_guided/22-{N}/rail_ben.json', encoding='utf8')); T = BJ['tracks']
im = cv2.imread(f'cufp/22-{N}.jpg'); H, W = im.shape[:2]; ink = cv2.cvtColor(im, cv2.COLOR_BGR2LAB)[..., 0] < 140
al = np.load(f'cufp/{N}/png_alpha_s4.npy'); paper = cv2.resize(al, (W, H), interpolation=cv2.INTER_NEAREST) > 0; ink &= paper
Dink = cv2.distanceTransform((~ink).astype(np.uint8), cv2.DIST_L2, 5)
def draw(tr, wd):
    m = np.zeros((H, W), np.uint8)
    for p in tr: cv2.polylines(m, [np.round(np.asarray(p)).astype(np.int32)], False, 1, wd)
    return m > 0
for k in ('railroad', 'streetcar'):
    tr = [t['pts'] for t in T if t['kind'] == k]; s = np.vstack([samp(p) for p in tr]).round().astype(int)
    off = Dink[s[:, 1], s[:, 0]]
    print(f'{k}: off-ink median {np.median(off):.1f}, p90 {np.percentile(off, 90):.1f}, share >3 px {100 * (off > 3).mean():.1f}%')
    for wd in (5, 13):
        m = draw(tr, wd); print(f'   {wd} px target: {m.sum():,} px = {100 * m.sum() / paper.sum():.3f}% of paper')
    band = draw(tr, 21) & ink; core = draw(tr, 7) & ink; print(f'   ink within 10 px {band.sum():,}, 4-10 px off {(band & ~core).sum():,}')
    # neighbours: for samples of each track, distance to other tracks of any kind
    nn = []
    for i, p in enumerate(tr):
        others = [q for j, q in enumerate([t['pts'] for t in T]) if not (T[j]['kind'] == k and [t['pts'] for t in T if t['kind'] == k].index(p) == i and q is p)]
        oth = [q for q in [t['pts'] for t in T] if q is not p]
        if not oth: continue
        tree = cKDTree(np.vstack([samp(q, 1) for q in oth])); sp = samp(p, 4); d, _ = tree.query(sp)
        # exclude points near the track's own ends where it meets another track (switch): within 30 px of an end
        e = np.minimum(np.hypot(*(sp - np.asarray(p[0])).T), np.hypot(*(sp - np.asarray(p[-1])).T)); nn.append(d[e > 30])
    nn = np.concatenate(nn); print(f'   share of length with another track within 21 px (ends excluded): {100 * (nn <= 21).mean():.1f}%, p5 {np.percentile(nn, 5):.1f}')
# 448 tiles
for k in ('railroad', 'streetcar'):
    m = draw([t['pts'] for t in T if t['kind'] == k], 3); cnt = tot = 0
    for y in range(0, H - 448, 448):
        for x in range(0, W - 448, 448):
            if paper[y:y + 448, x:x + 448].mean() < 0.5: continue
            tot += 1; cnt += m[y:y + 448, x:x + 448].sum() >= 60
    print(f'{k}: {cnt}/{tot} tiles = {100 * cnt / tot:.0f}%')
SM = json.load(open('streetmap/22-44.json', encoding='utf8')); bl = np.zeros((H, W), np.uint8)
for l in SM['lines']: cv2.line(bl, tuple(np.round(l['a']).astype(int).tolist()), tuple(np.round(l['b']).astype(int).tolist()), 1, 5)
m = draw([t['pts'] for t in T], 5); print('rail 5px target overlapping 5px block line:', f'{100 * (m & (bl > 0)).sum() / m.sum():.2f}%')
# --- 1A mixed-bin streetcar pieces
B = cv2.imread('unet_data/1A_bins.png', 0); mm = cv2.morphologyEx((B == 5).astype(np.uint8), cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
n, lb, stt, _ = cv2.connectedComponentsWithStats(mm, connectivity=8); a = np.sort(stt[1:, 4])[::-1]
print('1A mixed streetcar bin pieces (>=150 px):', int((a >= 150).sum()), 'largest', a[:12].tolist())
