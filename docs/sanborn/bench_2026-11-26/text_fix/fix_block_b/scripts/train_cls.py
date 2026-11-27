"""Fit blockfix's figure classifier (numpy MLP: 940 inputs -> 128 relu -> 11 classes '0'..'9', 'none') on one fold.
    python -B .../scripts/train_cls.py FOLD OUT.npz      (FOLD: A, B or all; proposals from models/props/N_tmpl_real_<A|B|all>.npz)

Positives: the real figures cut from the fold's plates (extract_digits.py) and the ones placed by fitting the known
reading (fit_digits.py: crossed or joined figures); never inside a dev truth window or an H window. Each as its own box
and as the proposal placed on it, shifted (+-3 px), scaled (0.88-1.12) and crossed by a drawn thin line (2-4 px). Synthetic figures from two Windows fonts (Franklin Gothic Demi, Arial Bold) rendered
at the measured stroke are added at low weight. Negatives ('none'): proposals far from every surveyed block number and
every dev target (more than 110 px across or 90 px down), never inside a dev truth window or an H window; and proposals
inside a surveyed number that sit on no figure of it (half off a figure, or at the wrong height). Reads no truth mask."""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'code'))
import numpy as np, cv2
import bfcommon as C, blockfix as B

fold, outp = sys.argv[1], sys.argv[2]
plates = C.FOLD['A'] + C.FOLD['B'] if fold == 'all' else C.FOLD[fold]
tn = {'A': 'real_A', 'B': 'real_B', 'all': 'real_all'}[fold]
rng = np.random.default_rng(7)
R = [q for q in np.load(os.path.join(B.MOD, 'real_digits.npy'), allow_pickle=True) if q['plate'] in plates]
for q in R: q['cx'], q['cy'] = q['x'] + q['w'] / 2, q['y'] + q['h'] / 2
FITS = {'A': ['fit_A.npy'], 'B': ['fit_B.npy'], 'all': ['fit_A.npy', 'fit_B.npy']}[fold]
RF = [q for f in FITS for q in np.load(os.path.join(B.MOD, f), allow_pickle=True) if q['plate'] in plates]
for q in RF: q['w'] = 0.75 * q['h']
SJ = (0.88, 1.12); PJ = 3; NEG = 8000
crops = C.dev_crops(); E5 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)); CL = list('0123456789') + ['none']


def feat_local(I, cx, cy, h, line=None):
    """features as blockfix.features, but from a local crop so a line can be drawn in first"""
    m = int(1.6 * h) + 6; H, W = I.shape; x0, y0 = int(cx) - m, int(cy) - m
    if x0 < 0 or y0 < 0 or x0 + 2 * m > W or y0 + 2 * m > H: return None
    loc = I[y0:y0 + 2 * m, x0:x0 + 2 * m].copy()
    if line is not None:
        ang, off, wd = line; c = np.array([cx - x0, cy - y0]); u = np.array([np.cos(ang), np.sin(ang)]); n = np.array([-u[1], u[0]])
        p0 = c + n * off - u * 3 * m; p1 = c + n * off + u * 3 * m
        cv2.line(loc, tuple(np.round(p0).astype(int).tolist()), tuple(np.round(p1).astype(int).tolist()), 1, wd)
    K = B.thick(loc, 5)
    return B.features(K, loc, [cx - x0], [cy - y0], [h])[0]


X, Y, Wt = [], [], []
def add(f, y, w=1.0):
    if f is not None: X.append(f); Y.append(CL.index(y)); Wt.append(w)


for N in plates:
    codes = cv2.imread(C.f3_path(N), 0); I = (codes > 0).astype(np.uint8); K = B.thick(I, 5)
    z = dict(np.load(os.path.join(B.MOD, 'props', f'{N}_{tn}.npz')))
    bl = B.blobs(K, B.P)   # blob proposals too, as blockfix makes them
    for k_, v_ in (('cx', [q['cx'] for q in bl]), ('cy', [q['cy'] for q in bl]), ('h', [q['h'] for q in bl]), ('s', [0.6] * len(bl)), ('d', ['blob'] * len(bl))):
        z[k_] = np.r_[z[k_], np.array(v_, dtype=z[k_].dtype if k_ != 'd' else object)]
    cands = [(x, y) for x, y, r, _ in C.candidates(N)]
    for tid, c in crops.items():
        if c['plate'] != N: continue
        W_ = json.load(open(os.path.join(C.DEVB, 'truth', f'{tid}_words.json'), encoding='utf8'))['words']
        b = [q for q in W_ if q.get('target')][0]['aabb']; cands.append(((b[0] + b[2]) / 2, (b[1] + b[3]) / 2))
    wins = [c['win'] for c in crops.values() if c['plate'] == N]
    inw = lambda x, y: any(w[0] - 40 <= x <= w[2] + 40 and w[1] - 40 <= y <= w[3] + 40 for w in wins) or C.in_hwin(N, (x - 40, y - 40, x + 40, y + 40))
    RN = [q for q in R if q['plate'] == N]
    used = np.zeros(len(z['cx']), bool); npos = 0
    for q in RN + [q for q in RF if q['plate'] == N]:
        cx, cy, h = q['cx'], q['cy'], q['h']
        m = (np.abs(z['cx'] - cx) <= 0.25 * q['w'] + 4) & (np.abs(z['cy'] - cy) <= 0.15 * h) & (np.abs(z['h'] - h) <= 0.2 * h)
        views = [(cx, cy, h)] + [(z['cx'][i], z['cy'][i], z['h'][i]) for i in np.nonzero(m)[0][:2]]
        used |= m
        for vx, vy, vh in views:
            add(B.features(K, I, [vx], [vy], [vh])[0], q['digit'])
            for _ in range(4):
                add(feat_local(I, vx + rng.uniform(-PJ, PJ), vy + rng.uniform(-PJ, PJ), vh * rng.uniform(*SJ)), q['digit'])
            for _ in range(4):
                add(feat_local(I, vx + rng.uniform(-PJ, PJ), vy + rng.uniform(-PJ, PJ), vh * rng.uniform(*SJ),
                               (rng.uniform(0, np.pi), rng.uniform(-0.5, 0.5) * vh, int(rng.integers(2, 5)))), q['digit'])
        npos += 1
    # partial negatives: proposals inside a cut-out number's area that sit on none of its figures
    nparts = 0
    for q in RN:
        sib = [s for s in RN if s['reading'] == q['reading'] and abs(s['y'] - q['y']) < 40 and abs(s['x'] - q['x']) < 200]
        x0 = min(s['x'] for s in sib) - 10; x1 = max(s['x'] + s['w'] for s in sib) + 10; y0 = min(s['y'] for s in sib) - 10; y1 = max(s['y'] + s['h'] for s in sib) + 10
        inn = (z['cx'] >= x0) & (z['cx'] <= x1) & (z['cy'] >= y0) & (z['cy'] <= y1) & ~used
        for i in np.nonzero(inn)[0]:
            ok = True
            for s in sib:
                if abs(z['cx'][i] - (s['x'] + s['w'] / 2)) <= 0.4 * max(s['w'], 0.5 * s['h']) and abs(z['h'][i] - s['h']) <= 0.25 * s['h'] and abs(z['cy'][i] - (s['y'] + s['h'] / 2)) <= 0.2 * s['h']: ok = False
            if ok: add(B.features(K, I, [z['cx'][i]], [z['cy'][i]], [z['h'][i]])[0], 'none', 1.0); used[i] = True; nparts += 1
    # far negatives
    far = np.ones(len(z['cx']), bool)
    for x, y in cands: far &= ~((np.abs(z['cx'] - x) <= 110) & (np.abs(z['cy'] - y) <= 90))
    far &= np.array([not inw(x, y) for x, y in zip(z['cx'], z['cy'])])
    idx = np.nonzero(far)[0]
    if len(idx) > NEG:   # keep the hard ones (high s) and a random rest
        o = idx[np.argsort(-z['s'][idx])]; idx = np.r_[o[:NEG // 2], rng.choice(o[NEG // 2:], NEG - NEG // 2, replace=False)]
    F = B.features(K, I, z['cx'][idx], z['cy'][idx], z['h'][idx])
    for f in F: add(f, 'none')
    print(N, 'figures', npos, 'partial negatives', nparts, 'far negatives', len(idx), flush=True)

# synthetic figures from fonts, at low weight
from PIL import Image, ImageDraw, ImageFont
nsyn = 0
for fn in ('FRADM.TTF', 'arialbd.ttf'):
    f = ImageFont.truetype(os.path.join('C:/Windows/Fonts', fn), 60)
    for d in '0123456789':
        for _ in range(12):
            h = int(rng.integers(46, 64)); im = Image.new('L', (200, 160), 0); ImageDraw.Draw(im).text((60, 30), d, fill=255, font=f)
            a = (np.array(im) > 127).astype(np.uint8); ys, xs = np.nonzero(a); g = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
            s = h / g.shape[0]; g = cv2.resize(g, (max(1, int(g.shape[1] * s * rng.uniform(0.85, 1.0))), h), interpolation=cv2.INTER_NEAREST)
            k = int(rng.integers(-1, 2))
            if k > 0: g = cv2.dilate(g, np.ones((3, 3), np.uint8))
            if k < 0: g = cv2.erode(g, np.ones((3, 3), np.uint8))
            canvas = np.zeros((260, 260), np.uint8); y0 = 130 - h // 2; x0 = 130 - g.shape[1] // 2; canvas[y0:y0 + h, x0:x0 + g.shape[1]] = g
            line = (rng.uniform(0, np.pi), rng.uniform(-0.5, 0.5) * h, int(rng.integers(2, 5))) if rng.random() < 0.5 else None
            add(feat_local(canvas, 130 + rng.uniform(-2, 2), 130 + rng.uniform(-2, 2), h, line), d, 0.3); nsyn += 1
X = np.array(X, np.float32); Y = np.array(Y); Wt = np.array(Wt, np.float32)
print('samples', len(Y), 'by class', np.bincount(Y, minlength=11).tolist(), 'synthetic', nsyn, flush=True)

# class weights: the 10 figures together weigh as much as 'none'
cw = np.ones(11, np.float32); nd = (Y < 10).sum(); nn = (Y == 10).sum()
for c in range(10): cw[c] = nn / max(1, nd)
Wt = Wt * cw[Y]
mu = X.mean(0); sd = X.std(0) + 0.05
Z = (X - mu) / sd
perm = rng.permutation(len(Y)); nv = len(Y) // 8; va, tr = perm[:nv], perm[nv:]
Dh = 128; W1 = rng.normal(0, np.sqrt(2 / Z.shape[1]), (Z.shape[1], Dh)).astype(np.float32); b1 = np.zeros(Dh, np.float32)
W2 = rng.normal(0, np.sqrt(2 / Dh), (Dh, 11)).astype(np.float32); b2 = np.zeros(11, np.float32)
params = [W1, b1, W2, b2]; m_ = [np.zeros_like(q) for q in params]; v_ = [np.zeros_like(q) for q in params]
lr, l2, bs, t = 1e-3, 1e-4, 256, 0


def fwd(Zb):
    Hh = np.maximum(0, Zb @ W1 + b1); O = Hh @ W2 + b2; O = O - O.max(1, keepdims=True); E = np.exp(O); return Hh, E / E.sum(1, keepdims=True)


best = (1e9, None)
for ep in range(60):
    rng.shuffle(tr)
    for s in range(0, len(tr), bs):
        ib = tr[s:s + bs]; Zb = Z[ib]; Hh, Pp = fwd(Zb); w = Wt[ib][:, None]
        G = Pp.copy(); G[np.arange(len(ib)), Y[ib]] -= 1; G *= w / w.sum()
        gW2 = Hh.T @ G + l2 * W2; gb2 = G.sum(0); GH = (G @ W2.T) * (Hh > 0); gW1 = Zb.T @ GH + l2 * W1; gb1 = GH.sum(0)
        t += 1
        for q, g, m1, v1 in zip(params, (gW1, gb1, gW2, gb2), m_, v_):
            m1 *= 0.9; m1 += 0.1 * g; v1 *= 0.999; v1 += 0.001 * g * g
            q -= lr * (m1 / (1 - 0.9 ** t)) / (np.sqrt(v1 / (1 - 0.999 ** t)) + 1e-8)
    _, Pv = fwd(Z[va]); lv = float(-(Wt[va] * np.log(Pv[np.arange(len(va)), Y[va]] + 1e-9)).sum() / Wt[va].sum())
    acc = float((Pv.argmax(1) == Y[va]).mean()); accd = float((Pv.argmax(1)[Y[va] < 10] == Y[va][Y[va] < 10]).mean())
    if lv < best[0]: best = (lv, [q.copy() for q in params], ep, acc, accd)
    if ep % 10 == 9: print(f'epoch {ep + 1}: val loss {lv:.4f} acc {acc:.4f} figures read right {accd:.4f}', flush=True)
lv, (W1, b1, W2, b2), ep, acc, accd = best
print(f'kept epoch {ep + 1}: val loss {lv:.4f}, acc {acc:.4f}, figures read right {accd:.4f}')
np.savez(outp, W1=W1, b1=b1, W2=W2, b2=b2, mu=mu, sd=sd, classes=np.array(CL), fold=fold, plates=np.array(plates),
         n=np.bincount(Y, minlength=11), val=np.array([lv, acc, accd]))
