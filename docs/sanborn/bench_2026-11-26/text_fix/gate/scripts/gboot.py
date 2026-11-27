"""gboot.py (final gate, 27 Nov 2026): gate numbers, breakdowns and 95% ranges from gscore.py's rows.

    cd data/sanborn
    python -B bench_2026-11-26/text_fix/gate/scripts/gboot.py SCORES.npz OUT.json [--a finder3 --b finder4] [--draws 2000]

Targeted sets (target words only, as target_recall.py): block numbers (52) and ditto marks (151).
  pixel recall = found text px / text px over the words; words found = share of words with found >= half.
  95% range: by-word bootstrap (draws of the words with replacement, the same draws for both methods, so the
  finder4 - finder3 difference is paired). Also a by-crop bootstrap (dittos in one window are not independent).
Full crops (SA-F1, SB-F1): P, R, F1, non-text ink called text, street-name recall (pixels, words), straight-run proxy.
  95% range: 100 px tile bootstrap (tiles drawn with replacement within each crop, paired).
Seeded (numpy default_rng(20261127)).
"""
import json, sys
sys.dont_write_bytecode = True
import numpy as np


def pr(lo_hi): return [round(float(v), 4) for v in lo_hi]


def ci(x): return pr(np.percentile(x, [2.5, 97.5]))


def f1(tp, fp, fn):
    P = tp / np.maximum(1, tp + fp); R = tp / np.maximum(1, tp + fn)
    return 2 * P * R / np.maximum(1e-9, P + R), P, R


def main():
    a = sys.argv[1:]
    A = a[a.index('--a') + 1] if '--a' in a else 'finder3'; B = a[a.index('--b') + 1] if '--b' in a else 'finder4'
    D = int(a[a.index('--draws') + 1]) if '--draws' in a else 2000
    Z = np.load(a[0]); pix = json.loads(str(Z['pix'])); words = json.loads(str(Z['words'])); tiles = json.loads(str(Z['tiles']))
    rng = np.random.default_rng(20261127); O = dict(methods=[A, B], draws=D, seed=20261127)

    # ---------------- targeted sets
    for kind in ('block', 'ditto'):
        W = {m: [w for w in words if w['method'] == m and w['target'] and w['kind'] == kind] for m in (A, B)}
        if not W[A]: continue   # a truth set without target words (H1-H4)
        key = [(w['crop'], w['id']) for w in W[A]]; assert key == [(w['crop'], w['id']) for w in W[B]]
        n = np.array([w['n'] for w in W[A]], float); fa = np.array([w['f'] for w in W[A]], float); fb = np.array([w['f'] for w in W[B]], float)
        meta = W[A]
        res = {}

        def stats(idx):
            return dict(words=int(len(idx)), text_px=int(n[idx].sum()),
                        **{m: dict(pixel_recall=round(float(f[idx].sum() / max(1, n[idx].sum())), 4), words_found=int((f[idx] >= 0.5 * n[idx]).sum()),
                                   word_share=round(float((f[idx] >= 0.5 * n[idx]).mean()) if len(idx) else 0, 4)) for m, f in ((A, fa), (B, fb))})
        allidx = np.arange(len(n)); res['all'] = stats(allidx)
        for ft in (100, 200, 400):
            idx = np.array([i for i, w in enumerate(meta) if w['ft'] == ft], int)
            if len(idx): res[f'{ft}ft'] = stats(idx)
        for pl in sorted({w['plate'] for w in meta}, key=lambda s: (len(s), s)):
            idx = np.array([i for i, w in enumerate(meta) if w['plate'] == pl], int); res[f'plate_{pl}'] = stats(idx)
        # by-word bootstrap, paired
        bi = rng.integers(0, len(n), (D, len(n)))
        pra = fa[bi].sum(1) / n[bi].sum(1); prb = fb[bi].sum(1) / n[bi].sum(1)
        wa = (fa[bi] >= 0.5 * n[bi]).mean(1); wb = (fb[bi] >= 0.5 * n[bi]).mean(1)
        res['boot_word'] = {A: dict(pixel_recall=ci(pra), word_share=ci(wa)), B: dict(pixel_recall=ci(prb), word_share=ci(wb)),
                            'diff_B_minus_A': dict(pixel_recall=ci(prb - pra), word_share=ci(wb - wa)),
                            'share_of_draws_B_meets_target': None}
        tgt = 0.95 if kind == 'block' else 0.90
        res['boot_word']['share_of_draws_B_meets_target'] = round(float(((prb >= tgt) & (wb >= tgt)).mean()), 4)
        # by-scale bootstrap (by word, within the scale)
        for ft in (100, 200, 400):
            idx = np.array([i for i, w in enumerate(meta) if w['ft'] == ft], int)
            if not len(idx): continue
            bj = idx[rng.integers(0, len(idx), (D, len(idx)))]
            pa_ = fa[bj].sum(1) / n[bj].sum(1); pb_ = fb[bj].sum(1) / n[bj].sum(1)
            res[f'{ft}ft']['boot_word'] = {A: ci(pa_), B: ci(pb_), 'diff': ci(pb_ - pa_),
                                          B + '_word_share': ci((fb[bj] >= 0.5 * n[bj]).mean(1))}
        # by-crop bootstrap (sensitivity)
        cr = sorted({w['crop'] for w in meta}); ci_ = {c: np.array([i for i, w in enumerate(meta) if w['crop'] == c]) for c in cr}
        pa_l, pb_l, wb_l = [], [], []
        for _ in range(D):
            pick = rng.integers(0, len(cr), len(cr)); idx = np.concatenate([ci_[cr[j]] for j in pick])
            pa_l.append(fa[idx].sum() / n[idx].sum()); pb_l.append(fb[idx].sum() / n[idx].sum()); wb_l.append((fb[idx] >= 0.5 * n[idx]).mean())
        res['boot_crop'] = dict(crops=len(cr), **{A: ci(pa_l), B: ci(pb_l), B + '_word_share': ci(wb_l), 'diff': ci(np.array(pb_l) - np.array(pa_l))})
        # misses
        res['missed_by_B'] = [dict(crop=w['crop'], id=w['id'], plate=w['plate'], ft=w['ft'], reading=w['reading'], n=int(w['n']), fB=int(fb[i]), fA=int(fa[i]),
                                   aabb=w['aabb']) for i, w in enumerate(meta) if fb[i] < 0.5 * n[i]]
        res['partial_by_B'] = [dict(crop=w['crop'], id=w['id'], plate=w['plate'], ft=w['ft'], reading=w['reading'], n=int(w['n']), fB=int(fb[i]), fA=int(fa[i]),
                                    recall_B=round(fb[i] / n[i], 3), aabb=w['aabb']) for i, w in enumerate(meta) if 0.5 * n[i] <= fb[i] < 0.9 * n[i]]
        res['lost_vs_A'] = [dict(crop=w['crop'], id=w['id'], n=int(w['n']), fA=int(fa[i]), fB=int(fb[i])) for i, w in enumerate(meta) if fb[i] < fa[i]]
        # non-text ink called text inside the scopes of this target kind
        rows = {m: [r for r in pix if r['method'] == m and r['ctype'] == 'targeted' and r['target'] == kind] for m in (A, B)}
        res['scopes'] = {m: dict(nontext_px=sum(r['t1'] for r in rows[m]), called_text=sum(r['fp'] for r in rows[m]),
                                 share=round(sum(r['fp'] for r in rows[m]) / max(1, sum(r['t1'] for r in rows[m])), 5),
                                 inscope_F1=round(float(f1(sum(r['tp'] for r in rows[m]), sum(r['fp'] for r in rows[m]), sum(r['fn'] for r in rows[m]))[0]), 4))
                         for m in (A, B)}
        for ft in (100, 200, 400):
            for m in (A, B):
                rr = [r for r in rows[m] if r['ft'] == ft]
                if rr: res['scopes'][m][f'share_{ft}ft'] = round(sum(r['fp'] for r in rr) / max(1, sum(r['t1'] for r in rr)), 5)
        O[kind] = res

    # ---------------- full crops
    full = {}
    crops_full = sorted({r['crop'] for r in pix if r['ctype'] == 'full'})
    for scope in crops_full + ['both']:
        cl = crops_full if scope == 'both' else [scope]
        r = {}
        for m in (A, B):
            R = [x for x in pix if x['method'] == m and x['crop'] in cl]
            tp, fp, fn, t1 = (sum(x[k] for x in R) for k in ('tp', 'fp', 'fn', 't1'))
            F, P, Rr = f1(tp, fp, fn)
            Wd = [w for w in words if w['method'] == m and w['crop'] in cl]
            kinds = {}
            for w in Wd:
                k = kinds.setdefault(w['kind'], dict(words=0, text_px=0, found_px=0, words_found=0))
                k['words'] += 1; k['text_px'] += w['n']; k['found_px'] += w['f']; k['words_found'] += int(w['f'] >= 0.5 * w['n'])
            for k in kinds.values(): k['recall'] = round(k['found_px'] / max(1, k['text_px']), 4)
            T = [t for t in tiles if t['method'] == m and t['crop'] in cl]
            r[m] = dict(tp=tp, fp=fp, fn=fn, nontext_px=t1, P=round(float(P), 4), R=round(float(Rr), 4), F1=round(float(F), 4), nontext_share=round(fp / max(1, t1), 5),
                        street_pixel_recall=kinds.get('street', {}).get('recall'), street_words=f"{kinds.get('street', {}).get('words_found')}/{kinds.get('street', {}).get('words')}",
                        straight_px=sum(t['st'] for t in T), straight_called_text=sum(t['stf'] for t in T), by_kind=dict(sorted(kinds.items())))
        # tile bootstrap, stratified by crop, paired
        TA = {c: [t for t in tiles if t['method'] == A and t['crop'] == c] for c in cl}; TB = {c: [t for t in tiles if t['method'] == B and t['crop'] == c] for c in cl}
        for c in cl: assert [(t['tx'], t['ty']) for t in TA[c]] == [(t['tx'], t['ty']) for t in TB[c]]
        arr = lambda TT, k: np.concatenate([np.array([t[k] for t in TT[c]], float) for c in cl])
        offs = np.cumsum([0] + [len(TA[c]) for c in cl])
        idx = np.concatenate([offs[j] + rng.integers(0, len(TA[c]), (D, len(TA[c]))) for j, c in enumerate(cl)], axis=1)
        bo = {}
        for m, TT in ((A, TA), (B, TB)):
            tp, fp, fn, t1, sn, sf, stf = (arr(TT, k)[idx].sum(1) for k in ('tp', 'fp', 'fn', 't1', 'sn', 'sf', 'stf'))
            bo[m] = dict(F1=f1(tp, fp, fn)[0], nontext=fp / np.maximum(1, t1), street=sf / np.maximum(1, sn), straight=stf)
        r['boot_tile'] = dict(tiles=int(idx.shape[1]), **{m: {k: ci(v) for k, v in bo[m].items()} for m in (A, B)},
                              diff_B_minus_A={k: ci(bo[B][k] - bo[A][k]) for k in bo[A]})
        r['boot_tile']['share_draws_F1_ok'] = round(float((bo[B]['F1'] >= bo[A]['F1'] - 0.002).mean()), 4)
        r['boot_tile']['share_draws_nontext_ok'] = round(float((bo[B]['nontext'] - bo[A]['nontext'] <= 0.003).mean()), 4)
        r['boot_tile']['share_draws_straight_ok'] = round(float((bo[B]['straight'] <= bo[A]['straight']).mean()), 4)
        # street words: by-word bootstrap
        Sa = [w for w in words if w['method'] == A and w['crop'] in cl and w['kind'] == 'street']; Sb = [w for w in words if w['method'] == B and w['crop'] in cl and w['kind'] == 'street']
        if Sb:
            n = np.array([w['n'] for w in Sb], float); fb_ = np.array([w['f'] for w in Sb], float); bi = rng.integers(0, len(n), (D, len(n)))
            r['street_words_boot'] = {B: dict(pixel_recall=ci(fb_[bi].sum(1) / n[bi].sum(1)), word_share=ci((fb_[bi] >= 0.5 * n[bi]).mean(1)))}
            r['street_words'] = [dict(id=w['id'], reading=w['reading'], n=w['n'], fA=wa['f'], fB=w['f']) for w, wa in zip(Sb, Sa)]
        full[scope] = r
    O['full'] = full
    # H-like whole-set (all sealed crops) pooled pixels, for reference
    for m in (A, B):
        R = [x for x in pix if x['method'] == m]
        tp, fp, fn = (sum(x[k] for x in R) for k in ('tp', 'fp', 'fn'))
        O.setdefault('all_crops_pooled', {})[m] = dict(tp=tp, fp=fp, fn=fn, F1=round(float(f1(tp, fp, fn)[0]), 4))
    json.dump(O, open(a[1], 'w', encoding='utf8', newline='\n'), indent=1)
    # print the headline
    for kind in ('block', 'ditto'):
        if kind not in O: continue
        r = O[kind]['all']; b = O[kind]['boot_word']
        print(f"{kind}: {A} {r[A]['pixel_recall']} ({r[A]['words_found']}/{r['words']})  {B} {r[B]['pixel_recall']} ({r[B]['words_found']}/{r['words']})  "
              f"95% {B} px {b[B]['pixel_recall']} words {b[B]['word_share']}  diff px {b['diff_B_minus_A']['pixel_recall']}")
        for ft in (100, 200, 400):
            if f'{ft}ft' in O[kind]:
                s = O[kind][f'{ft}ft']; print(f"   {ft} ft: {A} {s[A]['pixel_recall']} ({s[A]['words_found']}/{s['words']})  {B} {s[B]['pixel_recall']} ({s[B]['words_found']}/{s['words']})")
        print('   scopes non-text called text:', {m: O[kind]['scopes'][m]['share'] for m in (A, B)})
    for sc, r in full.items():
        print(f"full {sc}: F1 {r[A]['F1']} -> {r[B]['F1']}  nontext {r[A]['nontext_share']} -> {r[B]['nontext_share']}  street {r[A]['street_pixel_recall']} ({r[A]['street_words']}) -> "
              f"{r[B]['street_pixel_recall']} ({r[B]['street_words']})  straight {r[A]['straight_called_text']} -> {r[B]['straight_called_text']} of {r[A]['straight_px']}")
        print('    diff F1', r['boot_tile']['diff_B_minus_A']['F1'], 'diff nontext', r['boot_tile']['diff_B_minus_A']['nontext'])


if __name__ == '__main__':
    main()
