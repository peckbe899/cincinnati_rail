"""Detection and reading check of blockfix numbers against dev_block's survey lists and dev truth targets (dev plates).
    python -B .../scripts/eval_blocks.py RUN_DIR plates... [--sheet OUT.png] [--which acc|rej] [--json OUT.json] [--sure]
--sure: only the sure readings (not the ones listed as unsure).
A number matches a survey point when the point lies within its box grown by 45 px (survey points are rough). Readings with
a fraction (6 1/2) are compared on their whole figures. H windows are skipped."""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'code'))
import numpy as np, cv2
import bfcommon as C

a = sys.argv[1:]; sheet = None; which = 'acc'; jout = None; sure = '--sure' in a; a = [x for x in a if x != '--sure']
if '--sheet' in a: i = a.index('--sheet'); sheet = a[i + 1]; a = a[:i] + a[i + 2:]
if '--which' in a: i = a.index('--which'); which = a[i + 1]; a = a[:i] + a[i + 2:]
if '--json' in a: i = a.index('--json'); jout = a[i + 1]; a = a[:i] + a[i + 2:]
rd, plates = a[0], a[1:]
crops = C.dev_crops(); tiles = []; tot = dict(cand=0, found=0, read_ok=0, nums=0, fp=0); per = {}
digits = lambda s: ''.join(ch for ch in s if ch.isdigit())
for N in plates:
    B = json.load(open(os.path.join(rd, f'{N}_blocks.json'), encoding='utf8'))
    nums = B['numbers'] if which == 'acc' else B['rejected']
    if sure: nums = [n for n in nums if not n.get('unsure')]
    cands = [(x, y, r) for x, y, r, _ in C.candidates(N) if not C.in_hwin(N, (x - 50, y - 50, x + 50, y + 50))]
    # dev targets: their exact boxes replace the survey point nearby
    for tid, c in crops.items():
        if c['plate'] != N: continue
        W = json.load(open(os.path.join(C.DEVB, 'truth', f'{tid}_words.json'), encoding='utf8'))['words']
        w = [q for q in W if q.get('target')][0]; bx = w['aabb']; cx, cy = (bx[0] + bx[2]) / 2, (bx[1] + bx[3]) / 2
        cands = [q for q in cands if np.hypot(q[0] - cx, q[1] - cy) > 80] + [(cx, cy, w['reading'])]
    nums = [n for n in nums if not C.in_hwin(N, n['box'])]
    used = set(); res = dict(cand=len(cands), found=0, read_ok=0, nums=len(nums), fp=0, misses=[], wrong=[], fps=[])
    for x, y, r in cands:
        best = None
        for i, n in enumerate(nums):
            b = n['box']
            if b[0] - 45 <= x <= b[2] + 45 and b[1] - 45 <= y <= b[3] + 45:
                d = np.hypot((b[0] + b[2]) / 2 - x, (b[1] + b[3]) / 2 - y)
                if best is None or d < best[0]: best = (d, i)
        if best is None: res['misses'].append((int(x), int(y), r)); continue
        res['found'] += 1; used.add(best[1]); n = nums[best[1]]
        if n['reading'] == digits(r): res['read_ok'] += 1
        else: res['wrong'].append((int(x), int(y), r, n['reading']))
    for i, n in enumerate(nums):
        if i not in used: res['fp'] += 1; res['fps'].append((n['reading'], [int(v) for v in n['box']], n.get('why_not', '')))
    per[N] = res
    for k in tot: tot[k] += res[k]
    print(f"{N}: survey+targets {res['cand']}, found {res['found']}, read right {res['read_ok']}; numbers {res['nums']}, not on the list {res['fp']}")
    if sheet:
        im = cv2.imread(f'cufp/22-{N}.jpg'); H, W = im.shape[:2]
        for i, n in enumerate(nums):
            b = [int(v) for v in n['box']]; cx, cy = (b[0] + b[2]) // 2, (b[1] + b[3]) // 2
            X0, Y0 = max(0, cx - 80), max(0, cy - 60); t = im[Y0:Y0 + 120, X0:X0 + 160].copy()
            t = cv2.copyMakeBorder(t, 0, 120 - t.shape[0], 0, 160 - t.shape[1], cv2.BORDER_CONSTANT, value=(255, 255, 255))
            cv2.rectangle(t, (b[0] - X0, b[1] - Y0), (b[2] - X0, b[3] - Y0), (0, 160, 0) if i in used else (0, 0, 255), 1)
            cv2.putText(t, f"{N} {n['reading']} {n['score']:.2f}", (2, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255) if i not in used else (0, 120, 0), 1)
            if which != 'acc': cv2.putText(t, n.get('why_not', '')[:24], (2, 116), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (200, 0, 0), 1)
            tiles.append(t)
print(f"ALL: survey+targets {tot['cand']}, found {tot['found']} ({tot['found'] / max(1, tot['cand']):.3f}), read right {tot['read_ok']} ({tot['read_ok'] / max(1, tot['found']):.3f} of found); "
      f"numbers {tot['nums']}, not on the list {tot['fp']}")
if jout: json.dump(dict(total=tot, plates=per), open(jout, 'w'), indent=1)
if sheet and tiles:
    cols = 10; rows = (len(tiles) + cols - 1) // cols; S = np.full((rows * 122, cols * 162, 3), 255, np.uint8)
    for i, t in enumerate(tiles): r_, c_ = divmod(i, cols); S[r_ * 122:r_ * 122 + 120, c_ * 162:c_ * 162 + 160] = t
    cv2.imwrite(sheet, S); print('sheet', S.shape)
