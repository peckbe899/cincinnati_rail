"""dev loop (finder2, 25 Nov 2026): run finder2 on the truth v2 windows T1-T7 (300 px margin), score with score_text.py's
pixel rules (text = codes 2,3), print P/R/F1, recall by kind, and where missed / false text went. Truth v2 only.
    cd data/sanborn; python -B <this> [--set key=value ...] [--save DIR] [T1 ...]"""
import json, os, sys, time, ast
sys.dont_write_bytecode = True
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); TV1 = os.path.normpath(os.path.join(HERE, '..', '..', '..'))
TRUTH = os.path.join(TV1, 'truth'); sys.path.insert(0, os.path.join(TV1, 'code'))
from score_text import poly_fill
import finder2 as F
a = sys.argv[1:]; save = None; ids = []
i = 0
while i < len(a):
    if a[i] == '--set': k, v = a[i + 1].split('=', 1); F.P[k] = ast.literal_eval(v); i += 2
    elif a[i] == '--save': save = a[i + 1]; i += 2
    else: ids.append(a[i]); i += 1
ids = ids or ['T1', 'T2', 'T3', 'T4', 'T6', 'T7']
M = 300; crops = json.load(open(os.path.join(TRUTH, 'crops.json'))); tot = dict(tp=0, fp=0, fn=0); kinds = {}; miss = {}; fps = {}; t00 = time.time()
for tid in ids:
    c = crops[tid]; x0, y0, x1, y1 = c['win']
    code, rec, _ = F.run(c['plate'], (x0 - M, y0 - M, x1 + M, y1 + M), out=None, verbose=False)
    code = code[M:M + y1 - y0, M:M + x1 - x0]
    tr = cv2.imread(os.path.join(TRUTH, f'{tid}_mask.png'), 0); pred = np.isin(code, (2, 3)); t2 = tr == 2; t1 = tr == 1
    tp, fp, fn = int((pred & t2).sum()), int((pred & t1).sum()), int((~pred & t2).sum())
    for kk, v in (('tp', tp), ('fp', fp), ('fn', fn)): tot[kk] += v
    for v in range(6):
        miss[v] = miss.get(v, 0) + int(((code == v) & t2 & ~pred).sum()); fps[v] = fps.get(v, 0) + int(((code == v) & t1 & pred).sum())
    P_ = tp / max(1, tp + fp); R_ = tp / max(1, tp + fn)
    print(f'{tid} P {P_:.4f} R {R_:.4f} F1 {2 * P_ * R_ / max(1e-9, P_ + R_):.4f}  fp {fp} fn {fn}  big {rec.get("big")}', flush=True)
    for w in json.load(open(os.path.join(TRUTH, f'{tid}_words.json'), encoding='utf8'))['words']:
        if not w.get('poly'): continue
        pm = poly_fill(tr.shape, w['poly'], np.array([x0, y0])) & t2; nn = int(pm.sum())
        if nn: d = kinds.setdefault(w['kind'], [0, 0]); d[0] += nn; d[1] += int((pm & pred).sum())
    if save: os.makedirs(save, exist_ok=True); cv2.imwrite(os.path.join(save, f'{tid}_text.png'), code)
P_ = tot['tp'] / max(1, tot['tp'] + tot['fp']); R_ = tot['tp'] / max(1, tot['tp'] + tot['fn'])
print(f'ALL P {P_:.4f} R {R_:.4f} F1 {2 * P_ * R_ / (P_ + R_):.4f}  fp {tot["fp"]} fn {tot["fn"]}  ({time.time() - t00:.0f} s)')
print('recall: ' + '  '.join(f'{kk} {v[1] / max(1, v[0]):.3f}' for kk, v in sorted(kinds.items())))
print('missed text by code: ', {k: v for k, v in miss.items() if v}, '  false text by code:', {k: v for k, v in fps.items() if v})
