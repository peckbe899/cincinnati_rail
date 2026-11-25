"""Score the words agent's strings against the inventory agent's hand-checked word truth
(bench_2026-11-25/text/inventory/truth/T#_words.json and T#_mask.png), for every truth crop whose plate has been run.

    cd data/sanborn
    python -B bench_2026-11-25/text/words/scripts/measure.py [T1 T2 ...] [--name NAME] [--wtag {N}_finder]

For each truth word, its glyphs are the pieces of ours (glyphlab) with 60% or more of their pixels inside its rotated
box grown by 3 px. Then:
  missed    none of our pieces is in it, or none of them is in any word of ours (junk, or not a candidate)
  exact     all its pieces are in one word of ours, and that word has 80%+ of its ink inside the truth box
  split     its pieces are in two or more of our words (each holding 15%+ of its piece ink)
  merged    one word of ours holds it, but that word has more than 20% of its ink outside the truth box
  (split and merged together count as 'split+merged')
Reading direction: our word's reading angle against the truth's (truth: 0 left to right, 90 reading downwards; ours is
stored anticlockwise, so it is negated), within 30 degrees = right, within 30 of the opposite = turned over.
Kind: our word that holds most of the truth word's ink; truth kinds are mapped to ours (KMAP).
False words: words of ours (not junk) in the crop with under 20% of their ink on truth text (mask 2) or don't-care (3).
Writes out/measure[_TAG].json."""
import json, os, sys
import numpy as np
import cv2
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), 'out')
TR = os.path.join(os.path.dirname(os.path.dirname(HERE)), 'inventory', 'truth')
KMAP = dict(street='street_name', house='house_number', lotdim='lot_dimension', lot='lot_number', block='block_number',
            pipe='pipe_label', sewer='pipe_label', owner='owner_or_note', bldg='owner_or_note', story='story_or_single',
            ditto='ditto', rail='other', adj='other', other='other')


def load_lab(tag):
    L = cv2.imread(os.path.join(OUT, f'{tag}_glyphlab.png'))
    return L[..., 0].astype(np.int32) | (L[..., 1].astype(np.int32) << 8) | (L[..., 2].astype(np.int32) << 16)


def score(T, tag=None):
    J = json.load(open(os.path.join(TR, f'{T}_words.json'), encoding='utf8'))
    N = J['plate']; tag = tag or N
    wf = os.path.join(OUT, f'{tag}_words.json')
    if not os.path.exists(wf): return None
    W = json.load(open(wf, encoding='utf8'))
    x0, y0, x1, y1 = J['win']
    lab = load_lab(tag)[y0:y1, x0:x1]
    tm = cv2.imread(os.path.join(TR, J['mask']), cv2.IMREAD_UNCHANGED)
    owner = {}; words = []
    for r in W['strings']:
        for k, w in enumerate(r['words']):
            wid = len(words); words.append(dict(w, pid=r['id'], k=k, nstr=r['n']))
            for g in w['glyphs']: owner[g + 1] = wid
            for m in w['marks']: owner[m['g'] + 1] = wid
    area = np.bincount(lab.ravel(), minlength=lab.max() + 1)
    res = []; kc = {}
    for t in J['words']:
        poly = np.array(t['poly'], float) - [x0, y0]
        c = poly.mean(0); P = c + (poly - c) * (1 + 6.0 / max(np.hypot(*(poly[1] - poly[0])), np.hypot(*(poly[2] - poly[1])), 1))
        m = np.zeros(lab.shape, np.uint8); cv2.fillPoly(m, [np.round(P).astype(np.int32)], 1)
        ls, cnt = np.unique(lab[m > 0], return_counts=True)
        ins = [(int(l), int(n)) for l, n in zip(ls, cnt) if l > 0 and n >= 0.6 * area[l]]
        inw = [(owner[l], n) for l, n in ins if l in owner and words[owner[l]]['kind'] != 'junk']
        st = dict(id=t['id'], reading=t['reading'], kind=t['kind'], flags=t['flags'], angle=t['angle'], h=t['height'])
        if not inw:
            st['result'] = 'missed'; st['why'] = 'no candidate piece' if not ins else ('pieces not in any word (junk or lone)' if not [l for l, _ in ins if l in owner] else 'only in junk words')
            res.append(st); continue
        by = {}
        for wi, n in inw: by[wi] = by.get(wi, 0) + n
        tot = sum(by.values()); main = max(by, key=by.get)
        many = [wi for wi, n in by.items() if n >= 0.15 * tot]
        # how much of the main word's ink lies inside the truth box
        w = words[main]; gl = [g + 1 for g in w['glyphs']] + [mm['g'] + 1 for mm in w['marks']]
        wa = sum(area[g] for g in gl if g < len(area))
        inside = sum(n for l, n in ins if l in gl)
        frac_in = inside / max(wa, 1)
        split = len(many) >= 2; merged = frac_in < 0.8
        st['result'] = 'split+merged' if split and merged else ('split' if split else ('merged' if merged else 'exact'))
        st['our_kind'] = w['kind']; st['our_angle'] = -w['angle']; st['our_pid'] = w['pid']; st['our_frac_in'] = round(frac_in, 2); st['n_our_words'] = len(many)
        d = (st['our_angle'] - t['angle'] + 180) % 360 - 180
        st['orient'] = 'right' if abs(d) <= 30 else ('turned' if abs(d) >= 150 else 'off')
        st['single_piece'] = w['n'] == 1 and len(w['glyphs']) == 1
        res.append(st)
        k = (KMAP.get(t['kind'], 'other'), w['kind']); kc[k] = kc.get(k, 0) + 1
    # false words: ours in the window, mostly not on truth text
    fw = []
    lab_flat = lab.ravel(); tmf = tm.ravel()
    on = np.bincount(lab_flat, weights=(tmf >= 2).astype(float), minlength=lab.max() + 1)
    for wi, w in enumerate(words):
        if w['kind'] == 'junk': continue
        if not (x0 <= w['cx'] < x1 and y0 <= w['cy'] < y1): continue
        gl = [g + 1 for g in w['glyphs']] + [mm['g'] + 1 for mm in w['marks']]
        a = sum(area[g] for g in gl if g < len(area)); o = sum(on[g] for g in gl if g < len(on))
        if a > 0 and o / a < 0.2: fw.append(dict(pid=w['pid'], kind=w['kind'], cx=w['cx'], cy=w['cy'], h=w['h'], on_text=round(o / a, 2)))
    nwin = sum(1 for w in words if w['kind'] != 'junk' and x0 <= w['cx'] < x1 and y0 <= w['cy'] < y1)
    # text mask against the truth mask (care pixels only)
    tmask = cv2.imread(os.path.join(OUT, f'{tag}_textmask.png'), 0)[y0:y1, x0:x1] > 0
    care = tm <= 2; tt = (tm == 2) & care; pp = tmask & care
    px = dict(text_px=int(tt.sum()), ours_px=int(pp.sum()), tp=int((tt & pp).sum()))
    px['recall'] = round(px['tp'] / max(px['text_px'], 1), 3); px['precision'] = round(px['tp'] / max(px['ours_px'], 1), 3)
    return dict(crop=T, plate=N, tag=tag, win=J['win'], n_truth=len(J['words']), words=res, kind_pairs={f'{a}|{b}': n for (a, b), n in sorted(kc.items())},
                false_words=fw, our_words_in_window=nwin, pixels=px)


def summary(R):
    w = R['words']; n = len(w)
    c = {k: sum(x['result'] == k for x in w) for k in ('exact', 'merged', 'split', 'split+merged', 'missed')}
    found = [x for x in w if x['result'] != 'missed']
    multi = [x for x in w if x['result'] != 'missed' and len(x['reading'].replace(' ', '')) >= 2]
    o = {k: sum(x.get('orient') == k for x in found) for k in ('right', 'turned', 'off')}
    om = {k: sum(x.get('orient') == k for x in found if not x['single_piece']) for k in ('right', 'turned', 'off')}
    kk = sum(KMAP.get(x['kind'], 'other') == x['our_kind'] for x in found)
    bykind = {}
    for x in w:
        b = bykind.setdefault(x['kind'], dict(n=0, exact=0, missed=0, kind_right=0))
        b['n'] += 1; b['exact'] += x['result'] == 'exact'; b['missed'] += x['result'] == 'missed'
        b['kind_right'] += x['result'] != 'missed' and KMAP.get(x['kind'], 'other') == x['our_kind']
    return dict(crop=R['crop'], plate=R['plate'], truth_words=n, **c, orient_all=o, orient_multi_piece_words=om, kind_right=kk, kind_scored=len(found),
                by_truth_kind=bykind, false_words=len(R['false_words']), our_words_in_window=R['our_words_in_window'], pixels=R['pixels'])


def main():
    Ts = [a for a in sys.argv[1:] if a.startswith('T')] or sorted(f.split('_')[0] for f in os.listdir(TR) if f.endswith('_words.json'))
    tag = sys.argv[sys.argv.index('--wtag') + 1] if '--wtag' in sys.argv else None
    name = sys.argv[sys.argv.index('--name') + 1] if '--name' in sys.argv else None
    allr = []; sums = []
    for T in Ts:
        R = score(T, None if tag is None else tag.replace('{N}', json.load(open(os.path.join(TR, f'{T}_words.json'), encoding='utf8'))['plate']))
        if R is None: print(T, 'plate not run'); continue
        s = summary(R); allr.append(R); sums.append(s)
        print(json.dumps(s))
    tot = {}
    for s in sums:
        for k in ('truth_words', 'exact', 'merged', 'split', 'split+merged', 'missed', 'kind_right', 'kind_scored', 'false_words', 'our_words_in_window'):
            tot[k] = tot.get(k, 0) + s[k]
        for k in ('right', 'turned', 'off'):
            tot['orient_' + k] = tot.get('orient_' + k, 0) + s['orient_all'][k]; tot['orient_multi_' + k] = tot.get('orient_multi_' + k, 0) + s['orient_multi_piece_words'][k]
    print('TOTAL', json.dumps(tot))
    json.dump(dict(summaries=sums, total=tot, detail=allr), open(os.path.join(OUT, 'measure' + ('_' + name if name else '') + '.json'), 'w', encoding='utf8'), indent=1)


if __name__ == '__main__':
    main()
