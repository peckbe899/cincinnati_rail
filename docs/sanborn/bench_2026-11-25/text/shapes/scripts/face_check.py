"""A first code check of house-number readings along a block face (shapes prototype, 25 Nov 2026).

    python -B bench_2026-11-25/text/shapes/scripts/face_check.py [eval_faces_holdout.json] [reader]   (from data/sanborn)

Takes the readings of eval_faces.py (default: the hold-out run, reader knn_ctx) and checks each number token by rules
only, with no look at the truth:
  - tokens: the figures read on the face, in order along it, cut where the gap between two figures' boxes (projected
    on the face) is more than 0.45 of the median figure height, or where a '-' was read (the words of
    extract_glyphs.py join neighbouring numbers and split others, so they are not used); a run of 3-4 figures is a house number, a run of 2 right after a house number or after
    another such run is a continuation ('1424-22-20'); anything else (1 figure, 5 or more) is flagged 'shape';
  - house numbers on one face share one parity (the majority's) and run one way (the majority's); a number that breaks
    either, or jumps by more than 40 from its neighbour, is flagged;
  - a continuation must be the last two figures of the number before it, plus or minus 2.
Then compares with the truth: how many flagged tokens are wrong, how many wrong tokens are not flagged.
"""
import json, os, re, sys
import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


FACES = {'A': ((5642, 1944), (6211, 1888)), 'B': ((994, 3611), (1550, 3645)), 'C': ((1975, 214), (2600, 217))}   # as eval_faces.py


def tokens(glyphs, D, face):
    a, b = (np.array(p, float) for p in FACES[face]); u = (b - a) / np.linalg.norm(b - a); nrm = np.array([-u[1], u[0]])
    items = []
    for k, ch in glyphs:
        x, y, w, h = D['bbox'][k]; cs = np.array([[x, y], [x + w, y], [x, y + h], [x + w, y + h]], float) - a
        items.append((k, ch, (cs @ u).min(), (cs @ u).max(), np.ptp(cs @ nrm)))
    hts = [it[4] for it in items if it[1].isdigit()]; hmed = float(np.median(hts)) if hts else 25.0
    out = []; cur = ''; last = None
    for k, ch, lo, hi, _ in items:
        if ch == '-':
            if cur: out.append(cur); cur = ''
            last = None; continue
        if not ch.isdigit(): continue
        if last is not None and k != last[0] and lo - last[1] > 0.45 * hmed:
            out.append(cur); cur = ''
        cur += ch; last = (k, hi)
    if cur: out.append(cur)
    return out


def check(toks):
    kind = []; prev = None
    for t in toks:
        if len(t) in (3, 4): kind.append('num'); prev = 'num'
        elif len(t) == 2 and prev in ('num', 'cont'): kind.append('cont'); prev = 'cont'
        else: kind.append('shape'); prev = None
    flags = ['shape' if k == 'shape' else '' for k in kind]
    nums = [(i, int(t)) for i, (t, k) in enumerate(zip(toks, kind)) if k == 'num']
    if len(nums) >= 2:
        par = round(sum(v % 2 for _, v in nums) / len(nums))
        steps = [b[1] - a[1] for a, b in zip(nums, nums[1:])]; up = sum(s > 0 for s in steps) >= sum(s < 0 for s in steps)
        for j, (i, v) in enumerate(nums):
            if v % 2 != par: flags[i] = flags[i] or 'parity'
            for nb in (nums[j - 1] if j else None, nums[j + 1] if j + 1 < len(nums) else None):
                if nb is None: continue
                if abs(nb[1] - v) > 40: flags[i] = flags[i] or 'jump'
            if j and ((v - nums[j - 1][1] > 0) != up) and v != nums[j - 1][1]: flags[i] = flags[i] or 'order'
    last = None
    for i, (t, k) in enumerate(zip(toks, kind)):
        if k == 'num': last = int(t)
        elif k == 'cont' and last is not None:
            if abs(int(t) - last % 100) != 2: flags[i] = flags[i] or 'continuation'
            last = last - last % 100 + int(t)
    return kind, flags


def main():
    f = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'eval_faces_holdout.json'); rn = sys.argv[2] if len(sys.argv) > 2 else 'knn_ctx'
    J = json.load(open(f)); tot = dict(tokens=0, flagged=0, flagged_wrong=0, wrong=0, wrong_unflagged=0, right_flagged=0)
    D = np.load(os.path.join(HERE, J.get('glyphs', 'glyphs'), '44.npz'))
    for face, s in J['per'][rn].items():
        if not face[:2] in ('A ', 'B ', 'C '): continue
        toks = tokens(s['glyphs'], D, face[0]); kind, flags = check(toks)
        truth = re.findall(r'\d+', {'A': '1424-22-20 1418 1416 1414 1412 1410 1408', 'B': '1629 1625-23 1621 1613',
                                     'C': '1563-61 1559 1557 1555-53 1551 1549-47'}[face[0]])
        # a token is right if it equals the truth token that the reading's order puts there (greedy match in order)
        right = []; j = 0
        for t in toks:
            if j < len(truth) and t == truth[j]: right.append(True); j += 1
            elif t in truth[j:]: j = truth.index(t, j) + 1; right.append(True)
            else: right.append(False)
        print(face, '| truth', ' '.join(truth))
        for t, k, fl, r in zip(toks, kind, flags, right):
            print(f'   {t:>8s} {k:5s} {"FLAG " + fl if fl else "ok":18s} {"right" if r else "WRONG"}')
            tot['tokens'] += 1; tot['flagged'] += bool(fl); tot['flagged_wrong'] += bool(fl) and not r; tot['wrong'] += not r; tot['wrong_unflagged'] += (not r) and not fl; tot['right_flagged'] += r and bool(fl)
    print(tot)


if __name__ == '__main__':
    main()
