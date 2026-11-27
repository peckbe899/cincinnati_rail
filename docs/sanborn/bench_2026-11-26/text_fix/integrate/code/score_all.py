"""CHECK ONLY (integrate, 26 Nov 2026): score several masks side by side on every dev truth set.

    cd data/sanborn
    python -B bench_2026-11-26/text_fix/integrate/code/score_all.py OUT_DIR NAME=PATTERN[:CODES] [NAME=PATTERN[:CODES] ...] [--sets block,ditto,neg,t17]

PATTERN holds {plate}; CODES default 2,3 (bin 8: unet_data/{plate}_bins.png:8).
1. text_v1/code/score_text.py (unchanged, read-only) on each truth set, with pools by fold and by scale:
     block  dev_block/truth (45 crops). Folds by plate as fix_block_b's cross-fold models: A = 3 54A 30 26A 74 49,
            B = 12 19 64A 60B 93A 48.
     ditto  dev_ditto/truth (51 crops). Folds by plate as fix_ditto: A = 44 2 3 54A 30 60B 74 90 48, B = the rest.
     neg    dev_ditto/negatives (73 windows).
     t17    text_v1/truth (truth v2, T1-T7).
   Outputs OUT_DIR/<set>__<name>.json and .txt.
2. The breakdowns score_text.py does not give, with the same rules (a word's text px = truth 2 inside its polygon; found
   when half or more are called text): dev ditto TARGET words by fold, scale, style (pair, quote, other) and tiny tick
   pairs (pair, 30 text px or less); negatives by type (share of the mark's ink called text, marks with half or more).
   Outputs OUT_DIR/summary.json and summary.txt.
"""
import json, os, sys, subprocess, collections
sys.dont_write_bytecode = True
import numpy as np, cv2

TF = os.path.join('bench_2026-11-26', 'text_fix')
SETS = dict(block=os.path.join(TF, 'dev_block', 'truth'), ditto=os.path.join(TF, 'dev_ditto', 'truth'),
            neg=os.path.join(TF, 'dev_ditto', 'negatives'), t17=os.path.join('bench_2026-11-25', 'text_v1', 'truth'))
ST = os.path.join('bench_2026-11-25', 'text_v1', 'code', 'score_text.py')
BFOLD_A = {'3', '54A', '30', '26A', '74', '49'}; BFOLD_B = {'12', '19', '64A', '60B', '93A', '48'}
DFOLD_A = {'44', '2', '3', '54A', '30', '60B', '74', '90', '48'}
SEALED = {'6', '9', '52', '56', '58', '63', '35', '38', '41', '66', '71', '76', '84', '88', '46', '92'}
TAB = json.load(open('scale_table.json'))


def fold(setname, plate):
    if setname == 'block': return 'A' if plate in BFOLD_A else ('B' if plate in BFOLD_B else '?')
    return 'A' if plate in DFOLD_A else 'B'


def ft_of(c): return int(c.get('scale_ft_per_inch') or TAB[c['plate']]['ft_per_inch'])


def run_st(out, name, pat, codes, sets):
    res = {}
    for nm in sets:
        tdir = SETS[nm]; crops = json.load(open(os.path.join(tdir, 'crops.json')))
        ids = sorted(k for k in crops if os.path.exists(os.path.join(tdir, f'{k}_mask.png')))
        assert not any(crops[k]['plate'] in SEALED for k in ids)
        groups = collections.OrderedDict()
        for k in ids:
            groups.setdefault('fold' + fold(nm, crops[k]['plate']), []).append(k)
            groups.setdefault(f'ft{ft_of(crops[k])}', []).append(k)
            groups.setdefault(f"fold{fold(nm, crops[k]['plate'])}_ft{ft_of(crops[k])}", []).append(k)
        jp = os.path.join(out, f'{nm}__{name}.json')
        cmd = [sys.executable, '-B', ST, pat, '--codes', codes, '--truth', tdir, '--quiet', '--out', jp]
        for g, v in groups.items(): cmd += ['--group', f'{g}={",".join(v)}']
        r = subprocess.run(cmd, capture_output=True, text=True)
        open(os.path.join(out, f'{nm}__{name}.txt'), 'w', encoding='utf8').write(' '.join(cmd) + '\n' + r.stdout + r.stderr)
        if r.returncode: print(r.stderr[-2000:]); raise SystemExit(f'score_text failed for {name} {nm}')
        res[nm] = json.load(open(jp))
    return res


def poly_fill(shape, poly, off):
    m = np.zeros(shape, np.uint8); cv2.fillPoly(m, [np.round(np.array(poly, float) - off).astype(np.int32)], 1); return m > 0


def words_scored(setname, pat, codes):
    """per word of the ditto truth (targets) and negatives: n (text px, or ink px for a negative mark), f (called text)"""
    tdir = SETS[setname]; crops = json.load(open(os.path.join(tdir, 'crops.json'))); tc = [int(v) for v in codes.split(',')]
    cache = {}; out = []
    for k in sorted(crops, key=lambda k: crops[k]['plate']):
        mp = os.path.join(tdir, f'{k}_mask.png')
        if not os.path.exists(mp): continue
        c = crops[k]; t = cv2.imread(mp, 0); x0, y0, x1, y1 = c['win']; p = pat.replace('{plate}', c['plate'])
        if p not in cache: cache.clear(); cache[p] = cv2.imread(p, cv2.IMREAD_UNCHANGED)
        pred = np.isin(cache[p][y0:y1, x0:x1], tc)
        for wd in json.load(open(os.path.join(tdir, f'{k}_words.json'), encoding='utf8'))['words']:
            if not wd.get('poly'): continue
            pm = poly_fill(t.shape, wd['poly'], np.array([x0, y0]))
            if wd.get('kind') == 'negative':
                m = pm & (t == 1); out.append(dict(crop=k, id=wd['id'], kind='negative', neg=wd.get('neg_type'), n=int(m.sum()), f=int((m & pred).sum()), plate=c['plate'], ft=ft_of(c)))
                continue
            if not wd.get('target'): continue
            m = pm & (t == 2)
            if not m.any(): continue
            out.append(dict(crop=k, id=wd['id'], kind=wd['kind'], style=wd.get('style', ''), n=int(m.sum()), f=int((m & pred).sum()), plate=c['plate'], ft=ft_of(c),
                            fold=fold(setname, c['plate'])))
    return out


def rec(ws):
    n = sum(w['n'] for w in ws); f = sum(w['f'] for w in ws)
    return dict(words=len(ws), px=round(f / max(1, n), 3), found=int(sum(w['f'] >= 0.5 * w['n'] for w in ws if w['n'])))


def main():
    a = sys.argv[1:]; sets = list(SETS)
    if '--sets' in a: i = a.index('--sets'); sets = a[i + 1].split(','); a = a[:i] + a[i + 2:]
    out = a[0]; os.makedirs(out, exist_ok=True); meths = collections.OrderedDict()
    for s in a[1:]:
        n, v = s.split('=', 1)
        if ':' in v and v.rsplit(':', 1)[1].replace(',', '').isdigit(): pat, codes = v.rsplit(':', 1)
        else: pat, codes = v, '2,3'
        meths[n] = (pat, codes)
    S = collections.OrderedDict(); L = []
    def p(s=''): L.append(s); print(s, flush=True)
    for name, (pat, codes) in meths.items():
        res = run_st(out, name, pat, codes, sets); r = S.setdefault(name, collections.OrderedDict())
        for nm, d in res.items():
            r[nm] = {g: dict(P=v['pix']['precision'], R=v['pix']['recall'], F1=v['pix']['f1'], ntct=v['nontext_called_text']['share'], fp=v['pix']['fp'],
                             by_kind={k: dict(recall=x['recall'], found=x['words_found'], words=x['words']) for k, x in v['by_kind'].items()})
                     for g, v in d['pools'].items() if not g.startswith('plate_')}
            r[nm]['_crops'] = {k: dict(F1=v['pix']['f1'], block=v['by_kind'].get('block')) for k, v in d['crops'].items()}
        if 'ditto' in sets:
            W = words_scored('ditto', pat, codes); g = collections.OrderedDict()
            g['all'] = rec(W)
            for f in ('A', 'B'): g[f'fold {f}'] = rec([w for w in W if w['fold'] == f])
            for ft in (100, 200, 400): g[f'{ft} ft'] = rec([w for w in W if w['ft'] == ft])
            for f in ('A', 'B'):
                for ft in (100, 200, 400): g[f'fold {f} {ft} ft'] = rec([w for w in W if w['fold'] == f and w['ft'] == ft])
            for st in ('pair', 'quote', 'other'): g[f'style {st}'] = rec([w for w in W if w['style'] == st])
            g['tiny tick pairs'] = rec([w for w in W if w['style'] == 'pair' and w['n'] <= 30])
            for ft in (100, 200, 400):
                for st in ('pair', 'quote', 'other'):
                    x = rec([w for w in W if w['ft'] == ft and w['style'] == st])
                    if x['words']: g[f'{ft} ft {st}'] = x
            r['ditto_targets'] = g; r['_ditto_words'] = W
        if 'neg' in sets:
            W = words_scored('neg', pat, codes); g = collections.OrderedDict()
            for t in (None, 'rail_tick', 'dash', 'hook', 'line_end'):
                v = [w for w in W if t is None or w['neg'] == t]
                g[t or 'all'] = dict(marks=len(v), share=round(sum(w['f'] for w in v) / max(1, sum(w['n'] for w in v)), 4), hit=int(sum(w['f'] >= 0.5 * w['n'] for w in v if w['n'])))
            r['neg_types'] = g; r['_neg_words'] = W
    # tables
    names = list(S)
    def row(label, fn):
        vals = []
        for n in names:
            try: vals.append(fn(S[n]))
            except (KeyError, TypeError): vals.append('-')
        p(f'  {label:34s} ' + ' | '.join(f'{v:>22s}' for v in vals))
    p('MEASURED. Text = the codes given per method. Methods: ' + ', '.join(f'{n} = {meths[n][0]} codes {meths[n][1]}' for n in names))
    p(f"  {'':34s} " + ' | '.join(f'{n:>22s}' for n in names))
    kb = lambda r, s, g, k: f"{r[s][g]['by_kind'][k]['recall']:.3f} ({r[s][g]['by_kind'][k]['found']}/{r[s][g]['by_kind'][k]['words']})"
    pr = lambda r, s, g: f"{r[s][g]['F1']:.4f} / {r[s][g]['ntct']:.4f}"
    if 'block' in sets:
        p('DEV BLOCK TRUTH (45 crops): block recall px (words found); then in-scope F1 / non-text ink called text')
        for g in ('ALL', 'foldA', 'foldB', 'ft100', 'ft200', 'ft400', 'foldA_ft100', 'foldA_ft200', 'foldA_ft400', 'foldB_ft100', 'foldB_ft200', 'foldB_ft400'):
            row(f'block {g}', lambda r, g=g: kb(r, 'block', g, 'block'))
        for g in ('ALL', 'foldA', 'foldB'): row(f'F1 / ntct {g}', lambda r, g=g: pr(r, 'block', g))
    if 't17' in sets:
        p('T1-T7 (truth v2; IN-SAMPLE for finder3\'s combiner): F1 / non-text ink called text; recall by kind')
        row('F1 / ntct ALL', lambda r: pr(r, 't17', 'ALL'))
        row('P', lambda r: f"{r['t17']['ALL']['P']:.4f}"); row('R', lambda r: f"{r['t17']['ALL']['R']:.4f}")
        for k in ('block', 'street', 'ditto', 'owner', 'house', 'lot', 'lotdim', 'story', 'pipe', 'sewer', 'bldg', 'other', 'adjoining sheet', 'railroad lettering'):
            row(k, lambda r, k=k: kb(r, 't17', 'ALL', k))
    if 'ditto' in sets:
        p('DEV DITTO TRUTH (51 crops, 200 target words): ditto recall px (words found)')
        for g in S[names[0]]['ditto_targets']: row(g, lambda r, g=g: f"{r['ditto_targets'][g]['px']:.3f} ({r['ditto_targets'][g]['found']}/{r['ditto_targets'][g]['words']})")
        for g in ('ALL', 'foldA', 'foldB'): row(f'in-scope F1 / ntct {g}', lambda r, g=g: pr(r, 'ditto', g))
    if 'neg' in sets:
        p('DITTO NEGATIVES (73 marks): share of mark ink called text (marks with half or more)')
        for g in S[names[0]]['neg_types']: row(g, lambda r, g=g: f"{r['neg_types'][g]['share']:.4f} ({r['neg_types'][g]['hit']}/{r['neg_types'][g]['marks']})")
    json.dump(S, open(os.path.join(out, 'summary.json'), 'w', encoding='utf8', newline='\n'), indent=1)
    open(os.path.join(out, 'summary.txt'), 'w', encoding='utf8', newline='\n').write('\n'.join(L) + '\n')


if __name__ == '__main__':
    main()
