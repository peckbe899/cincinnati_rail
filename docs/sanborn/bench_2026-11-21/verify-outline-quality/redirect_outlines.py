"""verify-outline-quality (21 Nov 2026): make an output-redirected, runnable copy of an outlines.py (current or patched),
independently of outline-quality/make_redirected.py. Only I/O lines change; each edit must apply exactly once.
    python redirect_outlines.py SRC.py DST.py
DST runs as:  PYTHON DST.py N AREA_PNG_or_name LINES_PNG_or_name OUTDIR   (cwd anything)
Outputs (outlines.json, N_outlines.json/.jpg, N_blockmask.png) all go to OUTDIR; nothing is written into the repo."""
import sys
src, dst = sys.argv[1], sys.argv[2]
s = open(src, encoding='utf8').read()
SPV = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
E = [
    ("sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))\n", ""),
    ("import _ws  # noqa: E402\n", ""),
    ("SP = _ws.DATA; U = SP + 'unet_data/'",
     f"SP = '{SPV}'; U = SP + 'unet_data/'; OUT = os.path.abspath(sys.argv[4]).replace(chr(92), '/') + '/'; os.makedirs(OUT, exist_ok=True)"),
    ("cv2.imread(U + f'{N}_pred_{AREA}.png', 0)", "cv2.imread(AREA if AREA.endswith('.png') else U + f'{N}_pred_{AREA}.png', 0)"),
    ("cv2.imread(U + f'{N}_lines_{LINES}.png', 0)", "cv2.imread(LINES if LINES.endswith('.png') else U + f'{N}_lines_{LINES}.png', 0)"),
    ("os.makedirs(SP + f'picks22_guided/22-{N}', exist_ok=True)\n", ""),
    ("open(SP + f'picks22_guided/22-{N}/outlines.json', 'w'", "open(OUT + 'outlines.json', 'w'"),
    ("open(U + f'{N}_outlines.json', 'w'", "open(OUT + f'{N}_outlines.json', 'w'"),
    ("cv2.imwrite(U + f'{N}_outlines.jpg'", "cv2.imwrite(OUT + f'{N}_outlines.jpg'"),
    ("cv2.imwrite(U + f'{N}_blockmask.png'", "cv2.imwrite(OUT + f'{N}_blockmask.png'"),
]
for a, b in E:
    assert s.count(a) == 1, (a, s.count(a)); s = s.replace(a, b)
body = s.split('"""', 2)[2]
for bad in ('_ws', "SP + f'picks22", "U + f'{N}_outlines", "U + f'{N}_blockmask", "open(U +", "imwrite(U +"):
    assert bad not in body, bad
open(dst, 'w', encoding='utf8', newline='\n').write(s); print('wrote', dst)
