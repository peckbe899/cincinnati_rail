"""Development loop (finder2, 25 Nov 2026): run a finder module on the truth v2 windows T1-T7 (with a 300 px margin, so
the window edge does not change the result inside the crop), score it with score_text.py's rules, and break the misses
and false text down by the finder's piece kind. Truth v2 only (text_v1/truth); never the held-out crops.

    cd data/sanborn
    python -B bench_2026-11-25/text_v1/finder2/scripts/devscore.py [--mod finder2] [--codes 2,3] [--save DIR] [T1 ...]

--save DIR writes each window's code image (crop-sized, T#_text.png) there, for score_text.py --binary or errpic."""
import json, os, sys, time, importlib
sys.dont_write_bytecode = True
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__))
TRUTH = os.path.normpath(os.path.join(HERE, '..', '..', 'truth'))
CODE = os.path.normpath(os.path.join(HERE, '..', '..', 'code'))
sys.path.insert(0, CODE); sys.path.insert(0, HERE)
from score_text import poly_fill

a = sys.argv[1:]
def opt(k, d):
    global a
    if k in a: i = a.index(k); v = a[i + 1]; a = a[:i] + a[i + 2:]; return v
    return d
mod = opt('--mod', 'finder2'); codes = [int(v) for v in opt("--codes", "2,3").split(",")]; save = opt('--save', None)
ids = a or ['T1', 'T2', 'T3', 'T4', 'T6', 'T7']
F = importlib.import_module(mod)
M = 300
crops = json.load(open(os.path.join(TRUTH, 'crops.json')))
tot = dict(tp=0, fp=0, fn=0); kinds = {}; miss_k = {}; fp_k = {}; t00 = time.time()
for tid in ids:
    c = crops[tid]; x0, y0, x1, y1 = c['win']
    code, rec, (n, lb, Fe, k) = F.run(c['plate'], (x0 - M, y0 - M, x1 + M, y1 + M), out=None, verbose=False)
    sl = (slice(M, M + y1 - y0), slice(M, M + x1 - x0)); code = code[sl]; lbc = lb[sl]
    tr = cv2.imread(os.path.join(TRUTH, f'{tid}_mask.png'), 0)
    pred = np.isin(code, codes); t2 = tr == 2; t1 = tr == 1
    tp, fp, fn = int((pred & t2).sum()), int((pred & t1).sum()), int((~pred & t2).sum())
    for kk, v in (('tp', tp), ('fp', fp), ('fn', fn)): tot[kk] += v
    P_ = tp / max(1, tp + fp); R_ = tp / max(1, tp + fn)
    print(f'{tid} P {P_:.4f} R {R_:.4f} F1 {2 * P_ * R_ / max(1e-9, P_ + R_):.4f}   fp {fp} fn {fn}', flush=True)
    kk = np.asarray(k, dtype=object)
    lab = np.where(code == 1, 'LINE', np.where(lbc > 0, kk[lbc].astype(str), 'ring'))
    for nm, m, D in (('miss', ~pred & t2, miss_k), ('fp', pred & t1, fp_k)):
        u, cnt = np.unique(lab[m], return_counts=True)
        for uu, cc in zip(u, cnt): D[uu] = D.get(uu, 0) + int(cc)
    W = json.load(open(os.path.join(TRUTH, f'{tid}_words.json'), encoding='utf8'))['words']
    for w in W:
        if not w.get('poly'): continue
        pm = poly_fill(tr.shape, w['poly'], np.array([x0, y0])) & t2; nn = int(pm.sum())
        if not nn: continue
        d = kinds.setdefault(w['kind'], [0, 0]); d[0] += nn; d[1] += int((pm & pred).sum())
    if save:
        os.makedirs(save, exist_ok=True); cv2.imwrite(os.path.join(save, f'{tid}_text.png'), code)
P_ = tot['tp'] / max(1, tot['tp'] + tot['fp']); R_ = tot['tp'] / max(1, tot['tp'] + tot['fn'])
print(f'ALL P {P_:.4f} R {R_:.4f} F1 {2 * P_ * R_ / (P_ + R_):.4f}   fp {tot["fp"]} fn {tot["fn"]}   ({time.time() - t00:.0f} s)')
print('recall by kind: ' + '  '.join(f'{kk} {v[1] / max(1, v[0]):.3f}' for kk, v in sorted(kinds.items())))
print('missed text by finder label: ' + ', '.join(f'{kk} {v}' for kk, v in sorted(miss_k.items(), key=lambda x: -x[1])))
print('false text by finder label:  ' + ', '.join(f'{kk} {v}' for kk, v in sorted(fp_k.items(), key=lambda x: -x[1])))
