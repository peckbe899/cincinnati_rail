"""Dev harness for dittofix (26 Nov 2026). DEV AND CHECKS ONLY: it reads the dev truth; dittofix.py never imports it.

    cd data/sanborn
    python -B bench_2026-11-26/text_fix/fix_ditto/code/harness.py cache [N ...]     # marks + features per plate -> work/cache/N.pkl
    (then import harness and call evaluate(accept_fn) from tuning scripts)

The cache holds, per plate: every mark's features (dittofix.marks + context), the code-5 pixels of each mark (flat
indices), and the finder3 codes cut to every dev window on the plate. evaluate() turns accepted marks into new codes
inside those windows and scores them with the same rules as score_text.py (pixels inside the truth, words found when
half or more of their text px are called text). Final numbers are always re-made with score_text.py itself.
"""
import os, sys, json, pickle, time, collections
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import numpy as np, cv2
import devdata as D, dittofix as DF

WORK = os.environ.get('DITTO_CACHE') or os.path.join(HERE, '..', 'work', 'cache')
PARAMS = json.loads(os.environ['DITTO_PARAMS']) if os.environ.get('DITTO_PARAMS') else None


def cache_plate(N, p=None):
    t0 = time.time()
    codes = cv2.imread(D.f3_path(N), 0); gray, paper = DF.load(N); ft = DF.scale_of(N)
    lb, F, M, s = DF.marks(codes, gray, ft, p, paper); M = DF.context(M, F, s)
    flat = lb.ravel(); c5 = (codes.ravel() == 5)
    pix = []
    for k in range(len(M['A'])):
        x0, y0, x1, y1 = M['box'][k]; sub = lb[y0:y1, x0:x1]; m = np.isin(sub, M['ids'][k]) & (codes[y0:y1, x0:x1] == 5)
        yy, xx = np.nonzero(m); pix.append(((yy + y0) * codes.shape[1] + xx + x0).astype(np.int64))
    C = {k: c for k, c in D.crops().items() if c['plate'] == N}
    win = {}
    for k, c in C.items():
        x0, y0, x1, y1 = c['win']; m, W = D.truth(c, k)
        win[k] = dict(c=c, code=codes[y0:y1, x0:x1].copy(), truth=m, words=W)
    os.makedirs(WORK, exist_ok=True)
    M.pop('ids')
    pickle.dump(dict(N=N, ft=ft, shape=codes.shape, M=M, pix=pix, win=win), open(os.path.join(WORK, f'{N}.pkl'), 'wb'))
    print(N, ft, len(pix), 'marks', f'{time.time() - t0:.0f} s', flush=True)


def load_all():
    out = {}
    for f in sorted(os.listdir(WORK)):
        if f.endswith('.pkl'): d = pickle.load(open(os.path.join(WORK, f), 'rb')); out[d['N']] = d
    return out


def poly_fill(shape, poly, off):
    m = np.zeros(shape, np.uint8); cv2.fillPoly(m, [np.round(np.array(poly, float) - off).astype(np.int32)], 1); return m > 0


def new_win_codes(d, acc):
    """the crop windows' codes after turning the accepted marks' code-5 pixels into 3"""
    H, W = d['shape']; out = {}
    idx = np.concatenate([d['pix'][k] for k in np.nonzero(acc)[0]]) if acc.any() else np.zeros(0, np.int64)
    ys, xs = idx // W, idx % W
    for k, w in d['win'].items():
        x0, y0, x1, y1 = w['c']['win']; c = w['code'].copy()
        s = (xs >= x0) & (xs < x1) & (ys >= y0) & (ys < y1); c[ys[s] - y0, xs[s] - x0] = 3
        out[k] = c
    return out


def word_index(w):
    """per window, once: every word's text px (truth 2 inside its polygon) as flat indices; for negative marks the ink"""
    if 'widx' in w: return w['widx']
    t = w['truth']; x0, y0 = w['c']['win'][:2]; out = []
    for wd in w['words']:
        p = wd.get('poly')
        if not p: continue
        pm = poly_fill(t.shape, p, np.array([x0, y0]))
        if wd.get('kind') == 'negative':
            out.append(dict(kind='negative', neg=wd.get('neg_type'), idx=np.flatnonzero(pm & (t == 1)), id=wd['id'])); continue
        idx = np.flatnonzero(pm & (t == 2))
        if not len(idx): continue
        out.append(dict(kind=wd['kind'], style=wd.get('style', ''), target=bool(wd.get('target')), idx=idx, id=wd['id']))
    w['widx'] = out; w['t2'] = (t == 2); w['t1'] = (t == 1)
    return out


def score_win(w, code):
    widx = word_index(w); pred = np.isin(code, (2, 3)); t2, t1 = w['t2'], w['t1']
    r = dict(tp=int((pred & t2).sum()), fp=int((pred & t1).sum()), fn=int((~pred & t2).sum()), t1=int(t1.sum()))
    pf = pred.ravel(); words = []
    for wd in widx:
        n = len(wd['idx']); f = int(pf[wd['idx']].sum())
        e = {k: v for k, v in wd.items() if k != 'idx'}; e.update(n=n, f=f); words.append(e)
    r['words'] = words
    return r


def evaluate(data, accept, plates=None):
    """accept: dict N -> bool array over the plate's marks. Returns per-crop scores"""
    res = {}
    for N, d in data.items():
        if plates and N not in plates: continue
        acc = accept.get(N, np.zeros(len(d['pix']), bool))
        nc = new_win_codes(d, acc)
        for k, w in d['win'].items():
            r = score_win(w, nc[k]); r.update(plate=N, ft=d['ft'], set=w['c']['set'], fold=D.fold(N)); res[k] = r
    return res


def summary(res, fold=None):
    """pooled numbers: dev ditto (targets) recall by scale/style, in-scope P/R/F1, negatives, T1-T7"""
    S = collections.OrderedDict()
    sel = {k: r for k, r in res.items() if fold is None or r['fold'] == fold}
    dd = [r for r in sel.values() if r['set'] == 'dd']; ng = [r for r in sel.values() if r['set'] == 'neg']; tt = [r for r in sel.values() if r['set'] == 't']
    def prf(rs):
        tp = sum(r['tp'] for r in rs); fp = sum(r['fp'] for r in rs); fn = sum(r['fn'] for r in rs); t1 = sum(r['t1'] for r in rs)
        P = tp / max(1, tp + fp); R = tp / max(1, tp + fn); return dict(P=round(P, 4), R=round(R, 4), F1=round(2 * P * R / max(1e-9, P + R), 4), ntct=round(fp / max(1, t1), 4), fp=fp)
    S['dd_scope'] = prf(dd); S['t17'] = prf(tt)
    def rec(ws):
        n = sum(w['n'] for w in ws); f = sum(w['f'] for w in ws); return dict(words=len(ws), px=round(f / max(1, n), 3), found=sum(w['f'] >= 0.5 * w['n'] for w in ws))
    tw = [(r['ft'], w) for r in dd for w in r['words'] if w['target']]
    S['ditto_all'] = rec([w for _, w in tw])
    for ft in (100, 200, 400): S[f'ditto_{ft}'] = rec([w for f, w in tw if f == ft])
    for st in ('pair', 'quote', 'other'): S[f'ditto_{st}'] = rec([w for _, w in tw if w['style'] == st])
    S['ditto_tiny_pair'] = rec([w for _, w in tw if w['style'] == 'pair' and w['n'] <= 30])
    S['t17_ditto'] = rec([w for r in tt for w in r['words'] if w['kind'] == 'ditto'])
    nw = [w for r in ng for w in r['words'] if w['kind'] == 'negative']
    def negr(ws):
        n = sum(w['n'] for w in ws); f = sum(w['f'] for w in ws); return dict(marks=len(ws), px=round(f / max(1, n), 3), hit=sum(w['f'] >= 0.5 * w['n'] for w in ws if w['n']))
    S['neg_all'] = negr(nw)
    for t in ('rail_tick', 'dash', 'hook', 'line_end'): S[f'neg_{t}'] = negr([w for w in nw if w['neg'] == t])
    for kd in ('street', 'block'): S[f't17_{kd}'] = rec([w for r in tt for w in r['words'] if w['kind'] == kd])
    return S


def show(S):
    return ' | '.join(f"{k}: " + ' '.join(f'{a}={b}' for a, b in v.items()) for k, v in S.items())


if __name__ == '__main__':
    if sys.argv[1] == 'cache':
        plates = sys.argv[2:] or sorted({c['plate'] for c in D.crops().values()})
        for N in plates: cache_plate(N, PARAMS)
