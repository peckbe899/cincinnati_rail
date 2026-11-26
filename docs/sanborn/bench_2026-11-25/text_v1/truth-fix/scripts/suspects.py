"""Where to look harder when checking truth v2 by eye (25 Nov 2026). Only a pointer for the eye: nothing is changed.

    cd data/sanborn
    python -B bench_2026-11-25/text_v1/truth-fix/scripts/suspects.py T1 [T2 ...] [--min 15] [--tiles]

A suspect is a blob (8-connected, after a 3x3 closing) of ink where the finder (finder/out, codes 2,3,4) and ink_bins'
bin 8 BOTH disagree with the truth: both call text what the truth calls not text (blue suspect), or both miss what the
truth calls text (red suspect). Blobs of at least --min px are listed in pics/suspects_T#.json, largest first.
--tiles: 1:1 tiles (750 x 500) as look.py draws them, with the suspects boxed (cyan: both call text, truth not;
magenta: both miss truth text), written to pics/tile_T#_rRcC.png.
The two methods are only used to point at places. Every change to the truth is decided by eye on the scan."""
import json, os, sys
sys.dont_write_bytecode = True
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import look
FIX = look.FIX; ROOT = look.ROOT
FINDER = os.path.join(ROOT, 'bench_2026-11-25', 'text', 'finder', 'out')
arg = sys.argv; MIN = int(look.opt('--min', d='15'))


def suspects(tid):
    c = look.crops[tid]; N = c['plate']; x0, y0, x1, y1 = c['win']
    t = cv2.imread(os.path.join(look.TRD, f'{tid}_mask.png'), 0)
    f = np.isin(cv2.imread(os.path.join(FINDER, f'{N}_finder.png'), 0)[y0:y1, x0:x1], (2, 3, 4))
    b = cv2.imread(os.path.join(ROOT, 'unet_data', f'{N}_bins.png'), 0)[y0:y1, x0:x1] == 8
    out = []
    for kind, m in (('both_text_truth_not', (t == 1) & f & b), ('both_miss_truth_text', (t == 2) & ~f & ~b)):
        mc = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8)) & (t > 0)
        n, lb, st, _ = cv2.connectedComponentsWithStats(mc.astype(np.uint8), connectivity=8)
        for i in range(1, n):
            if st[i, 4] < MIN: continue
            out.append(dict(kind=kind, px=int(st[i, 4]), box=[int(st[i, 0] + x0), int(st[i, 1] + y0), int(st[i, 0] + st[i, 2] + x0), int(st[i, 1] + st[i, 3] + y0)]))
    out.sort(key=lambda d: -d['px'])
    json.dump(out, open(os.path.join(look.PICS, f'suspects_{tid}.json'), 'w'), indent=1)
    print(tid, len(out), 'suspects;', sum(d['kind'] == 'both_text_truth_not' for d in out), 'both-text,', sum(d['kind'] == 'both_miss_truth_text' for d in out), 'both-miss')
    return out


if __name__ == '__main__':
    for tid in [a for a in arg[1:] if a.startswith('T')]:
        S = suspects(tid)
        if '--tiles' in arg:
            X0, Y0, X1, Y1 = look.crops[tid]['win']; tw, th = 750, 500
            for r, yy in enumerate(range(Y0, Y1, th)):
                for cc, xx in enumerate(range(X0, X1, tw)):
                    P = look.panel(tid, xx, yy, min(X1, xx + tw), min(Y1, yy + th), 1.0, True); off = P.shape[1] // 2 + 3
                    for s in S:
                        bx = s['box']
                        if bx[2] < xx or bx[0] > xx + tw or bx[3] < yy or bx[1] > yy + th: continue
                        col = (255, 255, 0) if s['kind'] == 'both_text_truth_not' else (255, 0, 255)
                        cv2.rectangle(P, (bx[0] - xx - 3 + off, bx[1] - yy - 3), (bx[2] - xx + 3 + off, bx[3] - yy + 3), col, 1)
                    cv2.imwrite(os.path.join(look.PICS, f'tile_{tid}_r{r}c{cc}.png'), P)
