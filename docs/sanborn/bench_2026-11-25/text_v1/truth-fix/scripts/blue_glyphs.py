"""Glyph-sized pieces the truth calls NOT text, for checking by eye (truth v2, 25 Nov 2026). A second pointer for the
eye that does not use the finder or bin 8 (suspects.py does), so it can show errors that both methods share.

    cd data/sanborn
    python -B bench_2026-11-25/text_v1/truth-fix/scripts/blue_glyphs.py T1 [T2 ...] [--sheet]

The truth's non-text ink (1) less every straight run of 41 px or more (with its 2 px edge) is cut into 8-connected
pieces; a piece whose box is 7-60 px on its long side and that holds 25 px or more is listed in pics/blue_T#.json,
largest first; straight strokes (minor-axis spread under 1.6 px: dashes, ticks, figure 1s) are left out unless --all. --sheet: contact sheets of them (scan left, truth right) in pics/bluesheet_T#_N.png, 24 a sheet.
Nothing is changed; every change is decided by eye."""
import json, os, sys
sys.dont_write_bytecode = True
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import look
from common import window, line_mask


def pieces(tid):
    c = look.crops[tid]; N = c['plate']; x0, y0, x1, y1 = c['win']
    t = cv2.imread(os.path.join(look.TRD, f'{tid}_mask.png'), 0)
    _, _, ink, _ = window(N, x0, y0, x1, y1)
    ln = cv2.dilate(line_mask(ink, 41, nang=72).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    m = (t == 1) & ~ln
    n, lb, st, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8), connectivity=8)
    out = []
    for i in range(1, n):
        w, h, a = st[i, 2], st[i, 3], st[i, 4]
        if a >= 25 and 7 <= max(w, h) <= 60:
            ys, xs = np.nonzero(lb[st[i, 1]:st[i, 1] + h, st[i, 0]:st[i, 0] + w] == i)
            ev = np.linalg.eigvalsh(np.cov(np.vstack([xs, ys]).astype(float))) if len(xs) > 2 else np.array([0, 0])
            if np.sqrt(max(ev[0], 0)) < 1.6 and '--all' not in sys.argv: continue   # a straight stroke (dash, tick, 1): left out unless --all
            out.append(dict(px=int(a), box=[int(st[i, 0] + x0), int(st[i, 1] + y0), int(st[i, 0] + w + x0), int(st[i, 1] + h + y0)]))
    out.sort(key=lambda d: -d['px'])
    json.dump(out, open(os.path.join(look.PICS, f'blue_{tid}.json'), 'w'), indent=1)
    return out


def sheets(tid, S, per=24, CW=330, CH=150):
    for a0 in range(0, len(S), per):
        cells = []
        for i, s in enumerate(S[a0:a0 + per]):
            x0, y0, x1, y1 = s['box']; cx, cy = (x0 + x1) / 2, (y0 + y1) / 2; w = max(x1 - x0 + 30, 50); h = max(y1 - y0 + 30, 50)
            k = min(3.0, (CW / 2 - 4) / w, (CH - 14) / h); X0, Y0 = int(cx - w / 2), int(cy - h / 2)
            P = look.panel(tid, X0, Y0, X0 + int(w), Y0 + int(h), k, False); off = P.shape[1] // 2 + 3
            cv2.rectangle(P, (int((x0 - X0 - 2) * k) + off, int((y0 - Y0 - 2) * k)), (int((x1 - X0 + 2) * k) + off, int((y1 - Y0 + 2) * k)), (255, 255, 0), 1)
            C = np.full((CH, CW, 3), 255, np.uint8); C[14:14 + P.shape[0], :P.shape[1]] = P[:CH - 14, :CW]
            cv2.putText(C, f'#{a0 + i} {s["px"]}px {x0},{y0}', (2, 11), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (0, 0, 0), 1); cells.append(C)
        cols = 4; rows = (len(cells) + cols - 1) // cols
        G = np.full((rows * (CH + 3), cols * (CW + 3), 3), 200, np.uint8)
        for i, C in enumerate(cells):
            r, cc = divmod(i, cols); G[r * (CH + 3):r * (CH + 3) + CH, cc * (CW + 3):cc * (CW + 3) + CW] = C
        f = os.path.join(look.PICS, f'bluesheet_{tid}_{a0}.png'); cv2.imwrite(f, G); print(f)


if __name__ == '__main__':
    for tid in [a for a in sys.argv[1:] if a.startswith('T')]:
        S = pieces(tid); print(tid, len(S), 'glyph-sized non-text pieces')
        if '--sheet' in sys.argv: sheets(tid, S)
