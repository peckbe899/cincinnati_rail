"""DEV ONLY (integrate, 26 Nov 2026): make the combined block variants of finder4.combine() from the stored dev runs.

    cd data/sanborn
    python -B bench_2026-11-26/text_fix/integrate/code/devcombine.py OUT_ROOT N [N ...]

Reads OUT_ROOT/A, OUT_ROOT/Bf and OUT_ROOT/Bx (devrun.py) and work/f3; writes OUT_ROOT/<mode>f and <mode>x for the modes
Ubox, Upix, Gbox, Gpix (f = B's final models, x = B's cross-fold models, only where Bx exists).
"""
import json, os, sys
sys.dont_write_bytecode = True
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from finder4 import combine  # noqa: E402

root, plates = sys.argv[1], sys.argv[2:]
F3 = os.path.join(HERE, '..', 'work', 'f3')
for N in plates:
    f3 = cv2.imread(os.path.join(F3, f'{N}_text.png'), cv2.IMREAD_UNCHANGED)
    oA = cv2.imread(os.path.join(root, 'A', f'{N}_text.png'), cv2.IMREAD_UNCHANGED); iA = json.load(open(os.path.join(root, 'A', f'{N}_text.json')))
    for b in ('f', 'x'):
        p = os.path.join(root, f'B{b}', f'{N}_text.png')
        if not os.path.exists(p): continue
        oB = cv2.imread(p, cv2.IMREAD_UNCHANGED); iB = json.load(open(os.path.join(root, f'B{b}', f'{N}_text.json')))
        for mode in ('Ubox', 'Upix', 'Gbox', 'Gpix'):
            out, rec = combine(f3, oA, iA, oB, iB, mode)
            d = os.path.join(root, mode + b); os.makedirs(d, exist_ok=True)
            cv2.imwrite(os.path.join(d, f'{N}_text.png'), out)
            json.dump(rec, open(os.path.join(d, f'{N}_text.json'), 'w', encoding='utf8', newline='\n'), indent=1)
            print(N, mode + b, rec, flush=True)
