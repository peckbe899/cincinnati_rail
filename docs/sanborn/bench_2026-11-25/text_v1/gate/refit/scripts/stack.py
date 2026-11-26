"""Stage 2 of the second opinion: a small logistic COMBINER that puts the shape classifier's answer together with what
finder v2 already knows about the piece and its surroundings (classifier step, 26 Nov 2026).

    cd data/sanborn
    python -B bench_2026-11-25/text_v1/classifier/scripts/stack.py [SHAPE_MODEL.npz] [--out combiner.npz]

Why: the shape classifier alone cannot tell an italic figure 1 from a stub of line, or a piece of a letter cut by a line
from a bit of lot line (tune.py: with shape alone the best second opinion moves F1 on T1-T7 by +0.0008 at most). Context
decides those, and finder2's own rules carry most of it.

Features of a piece (all from the scan and finder2, no truth): the shape classifier's logit P(junk) and its summed
probabilities for figures, capitals, small letters, marks, letter pieces ('frag'), touching runs ('pair', 'run'), its top
probability; finder2's call (text or other ink) and kind (glyph or cluster, stroke, dot, eq, jog, blob, other), whether
it is a dash of a dashed line or a rail-tick end, whether and how much it touches line ink, its size, stroke width,
holes, share inside a big letter; and context from finder2's code image: text pixels within 8, 20 and 40 px of its box,
line ink within 8 px and other ink within 20 px; plus three products (finder2's call x logit, stroke x logit, stroke x
text within 20 px). Standardised. The combiner is a one-hidden-layer net (16 ReLU units, L2 3e-3, full-batch Adam,
600 steps), averaged over 5 seeds (fit_mlp); --logistic fits an L2 logistic regression instead (leave-one-crop-out
weighted AUC 0.9614 against the net's 0.9719, 26 Nov).

Labels: the pieces inside the truth crops T1-T7 (truth v2), text when truth-text pixels outnumber truth non-text pixels,
weighted by their scored pixels (capped at 400). LEAVE ONE CROP OUT: each crop's pieces are predicted by a combiner
fitted on the other five crops only; <out>_loco.npz holds those predictions for tune_stack.py (<out>_X.npz the features).
The combiner finder3 uses (--out, default out/combiner.npz; finder3's is out/combiner_cnn2.npz) is fitted on all six
crops; it has never seen a held-out crop."""
import json, os, sys
sys.dont_write_bytecode = True
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
CODE = os.path.normpath(os.path.join(HERE, '..', '..', 'code')); sys.path.insert(0, CODE)
import finder3  # noqa
from model_np import load_model  # noqa
CROPS = ('T1', 'T2', 'T3', 'T4', 'T6', 'T7')   # the truth crops; only main() and dev_pieces() (fitting) read truth
OUT = os.path.join(HERE, '..', 'out')
KINDS = ('glyph', 'stroke', 'dot', 'eq', 'jog', 'blob')
NAMES = ['lpj', 'p_dig', 'p_cap', 'p_low', 'p_mark', 'p_frag', 'p_run', 'p_max', 'f2_text', 'f2_other'] + [f'k_{k}' for k in KINDS] + \
        ['k_rest', 'dash', 'touch', 'log_touch', 'log_ext', 'log_area', 'sw', 'holes', 'in_letter', 'tx8', 'tx20', 'tx40', 'ln8', 'ot20',
         'text_x_lpj', 'stroke_x_lpj', 'stroke_x_tx20']


def box_sum(ii, bb, r):
    H, W = ii.shape[0] - 1, ii.shape[1] - 1
    x0 = np.clip(bb[:, 0] - r, 0, W); y0 = np.clip(bb[:, 1] - r, 0, H); x1 = np.clip(bb[:, 0] + bb[:, 2] + r, 0, W); y1 = np.clip(bb[:, 1] + bb[:, 3] + r, 0, H)
    return ii[y1, x1] - ii[y0, x1] - ii[y1, x0] + ii[y0, x0]


def features(S, pr, sel, classes):
    """stage-2 features for the pieces sel (indices into S's pieces) given the shape classifier's probabilities pr"""
    c = np.array(classes); J = classes.index('junk')
    grp = lambda f: pr[:, np.array([f(x) for x in c])].sum(1)
    pj = np.clip(pr[:, J], 1e-4, 1 - 1e-4); lpj = np.log(pj / (1 - pj))
    pdig = grp(lambda x: x.isdigit()); pcap = grp(lambda x: len(x) == 1 and x.isalpha() and x.isupper()); plow = grp(lambda x: len(x) == 1 and x.isalpha() and x.islower())
    pmark = grp(lambda x: x in ('\'', '"', '.', '-', '&', ',')); pfrag = grp(lambda x: x == 'frag'); prun = grp(lambda x: x in ('pair', 'run'))
    cc = S['codes'][sel]; tot = np.maximum(cc.sum(1), 1); f2t = ((cc[:, 2] + cc[:, 3]) >= 0.5 * tot).astype(float); f2o = (cc[:, 5] >= 0.5 * tot).astype(float)
    k = S['kind'][sel]; kk = [np.isin(k, ('glyph', 'cluster')).astype(float)] + [(k == q).astype(float) for q in KINDS[1:]]
    rest = 1 - np.clip(sum(kk), 0, 1)
    bb = S['bbox'][sel]; pre = S['pre']
    it = cv2.integral(np.isin(pre, (2, 3)).astype(np.uint8)); il = cv2.integral((pre == 1).astype(np.uint8)); io = cv2.integral((pre == 5).astype(np.uint8))
    own_t = cc[:, 2] + cc[:, 3]; own_o = cc[:, 5]
    tx = [np.log1p(np.maximum(box_sum(it, bb, r) - own_t, 0)) for r in (8, 20, 40)]
    ln8 = np.log1p(box_sum(il, bb, 8)); ot20 = np.log1p(np.maximum(box_sum(io, bb, 20) - own_o, 0))
    e = np.maximum(bb[:, 2], bb[:, 3]).astype(float)
    X = np.c_[lpj, pdig, pcap, plow, pmark, pfrag, prun, pr.max(1), f2t, f2o, np.array(kk).T, rest, S['isdash'][sel].astype(float), (S['f_touch'][sel] > 0).astype(float),
              np.log1p(S['f_touch'][sel]), np.log(e), np.log(S['f_A'][sel] + 1), S['f_sw'][sel], (S['f_holes'][sel] > 0).astype(float), S['inletter'][sel],
              tx[0], tx[1], tx[2], ln8, ot20, f2t * lpj, (k == 'stroke') * lpj, (k == 'stroke') * tx[1]]
    return X.astype(np.float64)


def fit(X, y, w, lam=1e-3, it=30):
    mu = X.mean(0); sd = X.std(0) + 1e-6; Z = np.c_[(X - mu) / sd, np.ones(len(X))]; b = np.zeros(Z.shape[1]); w = w / w.mean()
    for _ in range(it):
        p = 1 / (1 + np.exp(-Z @ b)); g = Z.T @ (w * (p - y)) / len(y) + lam * np.r_[b[:-1], 0]
        Hs = (Z * (w * p * (1 - p))[:, None]).T @ Z / len(y) + lam * np.diag(np.r_[np.ones(len(b) - 1), 0])
        b -= np.linalg.solve(Hs, g)
    return dict(mu=mu, sd=sd, b=b)


def fit_mlp(X, y, w, h=16, lam=3e-3, it=600, seeds=(0, 1, 2, 3, 4)):
    """one hidden layer of h ReLU units, weighted log loss + L2 (lam), full-batch Adam (lr 0.01, it steps); an average of
    the nets fitted from 5 seeds"""
    mu = X.mean(0); sd = X.std(0) + 1e-6; Z = (X - mu) / sd; w = w / w.mean(); nets = []
    for seed in seeds:
        rng = np.random.default_rng(seed)
        P = [rng.normal(0, 1 / np.sqrt(Z.shape[1]), (Z.shape[1], h)), np.zeros(h), rng.normal(0, 1 / np.sqrt(h), h), np.zeros(1)]
        m = [np.zeros_like(q) for q in P]; v = [np.zeros_like(q) for q in P]
        for t in range(1, it + 1):
            H = np.maximum(Z @ P[0] + P[1], 0); p = 1 / (1 + np.exp(-(H @ P[2] + P[3][0]))); d = w * (p - y) / len(y)
            dH = np.outer(d, P[2]) * (H > 0); G = [Z.T @ dH + lam * P[0], dH.sum(0), H.T @ d + lam * P[2], np.array([d.sum()])]
            for i, g in enumerate(G):
                m[i] = 0.9 * m[i] + 0.1 * g; v[i] = 0.999 * v[i] + 0.001 * g * g; P[i] -= 0.01 * (m[i] / (1 - 0.9 ** t)) / (np.sqrt(v[i] / (1 - 0.999 ** t)) + 1e-8)
        nets.append(P)
    return dict(kind='mlp', mu=mu, sd=sd, W1=np.stack([q[0] for q in nets]), b1=np.stack([q[1] for q in nets]), W2=np.stack([q[2] for q in nets]), b2=np.stack([q[3] for q in nets]))


def apply(C, X):
    if str(C.get('kind', 'logistic')) == 'mlp':
        Z = (X - C['mu']) / C['sd']; out = 0
        for W1, b1, W2, b2 in zip(C['W1'], C['b1'], C['W2'], C['b2']): out = out + 1 / (1 + np.exp(-(np.maximum(Z @ W1 + b1, 0) @ W2 + b2[0])))
        return out / len(C['W1'])
    Z = np.c_[(X - C['mu']) / C['sd'], np.ones(len(X))]; return 1 / (1 + np.exp(-Z @ C['b']))


def dev_pieces(S, N, crops):
    """pieces of plate N inside each truth crop, with truth-text and truth-non-text pixels"""
    from tune import TRUTH
    out = []
    for t in CROPS:
        c = crops[t]
        if c['plate'] != N: continue
        x0, y0, x1, y1 = c['win']; tr = cv2.imread(os.path.join(TRUTH, f'{t}_mask.png'), 0); bb = S['bbox']
        s = np.nonzero((bb[:, 0] >= x0) & (bb[:, 1] >= y0) & (bb[:, 0] + bb[:, 2] <= x1) & (bb[:, 1] + bb[:, 3] <= y1))[0]
        for i in s:
            x, y, w, h = bb[i]; m = finder3.piece_mask(S, i) > 0; v = tr[y - y0:y - y0 + h, x - x0:x - x0 + w][m]
            out.append((t, int(i), int((v == 2).sum()), int((v == 1).sum())))
    return out


def main():
    a = sys.argv[1:]; mp = next((x for x in a if x.endswith('.npz') and not x.startswith('--')), finder3.MODEL)
    outp = a[a.index('--out') + 1] if '--out' in a else os.path.join(OUT, 'combiner.npz')
    from tune import load_state, TRUTH
    M = load_model(mp); crops = json.load(open(os.path.join(TRUTH, 'crops.json')))
    rows = []; Xs = []
    for N in ('44', '1A', '5'):
        S = load_state(N); dp = dev_pieces(S, N, crops)
        idx = np.array([d[1] for d in dp]); e = np.maximum(S['bbox'][idx, 2], S['bbox'][idx, 3]); keep = (e >= finder3.P3['ext'][0]) & (e <= finder3.P3['ext'][1])
        idx = idx[keep]; dp = [d for d, k_ in zip(dp, keep) if k_]
        from common import piece_features
        from model_np import predict
        img, sc = piece_features([finder3.piece_mask(S, i) for i in idx]); pr = predict(M, img, sc)
        Xs.append(features(S, pr, idx, M['classes'])); rows += [(N,) + d for d in dp]
        print(N, len(dp), 'dev pieces', flush=True)
    X = np.vstack(Xs); crop = np.array([r[1] for r in rows]); t2 = np.array([r[3] for r in rows]); t1 = np.array([r[4] for r in rows])
    sc_ = (t2 + t1) > 0; y = (t2 > t1).astype(float); w = np.minimum(t2 + t1, 400).astype(float)
    FIT = fit_mlp if '--logistic' not in a else fit
    p_loco = np.full(len(y), np.nan)
    for t in CROPS:
        tr = sc_ & (crop != t); C = FIT(X[tr], y[tr], w[tr]); p_loco[crop == t] = apply(C, X[crop == t])
    C = FIT(X[sc_], y[sc_], w[sc_]); p_all = apply(C, X)
    from common import wauc
    print('weighted AUC of P(text), leave-one-crop-out:', round(wauc(p_loco[sc_], y[sc_], w[sc_]), 4), '| in-sample:', round(wauc(p_all[sc_], y[sc_], w[sc_]), 4))
    lpj = X[:, 0]; print('shape classifier alone, AUC of -logit P(junk):', round(wauc(-lpj[sc_], y[sc_], w[sc_]), 4), '| finder2 call alone:', round(wauc(X[sc_, 8], y[sc_], w[sc_]), 4))
    if 'b' in C:
        for n, b in sorted(zip(NAMES + ['bias'], C['b']), key=lambda q: -abs(q[1]))[:12]: print(f'   {n:14s} {b:+.3f}')
    np.savez_compressed(outp, **C, names=np.array(NAMES), shape_model=os.path.basename(mp), fitted_on='truth v2 T1-T7 pieces (all six crops)')
    base = os.path.splitext(outp)[0]
    np.savez_compressed(base + '_X.npz', X=X, y=y, w=w, crop=crop, scored=sc_, names=np.array(NAMES))
    np.savez_compressed(base + '_loco.npz', plate=np.array([r[0] for r in rows]), idx=np.array([r[2] for r in rows]), crop=crop, p_loco=p_loco, p_all=p_all, t2=t2, t1=t1)
    print('->', outp)


if __name__ == '__main__':
    main()
