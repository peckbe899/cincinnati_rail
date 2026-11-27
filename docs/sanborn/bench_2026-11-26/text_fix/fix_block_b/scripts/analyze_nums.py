"""Features of every number blockfix kept, labelled by the survey lists (on the list or not), to set the number rules.
    python -B .../scripts/analyze_nums.py RUN_DIR plates...
Matching as eval_blocks.py. Prints how many on-list and off-list numbers each rule would keep."""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'code'))
import numpy as np
import bfcommon as C

rd, plates = sys.argv[1], sys.argv[2:]; crops = C.dev_crops(); rows = []
for N in plates:
    B = json.load(open(os.path.join(rd, f'{N}_blocks.json'), encoding='utf8')); nums = [n for n in B['numbers'] if not C.in_hwin(N, n['box'])]
    cands = [(x, y, r) for x, y, r, _ in C.candidates(N) if not C.in_hwin(N, (x - 50, y - 50, x + 50, y + 50))]
    for tid, c in crops.items():
        if c['plate'] != N: continue
        W = json.load(open(os.path.join(C.DEVB, 'truth', f'{tid}_words.json'), encoding='utf8'))['words']
        w = [q for q in W if q.get('target')][0]; bx = w['aabb']; cx, cy = (bx[0] + bx[2]) / 2, (bx[1] + bx[3]) / 2
        cands = [q for q in cands if np.hypot(q[0] - cx, q[1] - cy) > 80] + [(cx, cy, w['reading'])]
    lab = np.zeros(len(nums), int)
    # a number is on the list when a survey point (or dev target) lies within its box grown 60 px, or a survey point with
    # the same reading lies within 250 px (survey points are rough, some by 100-200 px)
    for i, n in enumerate(nums):
        b = n['box']; cx_, cy_ = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
        for x, y, r in cands:
            if (b[0] - 60 <= x <= b[2] + 60 and b[1] - 60 <= y <= b[3] + 60) or (''.join(ch for ch in r if ch.isdigit()) == n['reading'] and np.hypot(x - cx_, y - cy_) <= 250): lab[i] = 1
    for x, y, r in []:
        best = None
        for i, n in enumerate(nums):
            b = n['box']
            if b[0] - 45 <= x <= b[2] + 45 and b[1] - 45 <= y <= b[3] + 45:
                d = np.hypot((b[0] + b[2]) / 2 - x, (b[1] + b[3]) / 2 - y)
                if best is None or d < best[0]: best = (d, i)
        if best: lab[best[1]] = 1
    for n, l in zip(nums, lab):
        f = n['figs']
        rows.append(dict(plate=N, lab=int(l), nf=len(f), pmin=min(q['p'] for q in f), pnmax=max(q['pnone'] for q in f), smin=min(q['s'] for q in f),
                         smean=float(np.mean([q['s'] for q in f])), iso=n.get('feat', {}).get('iso', 0), iso_t=n.get('feat', {}).get('iso_t', 0), h=max(q['h'] for q in f), reading=n['reading'],
                         feat=n.get('feat'), box=n['box']))
lab = np.array([r['lab'] for r in rows]); print('on list', lab.sum(), 'off list', (1 - lab).sum())
def show(name, keep):
    keep = np.array(keep); print(f'{name:40s} keeps on-list {int((keep & (lab == 1)).sum())}  off-list {int((keep & (lab == 0)).sum())}')
A = lambda k: np.array([r[k] for r in rows])
show('all', np.ones(len(rows), bool))
for t in (0, 1, 2, 3): show(f'iso <= {t}', A('iso') <= t)
for t in (0, 1, 2, 3): show(f'iso_t <= {t}', A('iso_t') <= t)
for t in (1, 2): show(f'iso + iso_t <= {t}', A('iso') + A('iso_t') <= t)
for t in (0.5, 0.6, 0.7, 0.8): show(f'smin >= {t}', A('smin') >= t)
for t in (0.2, 0.1, 0.05, 0.02): show(f'pnone max <= {t}', A('pnmax') <= t)
show('nf >= 2', A('nf') >= 2)
for t in (0.6, 0.7):
    for u in (0.2, 0.1):
        show(f'iso<=1 & smin>={t} & pnone<={u}', (A('iso') <= 1) & (A('smin') >= t) & (A('pnmax') <= u))
for nf in (1, 2, 3):
    m = A('nf') == nf; print(f'nf={nf}: on {int((m & (lab == 1)).sum())} off {int((m & (lab == 0)).sum())}')
json.dump(rows, open(os.path.join(rd, 'nums_features.json'), 'w'), indent=0)
