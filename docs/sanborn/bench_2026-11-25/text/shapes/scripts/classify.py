"""A tiny k-NN glyph reader fitted on cluster labels (shapes prototype, 25 Nov 2026).

    python -B bench_2026-11-25/text/shapes/scripts/classify.py LABELS.json [LABELS2.json ...] [--per N] [--out pred.npz]
    (from data/sanborn)   --holdout P: no training glyph from plate P (a reader that never saw P); --model-only:
    write model*.npz and the checks, skip reading every glyph

What is fitted on what:
  - the glyphs are those of extract_glyphs.py on the six plates (glyphs/*.npz), clusters from cluster.py (clusters.npz);
  - each LABELS.json gives a character (or 'junk') to some clusters of the clusters file it names ('clusters').
    A glyph labelled in two rounds keeps the later label. Every member of a labelled cluster takes that label,
    except the 20% of members furthest from their cluster's mean (in the feature space below), which are left out
    as likely strays. --per N keeps at most N random training glyphs per class (for the learning curve);
  - features: those of cluster.py (blurred pixels 16x16, HOG, log size), PCA to 60 dims fitted on every glyph of
    12 px or more (no labels used);
  - reader: k-NN, k = 5, Euclidean in the PCA space, majority vote; ties to the nearest.
Writes model.npz (PCA, training glyphs in PCA space, their labels) for read.py, and pred.npz: for every glyph of 12 px or more: plate, idx, char (best class), vote share, distance to the nearest
training glyph, and the same for the glyph turned 180 deg (char180, dist180), which read.py uses for words that may
read upward. Also prints a leave-one-plate-out check: the training glyphs of one plate read by a reader fitted on the
other five (agreement with the cluster labels, which are themselves not checked glyph by glyph).
"""
import json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cluster import features, load, HERE  # noqa: E402

K = 5; NPCA = 60; KEEP = 0.8


def knn(Ztr, ytr, Z, k=K, chunk=4000):
    """k-NN vote: returns best class index, vote share, nearest distance"""
    n2 = (Ztr ** 2).sum(1)
    best = np.zeros(len(Z), int); share = np.zeros(len(Z)); dmin = np.zeros(len(Z))
    ncls = ytr.max() + 1
    for s in range(0, len(Z), chunk):
        q = Z[s:s + chunk]
        d = (q ** 2).sum(1)[:, None] + n2[None] - 2 * q @ Ztr.T
        nn = np.argpartition(d, k, axis=1)[:, :k]
        dd = np.take_along_axis(d, nn, 1); o = np.argsort(dd, 1); nn = np.take_along_axis(nn, o, 1); dd = np.take_along_axis(dd, o, 1)
        votes = np.zeros((len(q), ncls))
        for j in range(k): votes[np.arange(len(q)), ytr[nn[:, j]]] += 1 + 1e-3 * (k - j)   # ties go to the nearer
        best[s:s + chunk] = votes.argmax(1); share[s:s + chunk] = votes.max(1).round() / k
        dmin[s:s + chunk] = np.sqrt(np.maximum(dd[:, 0], 0))
    return best, share, dmin


def main():
    args = sys.argv[1:]; lfs = []
    while args and not args[0].startswith('--'): lfs.append(args.pop(0))
    per = int(sys.argv[sys.argv.index('--per') + 1]) if '--per' in sys.argv else None
    G = load(); n = len(G['imgs'])
    lab = np.full(n, '', object)
    for lf in lfs:
        J = json.load(open(lf)); C = np.load(os.path.join(HERE, J.get('clusters', 'clusters.npz')))
        assert (C['idx'] == G['idx']).all() and (C['plate'] == G['plate']).all()
        for c, ch in J['labels'].items(): lab[C['cl'] == int(c)] = ch
        print(lf, len(J['labels']), 'clusters labelled')
    mx = G['hw'].max(1); use = mx >= 12
    F = features(G['imgs'], G['hw'])
    F180 = features(G['imgs'][:, ::-1, ::-1].copy(), G['hw'])
    rng = np.random.default_rng(0)
    sub = np.nonzero(use)[0]; mu = F[sub].mean(0)
    _, _, Vt = np.linalg.svd(F[rng.choice(sub, 30000, replace=False)] - mu, full_matrices=False); V = Vt[:NPCA].T
    Z = ((F - mu) @ V).astype(np.float32); Z180 = ((F180 - mu) @ V).astype(np.float32)
    classes = sorted(set(lab[lab != ''])); ci = {c: i for i, c in enumerate(classes)}
    tr = []; ytr = []
    # strays: per (cluster file, cluster) the 20% furthest from the mean of its members that carry the label
    for lf in lfs:
        J = json.load(open(lf)); C = np.load(os.path.join(HERE, J.get('clusters', 'clusters.npz')))
        for c, ch in J['labels'].items():
            mem = np.nonzero((C['cl'] == int(c)) & (lab == ch))[0]
            if not len(mem): continue
            d = np.linalg.norm(Z[mem] - Z[mem].mean(0), axis=1)
            keep = mem[d <= np.quantile(d, KEEP)]
            tr.append(keep); ytr.append(np.full(len(keep), ci[ch]))
    tr = np.concatenate(tr); u = np.unique(tr, return_index=True)[1]; ytr = np.concatenate(ytr)[u]; tr = tr[u]
    if '--holdout' in sys.argv:
        hp = sys.argv[sys.argv.index('--holdout') + 1]; k = G['plate'][tr] != hp; tr, ytr = tr[k], ytr[k]
        print(f'holdout: no training glyph from plate {hp}')
    if per:
        sel = np.concatenate([rng.choice(np.nonzero(ytr == k)[0], min(per, (ytr == k).sum()), replace=False) for k in range(len(classes))])
        tr, ytr = tr[sel], ytr[sel]
    print('training glyphs per class:', {classes[k]: int((ytr == k).sum()) for k in range(len(classes))})
    # leave one plate out
    plates = np.unique(G['plate']); agree = []; per_class = {}
    for p in plates:
        a = G['plate'][tr] == p
        if not a.any(): continue
        b, _, _ = knn(Z[tr[~a]], ytr[~a], Z[tr[a]])
        agree.append((p, int(a.sum()), float((b == ytr[a]).mean())))
        for k in range(len(classes)):
            m = ytr[a] == k
            if m.any(): per_class.setdefault(classes[k], []).append((int(m.sum()), int((b[m] == k).sum())))
    tot = sum(n for _, n, _ in agree); print('leave-one-plate-out agreement with the cluster labels:', ', '.join(f'{p} {r:.3f} (n={n})' for p, n, r in agree),
                                             f'| all {sum(n * r for _, n, r in agree) / tot:.3f}')
    print('  per class:', ', '.join(f'{c} {sum(g for _, g in v) / sum(n for n, _ in v):.2f}' for c, v in sorted(per_class.items())))
    out = os.path.join(HERE, sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else 'pred.npz')
    if '--model-only' in sys.argv:
        np.savez_compressed(out.replace('pred', 'model'), mu=mu, V=V, Ztr=Z[tr], ytr=ytr, classes=np.array(classes), labels=np.array(lfs)); return
    # every glyph
    q = np.nonzero(use)[0]
    b, s, d = knn(Z[tr], ytr, Z[q]); b2, s2, d2 = knn(Z[tr], ytr, Z180[q])
    out = os.path.join(HERE, sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else 'pred.npz')
    np.savez_compressed(out.replace('pred', 'model'), mu=mu, V=V, Ztr=Z[tr], ytr=ytr, classes=np.array(classes), labels=np.array(lfs))
    np.savez_compressed(out, plate=G['plate'][q], idx=G['idx'][q], char=np.array(classes)[b], share=s, dist=d,
                        char180=np.array(classes)[b2], share180=s2, dist180=d2, classes=np.array(classes), labels=np.array(lfs),
                        train_plate=G['plate'][tr], train_idx=G['idx'][tr], train_y=np.array(classes)[ytr])
    cnt = {c: int((np.array(classes)[b] == c).sum()) for c in classes}
    print('read as (glyphs of 12 px or more):', cnt, '->', out)


if __name__ == '__main__':
    main()
