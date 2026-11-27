"""Target-only numbers for the sealed set (sealed cross-check, 26 Nov 2026). score_text.py counts every word of a kind;
this counts only the target words (block numbers and ditto marks drawn at random), split by scale, with the same rules:
a word's text pixels are the truth-2 pixels inside its box; found = those the mask calls text; a word is found when at
least half its text pixels are found. Also non-text ink called text inside the targeted scopes, by target kind.
    cd data/sanborn
    python -B bench_2026-11-26/text_fix/sealed_check/scripts/target_recall.py MASK (--codes 2,3 | --binary) [--truth DIR] [--out F.json]
MASK as in score_text.py ({plate} and/or {crop}; plate-sized or crop-sized)."""
import argparse, json, os, sys
sys.dont_write_bytecode = True
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser(); ap.add_argument('mask'); g = ap.add_mutually_exclusive_group(required=True); g.add_argument('--codes'); g.add_argument('--binary', action='store_true')
ap.add_argument('--truth', default=os.path.normpath(os.path.join(HERE, '..', '..', 'sealed_final'))); ap.add_argument('--out'); a = ap.parse_args()
crops = json.load(open(os.path.join(a.truth, 'crops.json'), encoding='utf8'))
is_text = (lambda m: m > 0) if a.binary else (lambda m: np.isin(m, [int(v) for v in a.codes.split(',')]))
cache = {}; agg = {}; fp = {}
for tid, c in crops.items():
    if c.get('kind') != 'targeted': continue
    x0, y0, x1, y1 = c['win']; path = a.mask.replace('{plate}', c['plate']).replace('{crop}', tid)
    if path not in cache:
        m = cv2.imread(path, cv2.IMREAD_UNCHANGED)
        if m is None: raise SystemExit(f'no mask file {path}')
        cache[path] = m[..., 0] if m.ndim == 3 else m
    m = cache[path]; m = m if m.shape == (y1 - y0, x1 - x0) else m[y0:y1, x0:x1]
    T = cv2.imread(os.path.join(a.truth, f'{tid}_mask.png'), 0); P = is_text(m)
    f = fp.setdefault(c['target'], dict(nontext_px=0, called_text=0)); f['nontext_px'] += int((T == 1).sum()); f['called_text'] += int(((T == 1) & P).sum())
    for w in json.load(open(os.path.join(a.truth, f'{tid}_words.json'), encoding='utf8'))['words']:
        if not w.get('target'): continue
        pm = np.zeros(T.shape, np.uint8); cv2.fillPoly(pm, [np.round(np.array(w['poly']) - [x0, y0]).astype(np.int32)], 1)
        t = (pm > 0) & (T == 2); n = int(t.sum())
        if not n: continue
        k = agg.setdefault(f"{w['kind']}_{c['scale_ft_per_inch']}", dict(words=0, text_px=0, found_px=0, words_found=0))
        fnd = int((t & P).sum()); k['words'] += 1; k['text_px'] += n; k['found_px'] += fnd; k['words_found'] += int(fnd >= 0.5 * n)
for kind in ('block', 'ditto'):
    keys = [k for k in agg if k.startswith(kind + '_')]
    if keys: agg[kind + '_all'] = {q: sum(agg[k][q] for k in keys) for q in ('words', 'text_px', 'found_px', 'words_found')}
for k, v in agg.items(): v['pixel_recall'] = round(v['found_px'] / max(1, v['text_px']), 4); v['word_recall'] = round(v['words_found'] / max(1, v['words']), 4)
for k, v in fp.items(): v['share'] = round(v['called_text'] / max(1, v['nontext_px']), 5)
for k in sorted(agg): v = agg[k]; print(f"{k:10s} pixel recall {v['pixel_recall']:.3f}   words {v['words_found']}/{v['words']}")
for k, v in fp.items(): print(f"non-text ink called text in {k} scopes: {v['called_text']} of {v['nontext_px']} ({v['share']:.4f})")
if a.out: json.dump(dict(mask=a.mask, targets=agg, nontext_in_scopes=fp), open(a.out, 'w'), indent=1)
