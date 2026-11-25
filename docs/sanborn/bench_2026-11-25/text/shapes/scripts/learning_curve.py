"""How many labelled glyphs does the k-NN digit reader need? (shapes prototype, 25 Nov 2026)

    python -B bench_2026-11-25/text/shapes/scripts/learning_curve.py      (from data/sanborn)

Training pool: the cluster-labelled glyphs of plates 1A, 5, 3, 90, 94 (labels/claude_round1.json + claude_round2.json,
strays left out as in classify.py), never plate 44. For N in NS, N glyphs per class are drawn at random (digits,
letters and junk alike; 3 draws, seeds 0-2) and a k-NN reader is built (PCA as classify.py; k = 1 for N < 20,
else 5). Two tests on plate 44:
  T1  every glyph of plate 44 in a labelled digit cluster (cluster labels; Claude's, by cluster, roughly 90-95% right),
      read among digit + junk training glyphs: share read as its cluster's digit;
  T2  the three block faces of eval_faces.py (80 figures, 23 house numbers, truth by eye): figures right, numbers
      right, read as knn_ctx there (digits + junk, touching figures cut).
Writes learning_curve.json.
"""
import json, os, sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cluster import features, load, HERE  # noqa: E402
from classify import knn, NPCA, KEEP  # noqa: E402
import eval_faces as EF  # noqa: E402
from read import Reader  # noqa: E402

NS = [3, 5, 10, 20, 50, 100, 200, 500, 1000]
DIG = set('0123456789')


def main():
    G = load(); F = features(G['imgs'], G['hw']); mx = G['hw'].max(1); rng = np.random.default_rng(0)
    sub = np.nonzero(mx >= 12)[0]; mu = F[sub].mean(0)
    _, _, Vt = np.linalg.svd(F[rng.choice(sub, 30000, replace=False)] - mu, full_matrices=False); V = Vt[:NPCA].T
    Z = ((F - mu) @ V).astype(np.float32)
    lab = np.full(len(Z), '', object); inner = np.zeros(len(Z), bool)
    for lf in ('claude_round1.json', 'claude_round2.json'):
        J = json.load(open(os.path.join(HERE, 'labels', lf))); C = np.load(os.path.join(HERE, J['clusters']))
        for c, ch in J['labels'].items():
            m = C['cl'] == int(c); lab[m] = ch
    for lf in ('claude_round1.json', 'claude_round2.json'):
        J = json.load(open(os.path.join(HERE, 'labels', lf))); C = np.load(os.path.join(HERE, J['clusters']))
        for c, ch in J['labels'].items():
            mem = np.nonzero((C['cl'] == int(c)) & (lab == ch))[0]
            if len(mem): d = np.linalg.norm(Z[mem] - Z[mem].mean(0), axis=1); inner[mem[d <= np.quantile(d, KEEP)]] = True
    classes = sorted(set(lab[lab != ''])); ci = {c: i for i, c in enumerate(classes)}
    y = np.array([ci.get(c, -1) for c in lab])
    pool = inner & (G['plate'] != '44') & (y >= 0)
    t1 = np.nonzero((G['plate'] == '44') & np.isin(lab, list(DIG)))[0]
    dig_or_junk = np.array([c in DIG or c == 'junk' for c in classes])
    out = []
    for N in NS:
        for seed in range(3 if N < 200 else 1):
            r = np.random.default_rng(seed)
            tr = np.concatenate([r.choice(np.nonzero(pool & (y == k))[0], min(N, int((pool & (y == k)).sum())), replace=False) for k in range(len(classes))])
            k_ = 1 if N < 20 else 5
            m = dig_or_junk[y[tr]]
            b, _, _ = knn(Z[tr][m], y[tr][m], Z[t1], k=k_)
            acc1 = float((np.array(classes)[b] == lab[t1]).mean())
            R = Reader.__new__(Reader); R.mu, R.V, R.Ztr, R.ytr, R.classes, R.k = mu, V, Z[tr], y[tr], np.array(classes), k_
            Rd = EF.Restricted(R, DIG | {'junk'})
            tot = dict(n=0, right=0, numbers=0, numbers_right=0)
            for fname, (Np, a, bb, truth) in EF.FACES.items():
                D, W = EF.face_words(Np, a, bb, Rd, True, 1e9)
                s = EF.score(truth, ' '.join(w['text'] for w in W), DIG)
                for kk in tot: tot[kk] += s[kk]
            rec = dict(N=N, seed=seed, k=k_, train_glyphs=int(len(tr)), digit_train=int(m.sum() - (y[tr][m] == ci['junk']).sum()),
                       T1_agree=acc1, T1_n=int(len(t1)), T2_figures=f"{tot['right']}/{tot['n']}", T2_numbers=f"{tot['numbers_right']}/{tot['numbers']}")
            print(rec); out.append(rec)
    json.dump(dict(note=__doc__, runs=out), open(os.path.join(HERE, 'learning_curve.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
