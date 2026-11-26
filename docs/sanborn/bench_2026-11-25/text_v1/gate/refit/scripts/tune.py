"""Set finder3's two thresholds on truth v2 T1-T7 (classifier step, 26 Nov 2026). DEV ONLY: never the held-out crops.

    cd data/sanborn
    python -B bench_2026-11-25/text_v1/classifier/scripts/tune.py [MODEL.npz ...] [--grid]

Uses finder3's own stage_b and finder2's shared_ink on the saved finder2 states (data/state/N.npz, written by
finder3.py --save-state) of plates 44, 1A and 5, so a setting is scored exactly as finder3 would make it, crop by crop,
with score_text.py's rules (text = codes 2 and 3; truth 1 and 2 scored, 3 skipped). Prints P, R, F1 and non-text called
text over all 6 crops, the flips made, and recall for street names, block numbers and the adjoining sheet number."""
import json, os, sys, itertools
sys.dont_write_bytecode = True
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
CODE = os.path.normpath(os.path.join(HERE, '..', '..', 'code')); sys.path.insert(0, CODE)
import finder3, finder2  # noqa
from model_np import load_model  # noqa
TRUTH = os.path.join('bench_2026-11-25', 'text_v1', 'truth'); STATE = os.path.join(HERE, '..', 'data', 'state')
CROPS = ('T1', 'T2', 'T3', 'T4', 'T6', 'T7')


def load_state(N):
    D = dict(np.load(os.path.join(STATE, f'{N}.npz'), allow_pickle=True))
    D['pre'] = cv2.imdecode(D['pre'], 0); D['letter'] = cv2.imdecode(D['letter'], 0); D['win'] = None; D['plate'] = str(D['plate'])
    return D


def poly_mask(shape, poly, off):
    m = np.zeros(shape, np.uint8); cv2.fillPoly(m, [np.round(np.array(poly, float) - off).astype(np.int32)], 1); return m > 0


class Dev:
    def __init__(s):
        s.crops = json.load(open(os.path.join(TRUTH, 'crops.json'))); s.T = {}; s.W = {}
        for t in CROPS:
            s.T[t] = cv2.imread(os.path.join(TRUTH, f'{t}_mask.png'), 0)
            x0, y0 = s.crops[t]['win'][:2]; ws = json.load(open(os.path.join(TRUTH, f'{t}_words.json'), encoding='utf8'))['words']
            s.W[t] = [(w['kind'], poly_mask(s.T[t].shape, w['poly'], np.array([x0, y0]))) for w in ws if w.get('poly')]

    def score(s, codes):
        """codes: plate -> pre-shared code image (whole plate). Returns pooled numbers"""
        tp = fp = fn = of = 0; kinds = {}; per = {}
        for t in CROPS:
            c = s.crops[t]; x0, y0, x1, y1 = c['win']; g = 4; code = codes[c['plate']]
            sub = code[y0 - g:y1 + g, x0 - g:x1 + g].copy(); sub, _ = finder2.shared_ink(sub, (sub > 0).astype(np.uint8)); sub = sub[g:-g, g:-g]
            pred = np.isin(sub, (2, 3)); tr = s.T[t]; t2 = tr == 2; t1 = tr == 1
            a, b, d = int((pred & t2).sum()), int((pred & t1).sum()), int((~pred & t2).sum()); tp += a; fp += b; fn += d; of += int(t1.sum())
            P = a / max(1, a + b); R = a / max(1, a + d); per[t] = round(2 * P * R / max(1e-9, P + R), 4)
            for kd, m in s.W[t]:
                pt = m & t2; n = int(pt.sum())
                if n: q = kinds.setdefault(kd, [0, 0]); q[0] += n; q[1] += int((pt & pred).sum())
        P = tp / (tp + fp); R = tp / (tp + fn)
        return dict(P=round(P, 4), R=round(R, 4), F1=round(2 * P * R / (P + R), 4), nontext=round(fp / of, 5), per=per,
                    kinds={k: round(v[1] / v[0], 4) for k, v in sorted(kinds.items())})


def main():
    a = sys.argv[1:]; models = [x for x in a if x.endswith('.npz')]
    if '--grid2' in a: a.append('--grid') or [finder3.MODEL]
    dev = Dev(); S = {N: load_state(N) for N in ('44', '1A', '5')}
    base = dev.score({N: S[N]['pre'] for N in S}); print('finder2 (no second opinion):', json.dumps(base))
    res = dict(finder2=base)
    for mp in models:
        M = load_model(mp); pj = {N: finder3.classify(S[N], M)[0] for N in S}
        grid = list(itertools.product((0.8, 0.9, 0.95, 0.98, 2), (0.9, 0.95, 0.97, 0.99, 2))) if '--grid' in a else [(finder3.P3['tj'], finder3.P3['tt']), (finder3.P3['tj'], 2), (2, finder3.P3['tt'])]
        kinds = [None]
        if '--kinds' in a: kinds = [tuple(x.split(',')) for x in a[a.index('--kinds') + 1].split(';')]
        for (tj, tt), kk in itertools.product(grid, kinds):
            codes = {}; fl = {}; pp = dict(tj=tj, tt=tt)
            if kk: pp['tj_kinds'] = kk
            for N in S:
                codes[N], info = finder3.stage_b(S[N], pj[N], pp); fl[N] = (info['to_other'], info['to_text'])
            r = dev.score(codes); r['flips'] = fl; res[f'{os.path.basename(mp)} tj={tj} tt={tt} kinds={kk}'] = r
            k = r['kinds']
            print(f"{os.path.basename(mp)} tj {tj} tt {tt} kinds {kk}: P {r['P']:.4f} R {r['R']:.4f} F1 {r['F1']:.4f} nontext {r['nontext']:.4f} | street {k.get('street')} block {k.get('block')} adj {k.get('adj')} | flips {fl} | {r['per']}", flush=True)
    json.dump(res, open(os.path.join(HERE, '..', 'out', 'tune.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
