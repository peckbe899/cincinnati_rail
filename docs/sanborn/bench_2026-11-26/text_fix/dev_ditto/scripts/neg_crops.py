"""Make the NEGATIVE crops from the kept candidates (dev_ditto, 26 Nov 2026).

    cd data/sanborn; python -B bench_2026-11-26/text_fix/dev_ditto/scripts/neg_crops.py

For every candidate marked K in negatives/choose/verdicts_v1.txt and verdicts_v2.txt (in that order): a 64 x 64 px
window centred on it, scope the whole window (crops.json 'scope': 'window', 'target': 'negative'), ids N01 ...
annot/Nxx.txt gets the mark as a 'negative' word (its ink is labelled 1, not text), with flag neg:TYPE:
  rail tick: a 17 x 17 box on the crossing; dash: the box of the separate ink piece nearest the centre (within 6 px);
  line end, hook: a 15 x 15 box on the centre (the hook of D021 is given by hand).
Hand lines (text in the window, CARE) are added below the mark line afterwards and are kept on a re-run (the file is
only written when it does not exist yet). Never reads a finder output or bins."""
import json, os, sys
sys.dont_write_bytecode = True
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common import window
DD = os.path.normpath(os.path.join(HERE, '..')); NG = os.path.join(DD, 'negatives'); CH = os.path.join(NG, 'choose')
SC = json.load(open('scale_table.json'))
HAND = {'D021': [3664, 1988, 3681, 2006]}   # the hook left of the centre
# hook marks along lines: the samplers drew only one, so every hook mark in one drawn window (93A rank 3, the first
# looked-at window where hooks were seen) is taken, by eye on pics/z_w93A3hooks*.png (hand boxes, full-plate px)
HOOKS = [('93A', [2374, 2712, 2390, 2731]), ('93A', [2289, 2751, 2303, 2770]), ('93A', [2384, 2774, 2399, 2797]),
         ('93A', [2552, 2636, 2569, 2654]), ('93A', [2576, 2682, 2593, 2703]), ('93A', [2302, 2809, 2313, 2827])]


def main():
    cands = {}
    for f in ('candidates.json', 'candidates_v2.json'):
        for d in json.load(open(os.path.join(CH, f)))['draws']:
            if d.get('cid'): cands[d['cid']] = d
    kept = []
    for f in ('verdicts_v1.txt', 'verdicts_v2.txt'):
        for l in open(os.path.join(CH, f), encoding='utf8'):
            if l.startswith('#') or not l.strip(): continue
            cid, v, why = l.strip().split(None, 2)
            if v == 'K': kept.append((cid, why))
    crops = {}
    os.makedirs(os.path.join(NG, 'annot'), exist_ok=True)
    for i, (cid, why) in enumerate(kept):
        d = cands[cid]; p = d['plate']; x, y = d['centre']; nid = f'N{i + 1:02d}'
        typ = 'rail_tick' if why.startswith('rail') else 'dash' if why.startswith('dash') else 'hook' if why.startswith('hook') else 'line_end'
        win = [x - 32, y - 32, x + 32, y + 32]
        crops[nid] = dict(plate=p, win=win, scale_ft_per_inch=SC[p]['ft_per_inch'], why=f'{cid} {why}', kind='targeted', target='negative',
                          scope='window', scope_pad=0, neg_type=typ, candidate=cid, sampler=d['sampler'])
        if cid in HAND: box = HAND[cid]
        elif typ == 'rail_tick': box = [x - 8, y - 8, x + 8, y + 8]
        elif typ == 'dash':
            _, _, ink, (wx0, wy0, _, _) = window(p, x - 40, y - 40, x + 40, y + 40)
            n, lb, st, cen = cv2.connectedComponentsWithStats(ink.astype(np.uint8), connectivity=8)
            best = None
            for k in range(1, n):
                if st[k, 4] > 400: continue
                dd = np.hypot(cen[k][0] + wx0 - x, cen[k][1] + wy0 - y)
                if dd <= 6 and (best is None or dd < best[0]): best = (dd, k)
            if best is None: box = [x - 7, y - 7, x + 7, y + 7]; print(nid, cid, 'no separate piece at the centre: box on the centre')
            else:
                k = best[1]; box = [int(st[k, 0] + wx0), int(st[k, 1] + wy0), int(st[k, 0] + st[k, 2] - 1 + wx0), int(st[k, 1] + st[k, 3] - 1 + wy0)]
        else: box = [x - 7, y - 7, x + 7, y + 7]
        f = os.path.join(NG, 'annot', f'{nid}.txt')
        if not os.path.exists(f):
            with open(f, 'w', encoding='utf8') as fh:
                fh.write(f'# {nid} plate {p} window {win} ({cid}, sampler {d["sampler"]}: {why})\n')
                fh.write(f'B {box[0]} {box[1]} {box[2]} {box[3]} | - | negative | neg:{typ}\n')
    for j, (p, box) in enumerate(HOOKS):
        nid = f'N{len(kept) + j + 1:02d}'; x, y = (box[0] + box[2]) // 2, (box[1] + box[3]) // 2; win = [x - 32, y - 32, x + 32, y + 32]
        crops[nid] = dict(plate=p, win=win, scale_ft_per_inch=SC[p]['ft_per_inch'], why='hook mark along a line (all hooks in window 93A rank 3)', kind='targeted',
                          target='negative', scope='window', scope_pad=0, neg_type='hook', candidate=f'H{j + 1}', sampler='window 93A#3, every hook')
        f = os.path.join(NG, 'annot', f'{nid}.txt')
        if not os.path.exists(f):
            with open(f, 'w', encoding='utf8') as fh:
                fh.write(f'# {nid} plate {p} window {win} (hook mark {j + 1} of window 93A rank 3)\n')
                fh.write(f'B {box[0]} {box[1]} {box[2]} {box[3]} | - | negative | neg:hook\n')
    json.dump(crops, open(os.path.join(NG, 'crops.json'), 'w'), indent=1)
    import collections; print(len(crops), 'negative crops', collections.Counter(c['neg_type'] for c in crops.values()))


if __name__ == '__main__':
    main()
