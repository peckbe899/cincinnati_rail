"""Summary tables for the ditto fix report (DEV/CHECK ONLY): reads score_text.py's JSON outputs (score_all.py) and, for the
breakdowns score_text.py does not give (ditto style, tiny pairs, negative types, fold x scale), scores the written masks
themselves with the same rules (harness.score_win on the crop windows cut from the plate masks).

    cd data/sanborn
    python -B bench_2026-11-26/text_fix/fix_ditto/code/summarize.py F3_DIR FIX_DIR SCORE_DIR OUT.txt
"""
import os, sys, json, collections
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import numpy as np, cv2
import devdata as D, harness as H

f3, fix, sdir, outp = sys.argv[1:5]
L = []
def p(s=''): L.append(s); print(s)

# 1. score_text.py pools
p('A. score_text.py (text_v1/code/score_text.py, codes 2,3). MEASURED. finder3 -> dittofix')
for nm, title in (('ditto', 'dev ditto truth (51 crops, scopes only)'), ('t17', 'truth v2 T1-T7'), ('block', 'dev block truth (45 crops, scopes only)'), ('neg', 'ditto negatives (73 windows)')):
    a = json.load(open(os.path.join(sdir, f'{nm}_finder3.json'))); b = json.load(open(os.path.join(sdir, f'{nm}_dittofix.json')))
    p(f'  {title}')
    for pool in ['ALL', 'foldA', 'foldB'] + sorted(k for k in a['pools'] if k.startswith('ft')):
        if pool not in a['pools']: continue
        x, y = a['pools'][pool], b['pools'][pool]
        p(f"    {pool:6s} P {x['pix']['precision']:.4f} -> {y['pix']['precision']:.4f}   R {x['pix']['recall']:.4f} -> {y['pix']['recall']:.4f}   F1 {x['pix']['f1']:.4f} -> {y['pix']['f1']:.4f}"
          f"   non-text ink called text {x['nontext_called_text']['share']:.4f} -> {y['nontext_called_text']['share']:.4f} ({x['nontext_called_text']['px']} -> {y['nontext_called_text']['px']} px)")
    for kd in ('ditto', 'street', 'block', 'story', 'lot', 'lotdim', 'house'):
        x = a['pools']['ALL']['by_kind'].get(kd); y = b['pools']['ALL']['by_kind'].get(kd)
        if x: p(f"      {kd:7s} recall {x['recall']:.3f} ({x['words_found']}/{x['words']}) -> {y['recall']:.3f} ({y['words_found']}/{y['words']})")

# 2. breakdowns from the masks
crops = D.crops(); cache = {}
def win_code(d, N, win):
    path = os.path.join(d, f'{N}_text.png')
    if path not in cache: cache.clear(); cache[path] = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    x0, y0, x1, y1 = win; return cache[path][y0:y1, x0:x1]
res = {}
for meth, d in (('finder3', f3), ('dittofix', fix)):
    r = {}
    for k, c in sorted(crops.items(), key=lambda kv: kv[1]['plate']):
        m, W = D.truth(c, k); w = dict(c=c, truth=m, words=W)
        s = H.score_win(w, win_code(d, c['plate'], c['win'])); s.update(plate=c['plate'], ft=int(c.get('scale_ft_per_inch') or json.load(open('scale_table.json'))[c['plate']]['ft_per_inch']), set=c['set'], fold=D.fold(c['plate']))
        r[k] = s
    res[meth] = r
p(); p('B. Ditto recall by group (pixels; words found = half or more of a word\'s text px). MEASURED. finder3 -> dittofix')
def rec(ws):
    n = sum(w['n'] for w in ws); f = sum(w['f'] for w in ws); return f / max(1, n), sum(w['f'] >= 0.5 * w['n'] for w in ws), len(ws)
groups = collections.OrderedDict()
def tw(r, cond): return [(w) for x in r.values() if x['set'] == 'dd' for w in x['words'] if w['target'] and cond(x, w)]
defs = [('all', lambda x, w: True)]
for f in ('A', 'B'): defs.append((f'fold {f}', lambda x, w, f=f: x['fold'] == f))
for ft in (100, 200, 400): defs.append((f'{ft} ft', lambda x, w, ft=ft: x['ft'] == ft))
for f in ('A', 'B'):
    for ft in (100, 200, 400): defs.append((f'fold {f} {ft} ft', lambda x, w, f=f, ft=ft: x['fold'] == f and x['ft'] == ft))
for st in ('pair', 'quote', 'other'): defs.append((f'style {st}', lambda x, w, st=st: w['style'] == st))
defs.append(('tiny tick pairs (pair, 30 px or less)', lambda x, w: w['style'] == 'pair' and w['n'] <= 30))
for ft in (100, 200, 400):
    for st in ('pair', 'quote', 'other'): defs.append((f'{ft} ft {st}', lambda x, w, ft=ft, st=st: x['ft'] == ft and w['style'] == st))
out = {}
for name, cond in defs:
    a = rec(tw(res['finder3'], cond)); b = rec(tw(res['dittofix'], cond))
    if a[2] == 0: continue
    out[name] = dict(words=a[2], finder3=dict(px=round(a[0], 3), found=a[1]), dittofix=dict(px=round(b[0], 3), found=b[1]))
    p(f'  {name:40s} {a[2]:4d} words   {a[0]:.3f} ({a[1]}) -> {b[0]:.3f} ({b[1]})')
tt = lambda r: [w for x in r.values() if x['set'] == 't' for w in x['words'] if w['kind'] == 'ditto']
a, b = rec(tt(res['finder3'])), rec(tt(res['dittofix']))
p(f"  {'T1-T7 ditto words':40s} {a[2]:4d} words   {a[0]:.3f} ({a[1]}) -> {b[0]:.3f} ({b[1]})")
for f in ('A', 'B'):
    a = rec([w for x in res['finder3'].values() if x['set'] == 't' and x['fold'] == f for w in x['words'] if w['kind'] == 'ditto'])
    b = rec([w for x in res['dittofix'].values() if x['set'] == 't' and x['fold'] == f for w in x['words'] if w['kind'] == 'ditto'])
    p(f"  {'T1-T7 ditto words, fold ' + f:40s} {a[2]:4d} words   {a[0]:.3f} ({a[1]}) -> {b[0]:.3f} ({b[1]})")
p(); p('C. Negatives: share of the look-alike mark ink called text (marks with half or more called text). MEASURED. finder3 -> dittofix')
for t in (None, 'rail_tick', 'dash', 'hook', 'line_end'):
    def ng(r): return [w for x in r.values() if x['set'] == 'neg' for w in x['words'] if w['kind'] == 'negative' and (t is None or w['neg'] == t)]
    A_, B_ = ng(res['finder3']), ng(res['dittofix'])
    sa = sum(w['f'] for w in A_) / max(1, sum(w['n'] for w in A_)); sb = sum(w['f'] for w in B_) / max(1, sum(w['n'] for w in B_))
    p(f"  {t or 'all':10s} {len(A_):3d} marks   {sa:.3f} ({sum(w['f'] >= 0.5 * w['n'] for w in A_ if w['n'])}) -> {sb:.3f} ({sum(w['f'] >= 0.5 * w['n'] for w in B_ if w['n'])})")
    diff = [(wa['id'], wa['f'], wb['f']) for wa, wb in zip(A_, B_) if wa['f'] != wb['f']]
    if diff: p(f'     changed marks: {diff}')
json.dump(dict(groups=out), open(outp.replace('.txt', '.json'), 'w'), indent=1)
open(outp, 'w', encoding='utf8', newline='\n').write('\n'.join(L) + '\n')
