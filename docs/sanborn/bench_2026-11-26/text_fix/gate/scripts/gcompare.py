"""gcompare.py (final gate): do my scorer (gscore.py) and score_text.py / target_recall.py give the same counts?

    cd data/sanborn
    python -B bench_2026-11-26/text_fix/gate/scripts/gcompare.py GSCORE.npz METHOD SCORE_TEXT.json [TARGET_RECALL.json]

Checks, crop by crop: tp, fp, fn, don't care called text, text on paper; and by word kind: words, text px, found px,
words found. With TARGET_RECALL.json also the target-only counts by kind and scale and the non-text ink called text
inside the block and ditto scopes. Prints every difference and a last line 'AGREE' or 'DIFFER n'.
"""
import json, sys
sys.dont_write_bytecode = True
import numpy as np

Z = np.load(sys.argv[1]); m = sys.argv[2]; S = json.load(open(sys.argv[3], encoding='utf8'))
pix = {r['crop']: r for r in json.loads(str(Z['pix'])) if r['method'] == m}
words = [w for w in json.loads(str(Z['words'])) if w['method'] == m]
bad = 0; checked = 0
for cid, r in S['crops'].items():
    g = pix[cid]
    for k, v in (('tp', r['pix']['tp']), ('fp', r['pix']['fp']), ('fn', r['pix']['fn']), ('t3_called', r['dont_care']['called_text']), ('paper_called', r['text_on_paper'])):
        checked += 1
        if g[k] != v: bad += 1; print('DIFF', cid, k, g[k], v)
    mine = {}
    for w in words:
        if w['crop'] != cid: continue
        k = mine.setdefault(w['kind'], dict(words=0, text_px=0, found_px=0, words_found=0))
        k['words'] += 1; k['text_px'] += w['n']; k['found_px'] += w['f']; k['words_found'] += int(w['f'] >= 0.5 * w['n'])
    for kind in set(mine) | set(r['by_kind']):
        for q in ('words', 'text_px', 'found_px', 'words_found'):
            checked += 1
            a = mine.get(kind, {}).get(q); b = r['by_kind'].get(kind, {}).get(q)
            if a != b: bad += 1; print('DIFF', cid, kind, q, a, b)
if len(sys.argv) > 4:
    T = json.load(open(sys.argv[4], encoding='utf8')); agg = {}
    for w in words:
        if not w['target']: continue
        k = agg.setdefault(f"{w['kind']}_{w['ft']}", dict(words=0, text_px=0, found_px=0, words_found=0))
        k['words'] += 1; k['text_px'] += w['n']; k['found_px'] += w['f']; k['words_found'] += int(w['f'] >= 0.5 * w['n'])
    for key, v in T['targets'].items():
        if key.endswith('_all'): continue
        for q in ('words', 'text_px', 'found_px', 'words_found'):
            checked += 1
            if agg.get(key, {}).get(q) != v[q]: bad += 1; print('DIFF target', key, q, agg.get(key, {}).get(q), v[q])
    for kind, v in T['nontext_in_scopes'].items():
        rr = [r for r in pix.values() if r['ctype'] == 'targeted' and r['target'] == kind]
        for q, mine in (('nontext_px', sum(r['t1'] for r in rr)), ('called_text', sum(r['fp'] for r in rr))):
            checked += 1
            if mine != v[q]: bad += 1; print('DIFF scopes', kind, q, mine, v[q])
print(f'{m}: {checked} numbers checked; ' + ('AGREE' if not bad else f'DIFFER {bad}'))
