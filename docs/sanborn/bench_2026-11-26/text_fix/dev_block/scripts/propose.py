"""Find the bold figures near each drawn candidate, to centre the zoom pictures (dev_block, 26 Nov 2026). Scan only.

    cd data/sanborn
    python -B bench_2026-11-26/text_fix/dev_block/scripts/propose.py [DB01 ...]

The survey positions are rough (up to ~150 px off). Round each, the thick core of the ink (an opening with a 5 px disk:
block figures have 6-9 px strokes, lot numbers 3-4 px) falls into pieces; pieces 20-110 px tall and 6-110 px wide are
joined into words when they sit side by side (gap under 30 px, overlapping rows). The word nearest the survey position
whose piece count is close to the figure count is proposed. Only a pointer for the zoom: every box is then typed by eye.
Writes dev_block/candidates/proposed.json and the zooms pics/zoom/DBxx.png centred on the proposal."""
import os, sys, json, subprocess
sys.dont_write_bytecode = True
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); DB = os.path.normpath(os.path.join(HERE, '..'))
ROOT = os.path.normpath(os.path.join(DB, '..', '..', '..'))
sys.path.insert(0, HERE)
from common import window  # noqa: E402

R = 230


def propose(N, x, y, reading):
    _, _, ink, (wx0, wy0, _, _) = window(N, x - R, y - R, x + R, y + R)
    core = cv2.morphologyEx(ink.astype(np.uint8), cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
    n, lb, st, _ = cv2.connectedComponentsWithStats(core, connectivity=8)
    P = [st[i] for i in range(1, n) if 20 <= st[i][3] <= 110 and 6 <= st[i][2] <= 110 and st[i][4] >= 60]
    P.sort(key=lambda s: s[0]); words = []
    for s in P:
        for w in words:
            bx0, by0, bx1, by1 = w['box']
            if s[0] - bx1 < 30 and s[0] + s[2] > bx0 - 30 and min(by1, s[1] + s[3]) - max(by0, s[1]) > 0.4 * min(by1 - by0, s[3]):
                w['box'] = [min(bx0, s[0]), min(by0, s[1]), max(bx1, s[0] + s[2]), max(by1, s[1] + s[3])]; w['n'] += 1; break
        else: words.append(dict(box=[int(s[0]), int(s[1]), int(s[0] + s[2]), int(s[1] + s[3])], n=1))
    nd = sum(ch.isdigit() for ch in reading)
    best = None
    for w in words:
        cx, cy = (w['box'][0] + w['box'][2]) / 2 + wx0, (w['box'][1] + w['box'][3]) / 2 + wy0
        d = np.hypot(cx - x, cy - y) + 60 * abs(w['n'] - nd)
        if best is None or d < best[0]: best = (d, [int(w['box'][k] + (wx0, wy0)[k % 2]) for k in range(4)], w['n'])
    return best


if __name__ == '__main__':
    d = json.load(open(os.path.join(DB, 'candidates', 'draw.json'), encoding='utf8'))
    want = [a for a in sys.argv[1:] if a.startswith('DB')]
    out = {}
    for N, v in d['plates'].items():
        for p in v['picks']:
            if want and p['id'] not in want: continue
            b = propose(N, p['x'], p['y'], p['reading'])
            if b is None: print(p['id'], N, p['reading'], 'nothing found'); cx, cy = p['x'], p['y']; box = None
            else: box = b[1]; cx, cy = (box[0] + box[2]) // 2, (box[1] + box[3]) // 2; print(p['id'], N, p['reading'], 'box', box, 'pieces', b[2], 'moved', int(b[0]))
            out[p['id']] = dict(plate=N, reading=p['reading'], survey=[p['x'], p['y']], box=box, centre=[cx, cy])
            subprocess.run([sys.executable, '-B', os.path.join(HERE, 'zoom.py'), N, str(cx), str(cy), '--half', '110', '--scale', '3', '--name', p['id']], check=True, capture_output=True)
    f = os.path.join(DB, 'candidates', 'proposed.json'); old = json.load(open(f)) if os.path.exists(f) else {}
    old.update(out); json.dump(old, open(f, 'w'), indent=1, ensure_ascii=False)
