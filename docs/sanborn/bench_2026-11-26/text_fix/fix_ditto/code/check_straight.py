"""CHECK ONLY (26 Nov 2026): the 200 ft line concern (skeptic, text_v1/skeptic/scripts/sk_score.py lineish, same rule):
truth-1 ink lying on a straight run of 61 px or more (opening with 61 px lines every 7.5 deg) called text, before and
after dittofix, on the dev windows of 200 ft plates (dev ditto truth and dev block truth; their scopes only, as the truth
marks ink outside the scope 3, don't care). Also every window at 100 and 400 ft, for reference.

    cd data/sanborn
    python -B bench_2026-11-26/text_fix/fix_ditto/code/check_straight.py F3_DIR FIX_DIR OUT.json
"""
import os, sys, json
sys.dont_write_bytecode = True
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import devdata as D


def straight_of(t1):
    u = t1.astype(np.uint8); s = np.zeros(t1.shape, bool); L = 61
    for ang in np.arange(0, 180, 7.5):
        k = np.zeros((L, L), np.uint8); c = L // 2; d = np.array([np.cos(np.radians(ang)), np.sin(np.radians(ang))])
        p0 = np.round(c - d * c).astype(int); p1 = np.round(c + d * c).astype(int); cv2.line(k, tuple(p0.tolist()), tuple(p1.tolist()), 1, 1)
        s |= cv2.morphologyEx(u, cv2.MORPH_OPEN, k) > 0
    return s


f3d, fxd, outp = sys.argv[1:4]
sets = dict(ditto=D.DD, block=os.path.join(D.TF, 'dev_block', 'truth'))
tab = json.load(open('scale_table.json')); R = {}; cache = {}
def code(d, N):
    p = os.path.join(d, f'{N}_text.png')
    if p not in cache:
        if len(cache) > 2: cache.clear()
        cache[p] = cv2.imread(p, 0)
    return cache[p]
for nm, tdir in sets.items():
    crops = json.load(open(os.path.join(tdir, 'crops.json')))
    for k, c in sorted(crops.items(), key=lambda kv: kv[1]['plate']):
        mp = os.path.join(tdir, f'{k}_mask.png')
        if not os.path.exists(mp): continue
        t = cv2.imread(mp, 0); x0, y0, x1, y1 = c['win']; st = straight_of(t == 1)
        a = np.isin(code(f3d, c['plate'])[y0:y1, x0:x1], (2, 3)); b = np.isin(code(fxd, c['plate'])[y0:y1, x0:x1], (2, 3))
        ft = int(tab[c['plate']]['ft_per_inch'])
        R[f'{nm}:{k}'] = dict(plate=c['plate'], ft=ft, fold=D.fold(c['plate']), straight_px=int(st.sum()), finder3=int((st & a).sum()), dittofix=int((st & b).sum()),
                              nontext_px=int((t == 1).sum()), nontext_called_f3=int(((t == 1) & a).sum()), nontext_called_fix=int(((t == 1) & b).sum()))
out = {}
for ft in (100, 200, 400):
    for fold in (None, 'A', 'B'):
        v = [r for r in R.values() if r['ft'] == ft and (fold is None or r['fold'] == fold)]
        if not v: continue
        s = sum(r['straight_px'] for r in v); a = sum(r['finder3'] for r in v); b = sum(r['dittofix'] for r in v)
        key = f'{ft}ft' + (f'_fold{fold}' if fold else '')
        out[key] = dict(windows=len(v), straight_px=s, finder3_called=a, dittofix_called=b, finder3_share=round(a / max(1, s), 5), dittofix_share=round(b / max(1, s), 5))
        print(key, out[key])
json.dump(dict(pooled=out, by_window=R), open(outp, 'w', encoding='utf8', newline='\n'), indent=1)
