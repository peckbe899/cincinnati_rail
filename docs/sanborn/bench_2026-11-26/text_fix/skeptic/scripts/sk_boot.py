"""sk_boot.py (skeptic): 95% ranges again, with resampling units the gate did not use, and which verdicts could flip.

    cd data/sanborn
    python -B bench_2026-11-26/text_fix/skeptic/scripts/sk_boot.py SK.json OUT.json [--draws 4000]

Targeted sets (block 52, ditto 151 target words), finder3 (f3) and finder4 (f4), always paired:
  word     words drawn with replacement (the gate's main range)
  crop     crops drawn with replacement (the gate's second range)
  plate    plates drawn with replacement, all words of a drawn plate kept (words of one plate share print, scale and
           the finder's settings, so they are not independent; this is the honest unit with 16 plates)
  plate2   two stages: plates drawn, then words drawn within each drawn plate
  exact    Clopper-Pearson range of the words-found share (binomial, words independent)
For each: the 95% range of pixel recall and words-found share, the paired gain, and the share of draws in which f4
meets the target (block: pixel recall >= 0.95 and words >= 95%; ditto: >= 0.90 and >= 90%).
Full crops: tiles of 100 px (the gate's unit) and of 250 px (fewer, bigger tiles: nearby pixels share objects),
stratified by crop, paired: F1, non-text share, street pixel recall, straight-run proxy (my border rule: outside the
crop is paper); share of draws in which each sub-test passes. Street words: Clopper-Pearson of 9/9.
Seed numpy default_rng(271127).
"""
import json, sys
sys.dont_write_bytecode = True
import numpy as np
from scipy.stats import beta


def cp(k, n, a=0.05):
    lo = 0.0 if k == 0 else beta.ppf(a / 2, k, n - k + 1); hi = 1.0 if k == n else beta.ppf(1 - a / 2, k + 1, n - k)
    return [round(float(lo), 4), round(float(hi), 4)]


def ci(x): return [round(float(v), 4) for v in np.percentile(x, [2.5, 97.5])]


def main():
    a = sys.argv[1:]; D = int(a[a.index('--draws') + 1]) if '--draws' in a else 4000
    Z = json.load(open(a[0], encoding='utf8')); rng = np.random.default_rng(271127); O = dict(draws=D, seed=271127)
    for kind, tgt in (('block', 0.95), ('ditto', 0.90)):
        W = [w for w in Z['words'] if w['target'] and w['kind'] == kind and w['n'] > 0]
        n = np.array([w['n'] for w in W], float); f3 = np.array([w['f_f3'] for w in W], float); f4 = np.array([w['f_f4'] for w in W], float)
        plate = np.array([w['plate'] for w in W]); crop = np.array([w['crop'] for w in W])
        res = dict(words=len(W), f3=dict(pixel_recall=round(f3.sum() / n.sum(), 4), found=int((f3 >= 0.5 * n).sum())),
                   f4=dict(pixel_recall=round(f4.sum() / n.sum(), 4), found=int((f4 >= 0.5 * n).sum())))
        k4 = res['f4']['found']; res['exact_word_share_f4'] = cp(k4, len(W)); res['exact_word_share_f3'] = cp(res['f3']['found'], len(W))
        res['words_needed_for_target'] = int(np.ceil(tgt * len(W) - 1e-9)); res['more_words_needed'] = res['words_needed_for_target'] - k4

        def draw_idx(unit):
            if unit == 'word': return [rng.integers(0, len(W), len(W)) for _ in range(D)]
            groups = {}
            for i, g in enumerate(crop if unit == 'crop' else plate): groups.setdefault(g, []).append(i)
            keys = list(groups); out = []
            for _ in range(D):
                pick = rng.integers(0, len(keys), len(keys))
                if unit == 'plate2': idx = np.concatenate([np.array(groups[keys[j]])[rng.integers(0, len(groups[keys[j]]), len(groups[keys[j]]))] for j in pick])
                else: idx = np.concatenate([groups[keys[j]] for j in pick])
                out.append(idx)
            return out
        res['n_plates'] = len(set(plate)); res['n_crops'] = len(set(crop))
        for unit in ('word', 'crop', 'plate', 'plate2'):
            I = draw_idx(unit)
            p3 = np.array([f3[i].sum() / n[i].sum() for i in I]); p4 = np.array([f4[i].sum() / n[i].sum() for i in I])
            w3 = np.array([(f3[i] >= 0.5 * n[i]).mean() for i in I]); w4 = np.array([(f4[i] >= 0.5 * n[i]).mean() for i in I])
            res[unit] = dict(f4_pixel_recall=ci(p4), f4_word_share=ci(w4), f3_pixel_recall=ci(p3), gain_pixels=ci(p4 - p3), gain_words=ci(w4 - w3),
                             share_draws_f4_meets_target=round(float(((p4 >= tgt) & (w4 >= tgt)).mean()), 4),
                             share_draws_f4_pixels_meet=round(float((p4 >= tgt).mean()), 4), share_draws_f4_words_meet=round(float((w4 >= tgt).mean()), 4),
                             share_draws_gain_le_0=round(float((p4 - p3 <= 0).mean()), 4))
        # by scale (plate bootstrap within scale)
        for ft in (100, 200, 400):
            sel = np.array([w['ft'] == ft for w in W])
            if not sel.any(): continue
            idx = np.nonzero(sel)[0]; groups = {}
            for i in idx: groups.setdefault(plate[i], []).append(i)
            keys = list(groups); p4l = []; w4l = []
            for _ in range(D):
                pick = rng.integers(0, len(keys), len(keys)); ii = np.concatenate([groups[keys[j]] for j in pick])
                p4l.append(f4[ii].sum() / n[ii].sum()); w4l.append((f4[ii] >= 0.5 * n[ii]).mean())
            res[f'{ft}ft'] = dict(words=int(sel.sum()), plates=len(keys), f4_pixel_recall=round(f4[sel].sum() / n[sel].sum(), 4),
                                  f4_found=int((f4[sel] >= 0.5 * n[sel]).sum()), plate_boot_f4_pixel=ci(p4l), plate_boot_f4_words=ci(w4l))
        # leave one plate out: how far one plate moves the headline
        lo = {}
        for p in sorted(set(plate), key=lambda s: (len(s), s)):
            m = plate != p; lo[p] = dict(f4_pixel_recall=round(f4[m].sum() / n[m].sum(), 4), f4_word_share=round(float((f4[m] >= 0.5 * n[m]).mean()), 4), words_left_out=int((~m).sum()))
        res['leave_one_plate_out'] = lo
        res['leave_one_plate_out_range'] = dict(pixel=[min(v['f4_pixel_recall'] for v in lo.values()), max(v['f4_pixel_recall'] for v in lo.values())],
                                                words=[min(v['f4_word_share'] for v in lo.values()), max(v['f4_word_share'] for v in lo.values())])
        # misses by code (f4)
        miss = [w for w in W if w['f_f4'] < 0.9 * w['n']]; codes = {}
        for w in miss:
            for c, v in w['miss_codes_f4'].items(): codes[c] = codes.get(c, 0) + v
        res['f4_missed_or_partial'] = dict(words=len(miss), missed=int(sum(1 for w in W if w['f_f4'] < 0.5 * w['n'])), missed_px_by_code=codes,
                                           missed_px=int(sum(codes.values())))
        O[kind] = res
    # full crops
    T = Z['tiles']; full = {}
    for size in (100, 250):
        rows = {}
        for t in T:
            key = (t['crop'], t['tx'] // size, t['ty'] // size); r = rows.setdefault(key, dict(crop=t['crop'], t1=0, sn=0, st=0, f3=dict(tp=0, fp=0, fn=0, sf=0, stf=0), f4=dict(tp=0, fp=0, fn=0, sf=0, stf=0)))
            for q in ('t1', 'sn', 'st'): r[q] += t[q]
            for m in ('f3', 'f4'):
                for q in ('tp', 'fp', 'fn', 'sf', 'stf'): r[m][q] += t[m][q]
        R = list(rows.values()); crops = sorted({r['crop'] for r in R})
        arr = lambda f: np.array([f(r) for r in R], float)
        V = {m: {q: arr(lambda r, m=m, q=q: r[m][q]) for q in ('tp', 'fp', 'fn', 'sf', 'stf')} for m in ('f3', 'f4')}
        t1 = arr(lambda r: r['t1']); sn = arr(lambda r: r['sn'])
        cidx = {c: np.array([i for i, r in enumerate(R) if r['crop'] == c]) for c in crops}
        I = np.array([np.concatenate([cidx[c][rng.integers(0, len(cidx[c]), len(cidx[c]))] for c in crops]) for _ in range(D)])
        def met(m):
            tp, fp, fn, sf, stf = (V[m][q][I].sum(1) for q in ('tp', 'fp', 'fn', 'sf', 'stf'))
            P = tp / np.maximum(1, tp + fp); Rr = tp / np.maximum(1, tp + fn)
            return dict(F1=2 * P * Rr / np.maximum(1e-9, P + Rr), nontext=fp / np.maximum(1, t1[I].sum(1)), street=sf / np.maximum(1, sn[I].sum(1)), straight=stf)
        a3, a4 = met('f3'), met('f4')
        full[f'tile{size}'] = dict(tiles=len(R), f4={k: ci(v) for k, v in a4.items()}, diff={k: ci(a4[k] - a3[k]) for k in a4},
                                   share_draws_pass=dict(F1=round(float((a4['F1'] >= a3['F1'] - 0.002).mean()), 4),
                                                         nontext=round(float((a4['nontext'] - a3['nontext'] <= 0.003).mean()), 4),
                                                         street=round(float((a4['street'] >= 0.95).mean()), 4),
                                                         straight=round(float((a4['straight'] <= a3['straight']).mean()), 4)))
    full['street_words_exact_9of9'] = cp(9, 9)
    O['full'] = full
    json.dump(O, open(a[1], 'w'), indent=1)
    for kind in ('block', 'ditto'):
        r = O[kind]
        print(f"{kind}: f4 {r['f4']}  exact words {r['exact_word_share_f4']}  more words needed {r['more_words_needed']}  plates {r['n_plates']} crops {r['n_crops']}")
        for u in ('word', 'crop', 'plate', 'plate2'):
            print(f"   {u:6s} px {r[u]['f4_pixel_recall']} words {r[u]['f4_word_share']} gain px {r[u]['gain_pixels']} meets target {r[u]['share_draws_f4_meets_target']} "
                  f"(px {r[u]['share_draws_f4_pixels_meet']}, words {r[u]['share_draws_f4_words_meet']})")
        for ft in (100, 200, 400):
            if f'{ft}ft' in r: print(f'   {ft} ft', r[f'{ft}ft'])
        print('   leave one plate out', r['leave_one_plate_out_range'], ' misses', r['f4_missed_or_partial'])
    for k, v in O['full'].items(): print('full', k, v)


if __name__ == '__main__':
    main()
