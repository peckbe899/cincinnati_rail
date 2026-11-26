"""Contact sheets of the suspects (suspects.py) for checking by eye: each cell is the scan (left) and the truth (right,
look.py colours) at 3x around one suspect, outlined (cyan: finder and bin 8 call text, truth not; magenta: both miss
truth text), numbered as in pics/suspects_T#.json.

    cd data/sanborn
    python -B bench_2026-11-25/text_v1/truth-fix/scripts/sheet.py T1 [--from 0] [--n 15] [--scale 3] [--pad 14]
Writes pics/sheet_T#_<from>.png."""
import json, os, sys
sys.dont_write_bytecode = True
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import look

tid = sys.argv[1]; a0 = int(look.opt('--from', d='0')); n = int(look.opt('--n', d='15')); sc = float(look.opt('--scale', d='3')); pad = int(look.opt('--pad', d='14'))
S = json.load(open(os.path.join(look.PICS, f'suspects_{tid}.json')))[a0:a0 + n]
CW, CH = 500, 230
cells = []
for i, s in enumerate(S):
    x0, y0, x1, y1 = s['box']; cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    w = max(x1 - x0 + 2 * pad, 40); h = max(y1 - y0 + 2 * pad, 40)
    k = min(sc, (CW / 2 - 4) / w, (CH - 14) / h)
    X0, Y0 = int(cx - w / 2), int(cy - h / 2)
    P = look.panel(tid, X0, Y0, X0 + int(w), Y0 + int(h), k, True)
    off = P.shape[1] // 2 + 3; col = (255, 255, 0) if s['kind'] == 'both_text_truth_not' else (255, 0, 255)
    cv2.rectangle(P, (int((x0 - X0 - 2) * k) + off, int((y0 - Y0 - 2) * k)), (int((x1 - X0 + 2) * k) + off, int((y1 - Y0 + 2) * k)), col, 1)
    C = np.full((CH, CW, 3), 255, np.uint8); C[14:14 + P.shape[0], :P.shape[1]] = P[:CH - 14, :CW]
    cv2.putText(C, f"#{a0 + i} {s['kind'][:9]} {s['px']}px {x0},{y0}", (2, 11), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 0, 0), 1)
    cells.append(C)
cols = 3; rows = (len(cells) + cols - 1) // cols
G = np.full((rows * (CH + 4), cols * (CW + 4), 3), 200, np.uint8)
for i, C in enumerate(cells):
    r, c = divmod(i, cols); G[r * (CH + 4):r * (CH + 4) + CH, c * (CW + 4):c * (CW + 4) + CW] = C
f = os.path.join(look.PICS, f'sheet_{tid}_{a0}.png'); cv2.imwrite(f, G); print(f, len(cells))
