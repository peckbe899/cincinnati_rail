"""Compare masks and words of two truth folders (sealed cross-check). Prints per crop the pixels that differ (by value
pair) and the words whose reading, kind, aabb or target flag differ.
    python -B compare.py DIR_A DIR_B [ids...]   (ids default: every <id>_mask.png in DIR_B present in DIR_A)"""
import os, sys, json, glob
sys.dont_write_bytecode = True
import numpy as np, cv2
a, b = sys.argv[1], sys.argv[2]
ids = sys.argv[3:] or sorted(os.path.basename(p)[:-9] for p in glob.glob(os.path.join(b, '*_mask.png')) if os.path.exists(os.path.join(a, os.path.basename(p))))
tot = 0; nd = 0
for t in ids:
    A = cv2.imread(os.path.join(a, f'{t}_mask.png'), 0); B = cv2.imread(os.path.join(b, f'{t}_mask.png'), 0)
    d = A != B; n = int(d.sum()); tot += n
    pairs = {}
    if n:
        for u, v in zip(A[d].tolist(), B[d].tolist()): pairs[f'{u}->{v}'] = pairs.get(f'{u}->{v}', 0) + 1
    wa = {w['id']: w for w in json.load(open(os.path.join(a, f'{t}_words.json'), encoding='utf8'))['words']}
    wb = {w['id']: w for w in json.load(open(os.path.join(b, f'{t}_words.json'), encoding='utf8'))['words']}
    wd = []
    for k in sorted(set(wa) | set(wb)):
        x, y = wa.get(k), wb.get(k)
        if x is None or y is None: wd.append(f'{k} only in {"B" if x is None else "A"}'); continue
        tx = x.get('target', 'target' in x.get('flags', [])); ty = y.get('target', 'target' in y.get('flags', []))
        for f in ('reading', 'kind', 'aabb'):
            if x[f] != y[f]: wd.append(f'{k} {f} {x[f]} -> {y[f]}')
        if tx != ty: wd.append(f'{k} target {tx} -> {ty}')
    if n or wd: nd += 1; print(t, n, 'px differ', pairs, '; words:', wd[:8], '...' if len(wd) > 8 else '')
print('crops compared', len(ids), 'crops with a difference', nd, 'pixels differing', tot)
