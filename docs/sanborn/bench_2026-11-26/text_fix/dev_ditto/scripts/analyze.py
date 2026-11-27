"""Ditto recall by method, scale, style and size; what codes the finders give ditto ink; negatives by type
(dev_ditto, 26 Nov 2026). Uses the same word rule as score_text.py (text px = truth 2 inside the word's poly; a word is
found when half or more of its text px are called text) and checks its totals against score_text.py's json.

    cd data/sanborn; python -B bench_2026-11-26/text_fix/dev_ditto/scripts/analyze.py
Writes dev_ditto/scores/summary.json and summary.txt."""
import json, os, sys, collections
sys.dont_write_bytecode = True
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); DD = os.path.normpath(os.path.join(HERE, '..'))
M = dict(bin8=(8,), finder2=(2, 3), finder3=(2, 3))
CODE = {0: 'paper', 1: 'line', 2: 'text sure', 3: 'text by context', 4: 'shared', 5: 'other ink'}


def poly(shape, p, off):
    m = np.zeros(shape, np.uint8); cv2.fillPoly(m, [np.round(np.array(p, float) - off).astype(np.int32)], 1); return m > 0


def words(TD):
    C = json.load(open(os.path.join(TD, 'crops.json'))); out = []
    for cid in sorted(C):
        f = os.path.join(TD, f'{cid}_words.json')
        if not os.path.exists(f): continue
        c = C[cid]; T = cv2.imread(os.path.join(TD, f'{cid}_mask.png'), 0); X0, Y0 = c['win'][:2]
        preds = {m: cv2.imread(os.path.join(DD, 'runs', 'cut', m, f'{cid}.png'), cv2.IMREAD_UNCHANGED) for m in M}
        for w in json.load(open(f))['words']:
            if not (w['target'] or w['kind'] == 'negative'): continue
            pm = poly(T.shape, w['poly'], [X0, Y0])
            sel = pm & ((T == 2) if w['kind'] != 'negative' else (T == 1))
            n = int(sel.sum()); r = dict(crop=cid, id=w['id'], plate=c['plate'], scale=c['scale_ft_per_inch'], kind=w['kind'], style=w.get('style', ''),
                                         neg_type=c.get('neg_type', ''), unsure='unsure' in w['flags'], px=n, aabb=w['aabb'])
            for m, P in preds.items():
                r[m] = int((sel & np.isin(P, M[m])).sum())
                if m != 'bin8': r[m + '_codes'] = {CODE[int(v)]: int(((P == v) & sel).sum()) for v in np.unique(P[sel])}
            out.append(r)
    return out


def summ(rows, m, neg=False):
    n = sum(r['px'] for r in rows); f = sum(r[m] for r in rows); wf = sum(r[m] >= 0.5 * r['px'] for r in rows if r['px'])
    return dict(words=len(rows), px=n, found_px=f, recall_px=round(f / max(1, n), 3), words_found=wf, words_share=round(wf / max(1, len(rows)), 3)) if not neg else \
        dict(marks=len(rows), ink_px=n, called_text_px=f, share_px=round(f / max(1, n), 3), marks_called_text=wf, marks_share=round(wf / max(1, len(rows)), 3))


def main():
    R = words(os.path.join(DD, 'truth')); N = words(os.path.join(DD, 'negatives'))
    out = dict(ditto={}, negatives={}, codes={}, per_word=R, per_negative=N)
    groups = collections.OrderedDict()
    groups['ALL'] = R
    for s in (100, 200, 400): groups[f'{s} ft'] = [r for r in R if r['scale'] == s]
    for st in ('pair', 'quote', 'other'): groups[f'style {st}'] = [r for r in R if r['style'] == st]
    groups['tiny tick pair (pair, 30 px or less)'] = [r for r in R if r['style'] == 'pair' and r['px'] <= 30]
    groups['larger pair (over 30 px)'] = [r for r in R if r['style'] == 'pair' and r['px'] > 30]
    groups['sure'] = [r for r in R if not r['unsure']]; groups['unsure'] = [r for r in R if r['unsure']]
    for s in (100, 200, 400):
        for st in ('pair', 'quote', 'other'): groups[f'{s} ft {st}'] = [r for r in R if r['scale'] == s and r['style'] == st]
    for g, rows in groups.items():
        if rows: out['ditto'][g] = {m: summ(rows, m) for m in M}
    ng = collections.OrderedDict(); ng['ALL'] = N
    for t in ('rail_tick', 'dash', 'line_end', 'hook'): ng[t] = [r for r in N if r['neg_type'] == t]
    for g, rows in ng.items():
        if rows: out['negatives'][g] = {m: summ(rows, m, True) for m in M}
    for m in ('finder2', 'finder3'):
        for g in ('ALL', '100 ft', '200 ft', '400 ft', 'style pair', 'style quote', 'style other'):
            cc = collections.Counter()
            for r in groups[g]: cc.update(r[m + '_codes'])
            out['codes'][f'{m} {g}'] = dict(cc)
        cc = collections.Counter()
        for r in N: cc.update(r[m + '_codes'])
        out['codes'][f'{m} negatives'] = dict(cc)
    # cross-check against score_text.py
    chk = {}
    for m in M:
        s = json.load(open(os.path.join(DD, 'scores', f'ditto_{m}.json')))['pools']['ALL']['by_kind']['ditto']
        chk[m] = dict(score_text=[s['found_px'], s['text_px'], s['words_found'], s['words']], here=[out['ditto']['ALL'][m]['found_px'], out['ditto']['ALL'][m]['px'], out['ditto']['ALL'][m]['words_found'], out['ditto']['ALL'][m]['words']])
    out['crosscheck'] = chk
    json.dump(out, open(os.path.join(DD, 'scores', 'summary.json'), 'w'), indent=1)
    L = ['Ditto recall (MEASURED). px = ditto text px found / all; words = words with half or more of their px found.', '']
    L.append(f"{'group':42s} {'words':>5s} {'px':>6s} | " + ' | '.join(f'{m:^22s}' for m in M))
    for g, d in out['ditto'].items():
        a = d['bin8']; L.append(f"{g:42s} {a['words']:5d} {a['px']:6d} | " + ' | '.join(f"px {d[m]['recall_px']:.3f} w {d[m]['words_found']:3d} ({d[m]['words_share']:.3f})" for m in M))
    L += ['', 'Negatives (MEASURED): share of the mark ink called text, and marks with half or more of their ink called text.']
    for g, d in out['negatives'].items():
        a = d['bin8']; L.append(f"{g:12s} marks {a['marks']:3d} ink {a['ink_px']:6d} | " + ' | '.join(f"{m}: px {d[m]['share_px']:.3f} marks {d[m]['marks_called_text']:2d}" for m in M))
    L += ['', 'Finder codes on ditto text px and on negative mark ink (MEASURED):']
    for k, v in out['codes'].items():
        t = sum(v.values()); L.append(f"{k:28s} " + '  '.join(f"{c} {n} ({n / max(1, t):.2f})" for c, n in sorted(v.items(), key=lambda x: -x[1])))
    L += ['', f"cross-check against score_text.py (found px, text px, words found, words): {chk}"]
    open(os.path.join(DD, 'scores', 'summary.txt'), 'w').write('\n'.join(L) + '\n'); print('\n'.join(L))


if __name__ == '__main__':
    main()
