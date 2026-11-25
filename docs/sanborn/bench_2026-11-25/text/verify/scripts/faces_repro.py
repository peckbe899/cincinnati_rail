"""verify: reproduce the shapes agent's knn_ctx face score (eval_faces.py) without writing into its folder.
cd data/sanborn; python -B bench_2026-11-25/text/verify/scripts/faces_repro.py  -> prints; writes verify/out/faces_repro.json"""
import os, sys, json
T = os.path.join(os.getcwd(), 'bench_2026-11-25', 'text'); sys.path.insert(0, os.path.join(T, 'shapes', 'scripts'))
from read import Reader
import eval_faces as EF
R = Reader(os.path.join(T, 'shapes', 'model_no44.npz')); DIG = set('0123456789'); Rd = EF.Restricted(R, DIG | {'junk'}); out = {}; tot = {}
for f, (N, a, b, truth) in EF.FACES.items():
    D, W = EF.face_words(N, a, b, Rd, True, None); s = EF.score(truth, ' '.join(w['text'] for w in W), DIG); out[f] = s
    for k in ('n', 'right', 'wrong', 'missed', 'extra', 'numbers', 'numbers_right'): tot[k] = tot.get(k, 0) + s[k]
    print(f, s['right'], '/', s['n'], 'numbers', s['numbers_right'], '/', s['numbers'])
print('TOTAL', tot); json.dump(dict(per=out, total=tot), open(os.path.join(T, 'verify', 'out', 'faces_repro.json'), 'w'), indent=1)
