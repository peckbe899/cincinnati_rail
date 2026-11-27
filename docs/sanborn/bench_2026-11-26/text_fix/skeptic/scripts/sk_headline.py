"""sk_headline.py (skeptic): headline gate numbers from sk_score.py's rows, and a check against the gate's own files.

    cd data/sanborn
    python -B bench_2026-11-26/text_fix/skeptic/scripts/sk_headline.py SK.json OUT.json [--a f3 --b f4]

Prints, for both methods: block and ditto target recall (pixels, words found), by scale and plate; non-text called text
in the scopes; the full-crop numbers (F1, non-text share, street pixels and words, straight-run proxy); the same with
the pixel-centre fill; and compares with gate/scores/gate_verdicts.json, target_recall_*.json and boot_sealed.json.
"""
import json, sys
sys.dont_write_bytecode = True
G = 'bench_2026-11-26/text_fix/gate/scores'


def f1(tp, fp, fn):
    P = tp / max(1, tp + fp); R = tp / max(1, tp + fn); return 2 * P * R / max(1e-9, P + R), P, R


def tstats(W, m, fill='f'):
    n = sum(w['n' if fill == 'f' else 'n_sk'] for w in W); f = sum(w[f'{fill}_{m}'] for w in W)
    wf = sum(int(w[f'{fill}_{m}'] >= 0.5 * w['n' if fill == 'f' else 'n_sk']) for w in W if w['n' if fill == 'f' else 'n_sk'] > 0)
    nw = sum(1 for w in W if w['n' if fill == 'f' else 'n_sk'] > 0)
    return dict(words=nw, text_px=n, pixel_recall=round(f / max(1, n), 4), words_found=wf, word_share=round(wf / max(1, nw), 4))


def main():
    a = sys.argv[1:]; A = a[a.index('--a') + 1] if '--a' in a else 'f3'; B = a[a.index('--b') + 1] if '--b' in a else 'f4'
    Z = json.load(open(a[0], encoding='utf8')); W = Z['words']; C = Z['crops']; T = Z['tiles']
    O = {}
    for kind in ('block', 'ditto'):
        tw = [w for w in W if w['target'] and w['kind'] == kind and w['n'] > 0]
        r = {'all': {m: tstats(tw, m) for m in (A, B)}, 'all_pixel_centre_fill': {m: tstats(tw, m, 'fsk') for m in (A, B)}}
        for ft in (100, 200, 400):
            s = [w for w in tw if w['ft'] == ft]
            if s: r[f'{ft}ft'] = {m: tstats(s, m) for m in (A, B)}
        for pl in sorted({w['plate'] for w in tw}, key=lambda s: (len(s), s)):
            r[f'plate_{pl}'] = {m: tstats([w for w in tw if w['plate'] == pl], m) for m in (A, B)}
        rows = {m: [c for c in C if c['method'] == m and c['ctype'] == 'targeted' and c['target'] == kind] for m in (A, B)}
        r['scopes'] = {m: dict(nontext=sum(c['t1'] for c in rows[m]), called=sum(c['fp'] for c in rows[m]),
                               share=round(sum(c['fp'] for c in rows[m]) / max(1, sum(c['t1'] for c in rows[m])), 5),
                               F1=round(f1(*(sum(c[k] for c in rows[m]) for k in ('tp', 'fp', 'fn')))[0], 4)) for m in (A, B)}
        O[kind] = r
    full = {}
    fc = sorted({c['crop'] for c in C if c['ctype'] == 'full'})
    for sc in fc + ['both']:
        cl = fc if sc == 'both' else [sc]; r = {}
        for m in (A, B):
            R = [c for c in C if c['method'] == m and c['crop'] in cl]
            tp, fp, fn, t1 = (sum(c[k] for c in R) for k in ('tp', 'fp', 'fn', 't1'))
            F, P, Rr = f1(tp, fp, fn)
            sw = [w for w in W if w['crop'] in cl and w['kind'] == 'street' and w['n'] > 0]
            kinds = {}
            for w in W:
                if w['crop'] not in cl or w['n'] == 0: continue
                k = kinds.setdefault(w['kind'], [0, 0, 0, 0]); k[0] += 1; k[1] += w['n']; k[2] += w[f'f_{m}']; k[3] += int(w[f'f_{m}'] >= 0.5 * w['n'])
            r[m] = dict(tp=tp, fp=fp, fn=fn, P=round(P, 4), R=round(Rr, 4), F1=round(F, 4), nontext_share=round(fp / max(1, t1), 5),
                        street_pixel_recall=round(sum(w[f'f_{m}'] for w in sw) / max(1, sum(w['n'] for w in sw)), 4),
                        street_pixel_recall_centre_fill=round(sum(w[f'fsk_{m}'] for w in sw) / max(1, sum(w['n_sk'] for w in sw)), 4),
                        street_words=f"{sum(int(w[f'f_{m}'] >= 0.5 * w['n']) for w in sw)}/{len(sw)}",
                        straight_px=sum(c['straight_px'] for c in R), straight_called=sum(c['straight_called'] for c in R),
                        by_kind={k: dict(words=v[0], recall=round(v[2] / max(1, v[1]), 4), found=v[3]) for k, v in sorted(kinds.items())})
        full[sc] = r
    O['full'] = full
    O['all_crops'] = {m: dict(zip(('F1', 'P', 'R'), [round(x, 4) for x in f1(*(sum(c[k] for c in C if c['method'] == m) for k in ('tp', 'fp', 'fn')))])) for m in (A, B)}
    # compare with the gate's files
    cmp = {}
    try:
        GV = json.load(open(f'{G}/gate_verdicts.json')); GB = json.load(open(f'{G}/boot_sealed.json'))
        TRb = json.load(open(f'{G}/target_recall_finder4.json'))['targets']; TRa = json.load(open(f'{G}/target_recall_finder3.json'))['targets']
        cmp['block_px'] = (O['block']['all'][B]['pixel_recall'], GV['1_block']['pixel_recall'])
        cmp['block_words'] = (f"{O['block']['all'][B]['words_found']}/{O['block']['all'][B]['words']}", GV['1_block']['words'])
        cmp['ditto_px'] = (O['ditto']['all'][B]['pixel_recall'], GV['2_ditto']['pixel_recall'])
        cmp['ditto_words'] = (f"{O['ditto']['all'][B]['words_found']}/{O['ditto']['all'][B]['words']}", GV['2_ditto']['words'])
        for kind in ('block', 'ditto'):
            for ft in (100, 200, 400):
                k = f'{kind}_{ft}'
                if k in TRb:
                    cmp[k] = dict(mine_f4=(O[kind][f'{ft}ft'][B]['found_px'] if False else O[kind][f'{ft}ft'][B]['pixel_recall'], O[kind][f'{ft}ft'][B]['words_found']),
                                  target_recall_f4=(TRb[k]['pixel_recall'], TRb[k]['words_found']),
                                  mine_f3=(O[kind][f'{ft}ft'][A]['pixel_recall'], O[kind][f'{ft}ft'][A]['words_found']),
                                  target_recall_f3=(TRa[k]['pixel_recall'], TRa[k]['words_found']))
        g3 = GV['3_full_no_harm']
        cmp['full_F1'] = ([full['both'][A]['F1'], full['both'][B]['F1']], g3['F1'])
        cmp['full_nontext_pct'] = ([round(100 * full['both'][m]['nontext_share'], 3) for m in (A, B)], g3['nontext_points'])
        cmp['full_street'] = ([full['both'][m]['street_pixel_recall'] for m in (A, B)], g3['street_pixel_recall'])
        cmp['full_street_words'] = ([full['both'][m]['street_words'] for m in (A, B)], g3['street_words'])
        cmp['full_straight'] = ([full['both'][A]['straight_called'], full['both'][B]['straight_called'], full['both'][B]['straight_px']], g3['straight_called_text'])
        for kind in ('block', 'ditto'):
            cmp[f'{kind}_scope_nontext'] = ([O[kind]['scopes'][m]['share'] for m in (A, B)], [GB[kind]['scopes'][m]['share'] for m in ('finder3', 'finder4')])
    except Exception as e:
        cmp['error'] = repr(e)
    O['compare_with_gate'] = cmp
    json.dump(O, open(a[1], 'w', encoding='utf8', newline='\n'), indent=1)
    for kind in ('block', 'ditto'):
        print(kind, 'all', O[kind]['all'], '\n   centre fill', O[kind]['all_pixel_centre_fill'])
        for ft in (100, 200, 400):
            if f'{ft}ft' in O[kind]: print('  ', ft, {m: (v['pixel_recall'], f"{v['words_found']}/{v['words']}") for m, v in O[kind][f'{ft}ft'].items()})
        print('   scopes', O[kind]['scopes'])
    for sc, r in full.items(): print('full', sc, {m: {k: v for k, v in r[m].items() if k != 'by_kind'} for m in (A, B)})
    print('all crops', O['all_crops'])
    print('COMPARE (mine, gate):'); [print('  ', k, v) for k, v in cmp.items()]


if __name__ == '__main__':
    main()
