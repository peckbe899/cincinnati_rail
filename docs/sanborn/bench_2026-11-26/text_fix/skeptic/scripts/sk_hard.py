"""sk_hard.py (skeptic): finder3 and finder4 on the hard target words alone (sealed set), from sk_score.py's rows.

    cd data/sanborn
    python -B bench_2026-11-26/text_fix/skeptic/scripts/sk_hard.py SK.json OUT.json

Hard-case tags come from the truth only (no method output):
  block  crossed   the word touches a line (builder flag) or more than 5% of its box ink is non-text truth
         thin      median stroke width (2 x median distance-to-edge of its text px) over the figure height in the
                   lowest third of the 52 (the cut is printed)
         broken    more pieces of ink (all truth ink, text or not, 8-connected, inside the word box) than figures in
                   the reading: a figure that falls apart even with the lines that cross it
         dense     the two figures over the plate-92 grids (SB-B24, SB-B25)
         doubtful  flagged unsure or named doubtful in the README (SA-B15, SB-B24, SB-B25)
  ditto  tiny      26 px of ink or less (the size of the plate 90 / 54A dittos)
         touch     touches a line (builder flag)
         oneblob   the truth text of the mark is one piece
         lone      the only ditto word in its crop
         ft100     on a 100 ft plate;   plate6   on plate 6
Also the complement of each tag ('not crossed' ...), so the easy words can be compared with the hard ones.
"""
import json, sys
sys.dont_write_bytecode = True
import numpy as np, cv2
from scipy import ndimage as ndi
TR = 'bench_2026-11-26/text_fix/sealed_final'


def st(W, m):
    n = sum(w['n'] for w in W); f = sum(w[f'f_{m}'] for w in W); wf = sum(int(w[f'f_{m}'] >= 0.5 * w['n']) for w in W)
    return dict(words=len(W), pixel_recall=round(f / max(1, n), 4), words_found=wf, word_share=round(wf / max(1, len(W)), 4))


def main():
    Z = json.load(open(sys.argv[1], encoding='utf8')); W = [w for w in Z['words'] if w['target'] and w['n'] > 0]
    B = [w for w in W if w['kind'] == 'block']; D = [w for w in W if w['kind'] == 'ditto']
    ratio = np.array([w['stroke_w_median'] / max(1, w['height']) for w in B])
    cut = float(np.quantile(ratio, 1 / 3))
    crops = json.load(open(f'{TR}/crops.json'))
    inkpieces = {}
    for w in B:
        c = crops[w['crop']]; x0, y0 = c['win'][:2]; T = cv2.imread(f"{TR}/{w['crop']}_mask.png", 0)
        a = w['aabb']; sub = T[a[1] - y0:a[3] - y0 + 1, a[0] - x0:a[2] - x0 + 1] > 0
        lab, n = ndi.label(sub, structure=np.ones((3, 3))); sizes = ndi.sum(sub, lab, range(1, n + 1))
        inkpieces[(w['crop'], w['id'])] = int((np.asarray(sizes) >= 10).sum())
    digits = lambda r: max(1, sum(ch.isdigit() for ch in r))
    tags = {}
    for w in B:
        t = set()
        if w['touches_line'] or (w['box_nontext'] / max(1, w['box_ink']) > 0.05): t.add('crossed')
        if w['stroke_w_median'] / max(1, w['height']) < cut: t.add('thin')
        if inkpieces[(w['crop'], w['id'])] > digits(w['reading']): t.add('broken')
        if w['crop'] in ('SB-B24', 'SB-B25'): t.add('dense')
        if w['crop'] in ('SA-B15', 'SB-B24', 'SB-B25') or 'unsure' in w['flags']: t.add('doubtful')
        tags[(w['crop'], w['id'])] = t
    dcount = {}
    for w in Z['words']:
        if w['kind'] == 'ditto' and w['n'] > 0: dcount[w['crop']] = dcount.get(w['crop'], 0) + 1
    for w in D:
        t = set()
        if (w['ink_px'] or 0) <= 26: t.add('tiny')
        if w['touches_line']: t.add('touch')
        if w.get('text_components', 1) == 1: t.add('oneblob')
        if dcount.get(w['crop'], 0) == 1: t.add('lone')
        if w['ft'] == 100: t.add('ft100')
        if w['plate'] == '6': t.add('plate6')
        tags[(w['crop'], w['id'])] = t
    O = dict(thin_cut=round(cut, 4), broken_rule='ink pieces of 10 px or more in the word box > figures', block_stroke_ratio_quantiles=[round(float(q), 3) for q in np.quantile(ratio, [0.1, 0.25, 0.33, 0.5, 0.75])])
    for kind, WW, names in (('block', B, ('crossed', 'thin', 'broken', 'dense', 'doubtful')), ('ditto', D, ('tiny', 'touch', 'oneblob', 'lone', 'ft100', 'plate6'))):
        r = {'all': {m: st(WW, m) for m in ('f3', 'f4')}}
        for nm in names:
            h = [w for w in WW if nm in tags[(w['crop'], w['id'])]]; e = [w for w in WW if nm not in tags[(w['crop'], w['id'])]]
            r[nm] = {m: st(h, m) for m in ('f3', 'f4')}; r['not_' + nm] = {m: st(e, m) for m in ('f3', 'f4')}
        anyh = [w for w in WW if tags[(w['crop'], w['id'])]]; none = [w for w in WW if not tags[(w['crop'], w['id'])]]
        if kind == 'block':
            r['any_hard_tag'] = {m: st(anyh, m) for m in ('f3', 'f4')}; r['no_hard_tag'] = {m: st(none, m) for m in ('f3', 'f4')}
            two = [w for w in WW if len(tags[(w['crop'], w['id'])] - {'doubtful'}) >= 2]; r['two_or_more_tags'] = {m: st(two, m) for m in ('f3', 'f4')}
        else:
            tt = [w for w in WW if {'tiny', 'touch'} & tags[(w['crop'], w['id'])]]; r['tiny_or_touch'] = {m: st(tt, m) for m in ('f3', 'f4')}
            nt = [w for w in WW if not ({'tiny', 'touch', 'lone'} & tags[(w['crop'], w['id'])])]; r['not_tiny_touch_lone'] = {m: st(nt, m) for m in ('f3', 'f4')}
        O[kind] = r
    O['word_tags'] = [dict(crop=w['crop'], id=w['id'], plate=w['plate'], ft=w['ft'], reading=w['reading'], n=w['n'], f3=w['f_f3'], f4=w['f_f4'],
                           tags=sorted(tags[(w['crop'], w['id'])]), miss_codes_f4=w['miss_codes_f4']) for w in B + D]
    json.dump(O, open(sys.argv[2], 'w', encoding='utf8', newline='\n'), indent=1)
    print('block stroke/height quantiles (10,25,33,50,75%):', O['block_stroke_ratio_quantiles'])
    for kind in ('block', 'ditto'):
        print(kind)
        for k, v in O[kind].items():
            print(f"  {k:22s} words {v['f4']['words']:3d}   f3 {v['f3']['pixel_recall']:.3f} ({v['f3']['words_found']})   f4 {v['f4']['pixel_recall']:.3f} ({v['f4']['words_found']}/{v['f4']['words']} = {v['f4']['word_share']:.3f})")


if __name__ == '__main__':
    main()
