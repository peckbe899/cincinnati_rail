"""Counts of the sealed-B truth (no method output is read): targets by kind and scale, ink size of every target word,
words by kind, mask pixel classes, scope sizes. python -B stats.py -> sealed_B/truth/stats.json (and prints a summary)"""
import os, sys, json
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import numpy as np, cv2
from common import INV, jdump

TR = os.path.join(INV, 'truth')
crops = json.load(open(os.path.join(TR, 'crops.json'), encoding='utf8'))
out = dict(crops={}, targets=[], by_kind_scale={}, words_by_kind={}, mask_px={'0': 0, '1': 0, '2': 0, '3': 0}, scored_px_in_scopes={'1': 0, '2': 0, '3': 0})
for k in sorted(crops):
    c = crops[k]; M = cv2.imread(os.path.join(TR, f'{k}_mask.png'), 0); W = json.load(open(os.path.join(TR, f'{k}_words.json'), encoding='utf8'))
    assert M.shape == (c['win'][3] - c['win'][1], c['win'][2] - c['win'][0]), k
    px = {str(v): int((M == v).sum()) for v in range(4)}
    for v in px: out['mask_px'][v] += px[v]
    out['crops'][k] = dict(plate=c['plate'], scale=c['scale_ft_per_inch'], kind=c.get('kind'), target=c.get('target'), win=c['win'], n_words=len(W['words']),
                           n_targets=sum(w['target'] for w in W['words']), px=px)
    for w in W['words']:
        out['words_by_kind'][w['kind']] = out['words_by_kind'].get(w['kind'], 0) + 1
        if w['target']:
            out['targets'].append(dict(crop=k, id=w['id'], plate=c['plate'], scale=c['scale_ft_per_inch'], kind=w['kind'], reading=w['reading'],
                                       aabb=w['aabb'], ink_px=w['ink_px'], text_px=w['text_px_final'], flags=w['flags'], touches_line=w['touches_line']))
for t in out['targets']:
    d = out['by_kind_scale'].setdefault(t['kind'], {}).setdefault(str(t['scale']), dict(words=0, ink=[]))
    d['words'] += 1; d['ink'].append(t['ink_px'])
for kd, v in out['by_kind_scale'].items():
    for s, d in v.items():
        a = np.array(d['ink']); d.update(ink_median=float(np.median(a)), ink_min=int(a.min()), ink_max=int(a.max()), ink_sum=int(a.sum())); d.pop('ink')
jdump(out, os.path.join(TR, 'stats.json'))
for kd, v in sorted(out['by_kind_scale'].items()):
    for s, d in sorted(v.items(), key=lambda q: int(q[0])):
        print(f'{kd:6s} {s:>3s} ft: {d["words"]:3d} words, ink px median {d["ink_median"]:.0f} (min {d["ink_min"]}, max {d["ink_max"]})')
tk = [t for t in out['targets'] if t['kind'] == 'ditto']; tb = [t for t in out['targets'] if t['kind'] == 'block']
print('targets', len(out['targets']), 'block', len(tb), 'ditto', len(tk), '| touching a line: block', sum(t['touches_line'] for t in tb), 'ditto', sum(t['touches_line'] for t in tk))
print('crops', len(crops), 'words by kind', dict(sorted(out['words_by_kind'].items())))
print('mask px', out['mask_px'])
f = out['crops'].get('SB-F1'); print('SB-F1', f)
