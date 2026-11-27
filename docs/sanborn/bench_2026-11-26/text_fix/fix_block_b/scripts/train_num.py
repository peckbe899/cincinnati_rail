"""Fit the NUMBER model of blockfix: P(a chain of recognised figures is a block number), from numbers that describe it
(blockfix.NUM_FEATS: figure scores, size and fill, thick ink round it, letter-sized neighbours, finder3's codes under it).
Labels: on the survey lists or not (analyze_nums.py's rule). Fitted on one fold's plates, checked on the other's.
    python -B .../scripts/train_num.py FEATS.json FOLD OUT.npz [--mlp H]
FEATS.json: analyze_nums.py's nums_features.json of a cross-fold run (each plate read by the model of the other fold)."""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'code'))
import numpy as np
import bfcommon as C, blockfix as B

fj, fold, outp = sys.argv[1], sys.argv[2], sys.argv[3]; H = int(sys.argv[sys.argv.index('--mlp') + 1]) if '--mlp' in sys.argv else 0
rows = json.load(open(fj)); FE = list(B.NUM_FEATS)
tr_pl = C.FOLD['A'] + C.FOLD['B'] if fold == 'all' else C.FOLD[fold]
te_pl = [] if fold == 'all' else C.FOLD['B' if fold == 'A' else 'A']
X = lambda R: np.array([[r['feat'][k] for k in FE] for r in R], np.float32); Y = lambda R: np.array([r['lab'] for r in R], np.float32)
Rtr = [r for r in rows if r['plate'] in tr_pl]; Rte = [r for r in rows if r['plate'] in te_pl]
Xtr, ytr = X(Rtr), Y(Rtr); mu = Xtr.mean(0); sd = Xtr.std(0) + 1e-3; Z = (Xtr - mu) / sd
rng = np.random.default_rng(3); wpos = (1 - ytr).sum() / max(1, ytr.sum()); wt = np.where(ytr == 1, wpos, 1.0).astype(np.float32)
if H:
    W1 = rng.normal(0, np.sqrt(2 / Z.shape[1]), (Z.shape[1], H)).astype(np.float32); b1 = np.zeros(H, np.float32); w = np.zeros(H, np.float32); b = 0.0
else:
    w = np.zeros(Z.shape[1], np.float32); b = 0.0
lr, l2 = 0.05, 1e-2
for it in range(3000):
    if H:
        hd = np.maximum(0, Z @ W1 + b1); o = hd @ w + b
    else: o = Z @ w + b
    pr = 1 / (1 + np.exp(-o)); g = (pr - ytr) * wt / wt.sum()
    if H:
        gw = hd.T @ g + l2 * w; gb = g.sum(); gh = np.outer(g, w) * (hd > 0); gW1 = Z.T @ gh + l2 * W1; gb1 = gh.sum(0)
        W1 -= lr * gW1; b1 -= lr * gb1; w -= lr * gw; b -= lr * gb
    else:
        w -= lr * (Z.T @ g + l2 * w); b -= lr * g.sum()


def pred(Xa):
    z = (Xa - mu) / sd
    o = (np.maximum(0, z @ W1 + b1) @ w + b) if H else (z @ w + b)
    return 1 / (1 + np.exp(-o))


def auc(p, y):
    o = np.argsort(p); r = np.empty(len(p)); r[o] = np.arange(1, len(p) + 1); npos = y.sum(); nneg = len(y) - npos
    return float((r[y == 1].sum() - npos * (npos + 1) / 2) / max(1, npos * nneg))


rep = dict(fold=fold, feats=FE, train=dict(n=len(ytr), pos=int(ytr.sum()), auc=round(auc(pred(Xtr), ytr), 4)))
print('train', rep['train'])
if Rte:
    Xte, yte = X(Rte), Y(Rte); pt = pred(Xte); rep['test'] = dict(n=len(yte), pos=int(yte.sum()), auc=round(auc(pt, yte), 4), at={})
    for t in (0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8):
        k = pt >= t; rep['test']['at'][t] = dict(keep_on=int((k & (yte == 1)).sum()), keep_off=int((k & (yte == 0)).sum()))
    print('test', rep['test'])
if not H: print('weights', {k: round(float(v), 2) for k, v in zip(FE, w)})
sv = dict(feats=np.array(FE), mu=mu, sd=sd, w=w, b=np.float32(b), report=json.dumps(rep))
if H: sv.update(W1=W1, b1=b1)
np.savez(outp, **sv)
