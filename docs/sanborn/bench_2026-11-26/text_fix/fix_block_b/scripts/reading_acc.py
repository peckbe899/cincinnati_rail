"""Reading accuracy of blockfix on the dev truth: the 45 dev block targets and the 7 T1-T7 block words.
    python -B .../scripts/reading_acc.py RUN_DIR_DEV RUN_DIR_T17 OUT.json
A target is FOUND when a kept number's box overlaps the target's word box (aabb) by half the number's box or more;
READ RIGHT when that number's reading equals the target's whole figures (6 1/2 -> 6: the half is not read)."""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'code'))
import numpy as np
import bfcommon as C

rd, rt, outp = sys.argv[1], sys.argv[2], sys.argv[3]
digits = lambda s: ''.join(ch for ch in s if ch.isdigit())


def match(nums, bx):
    best = None
    for n in nums:
        b = n['box']; iw = min(b[2], bx[2]) - max(b[0], bx[0]); ih = min(b[3], bx[3]) - max(b[1], bx[1])
        if iw <= 0 or ih <= 0: continue
        f = iw * ih / max(1.0, (b[2] - b[0]) * (b[3] - b[1]))
        if f >= 0.5 and (best is None or f > best[0]): best = (f, n)
    return best[1] if best else None


res = {}
for tid, c in sorted(C.dev_crops().items()):
    W = json.load(open(os.path.join(C.DEVB, 'truth', f'{tid}_words.json'), encoding='utf8'))['words']; w = [q for q in W if q.get('target')][0]
    nums = json.load(open(os.path.join(rd, f"{c['plate']}_blocks.json"), encoding='utf8'))['numbers']; n = match(nums, w['aabb'])
    res[tid] = dict(plate=c['plate'], truth=w['reading'], read=n['reading'] if n else None, right=bool(n and n['reading'] == digits(w['reading'])), unsure=bool(n and n.get('unsure')),
                    flags=n.get('flags', []) if n else None, fold='A' if c['plate'] in C.FOLD['A'] else 'B')
T = json.load(open(os.path.join(C.TV1, 'truth', 'crops.json'))); t17 = {}
for tid in ('T1', 'T2', 'T3', 'T4', 'T6', 'T7'):
    if tid not in T: continue
    W = json.load(open(os.path.join(C.TV1, 'truth', f'{tid}_words.json'), encoding='utf8'))['words']; N = T[tid]['plate']
    nums = json.load(open(os.path.join(rt, f'{N}_blocks.json'), encoding='utf8'))['numbers']
    for w in W:
        if w['kind'] != 'block': continue
        n = match(nums, w['aabb'])
        t17[w['id']] = dict(plate=N, truth=w['reading'], read=n['reading'] if n else None, right=bool(n and n['reading'] == digits(w['reading'])), unsure=bool(n and n.get('unsure')))
out = dict(dev=res, t17=t17)
for k, R in (('dev A', {t: r for t, r in res.items() if r['fold'] == 'A'}), ('dev B', {t: r for t, r in res.items() if r['fold'] == 'B'}), ('dev all', res), ('T1-T7', t17)):
    f = sum(r['read'] is not None for r in R.values()); g = sum(r['right'] for r in R.values())
    fs = sum(r['read'] is not None and not r['unsure'] for r in R.values()); gs = sum(r['right'] and not r['unsure'] for r in R.values())
    out[k] = dict(targets=len(R), found=f, read_right=g, found_sure=fs, read_right_sure=gs)
    print(f'{k}: {len(R)} targets, found {f}, read right {g}; sure readings only: found {fs}, read right {gs}')
print('wrong or missed:', {t: (r['truth'], r['read']) for t, r in list(res.items()) + list(t17.items()) if not r['right']})
json.dump(out, open(outp, 'w'), indent=1)
