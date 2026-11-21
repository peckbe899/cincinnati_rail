"""Make outlines_bench_final.py from outlines_proposed.py (the proposed tools/sanborn/unet/outlines.py) by changing only its
input/output lines, so the code that is measured is the code in the diff:

    python make_bench_copy.py        -> outlines_bench_final.py ; then `diff outlines_proposed.py outlines_bench_final.py`

The copy is run as   PY outlines_bench_final.py N AREA LINES OUTDIR [MASK_CACHE_DIR]
  - `import _ws` dropped, SP written out; AREA / LINES may be a network name or a PNG path (as bench44's outlines_copy.py)
  - every output into OUTDIR (outlines.json, N_outlines.json, N_outlines.jpg, N_blockmask.png)
  - optional 5th argument: a folder with map_area.py's 1/8 masks (N_mask8.png); resized with INTER_NEAREST they are
    exactly map_area.map_mask (visual-pdf), so runs on many sheets need not run map_area.py again. Without it the copy
    imports map_area.py as the proposed file does (from its own folder, else bench_2026-11-21/visual-pdf).
"""
import os
HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, 'outlines_proposed.py'), encoding='utf8').read()
REPL = [
    ("\"\"\"Block outlines of a plate from the two networks (15 November 2026).\n",
     "\"\"\"Block outlines of a plate from the two networks (15 November 2026).\n\nBENCH COPY of outlines_proposed.py made by make_bench_copy.py (bench_2026-11-21/outline-nesting): only the input/output lines\n"
     "differ. Run as: PY outlines_bench_final.py N AREA LINES OUTDIR [MASK_CACHE_DIR]. The proposed file's docstring follows.\n"),
    ("sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))\nimport _ws  # noqa: E402\n"
     "N, AREA, LINES = sys.argv[1], sys.argv[2], sys.argv[3]; SP = _ws.DATA; U = SP + 'unet_data/'; HERE = os.path.dirname(os.path.abspath(__file__))\n",
     "N, AREA, LINES = sys.argv[1], sys.argv[2], sys.argv[3]; SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; U = SP + 'unet_data/'; HERE = os.path.dirname(os.path.abspath(__file__))\n"
     "OUT = os.path.abspath(sys.argv[4]).replace('\\\\', '/') + '/'; MASK_CACHE = sys.argv[5] if len(sys.argv) > 5 else None\n"
     "AREA_PNG = AREA if AREA.lower().endswith('.png') else U + f'{N}_pred_{AREA}.png'; LINES_PNG = LINES if LINES.lower().endswith('.png') else U + f'{N}_lines_{LINES}.png'\n"),
    ("pa = cv2.resize(cv2.imread(U + f'{N}_pred_{AREA}.png', 0), (W, H), interpolation=cv2.INTER_LINEAR)\npl = cv2.imread(U + f'{N}_lines_{LINES}.png', 0)\n",
     "pa = cv2.resize(cv2.imread(AREA_PNG, 0), (W, H), interpolation=cv2.INTER_LINEAR)\npl = cv2.imread(LINES_PNG, 0)\n"),
    ("if PDF:                                                  # an uncut sheet",
     "if PDF and MASK_CACHE: alpha = cv2.resize(cv2.imread(os.path.join(MASK_CACHE, f'{N}_mask8.png'), 0), (W, H), interpolation=cv2.INTER_NEAREST) > 127\n"
     "elif PDF:                                                # an uncut sheet"),
    ("os.makedirs(SP + f'picks22_guided/22-{N}', exist_ok=True)\njson.dump(polys, open(SP + f'picks22_guided/22-{N}/outlines.json', 'w', encoding='utf8', newline='\\n'))\n",
     "os.makedirs(OUT, exist_ok=True)\njson.dump(polys, open(OUT + 'outlines.json', 'w', encoding='utf8', newline='\\n'))\n"),
    ("json.dump(rep, open(U + f'{N}_outlines.json'", "json.dump(rep, open(OUT + f'{N}_outlines.json'"),
    ("cv2.imwrite(U + f'{N}_outlines.jpg'", "cv2.imwrite(OUT + f'{N}_outlines.jpg'"),
    ("cv2.imwrite(U + f'{N}_blockmask.png'", "cv2.imwrite(OUT + f'{N}_blockmask.png'"),
]
for a, b in REPL:
    assert src.count(a) == 1, ('not found once', a[:80]); src = src.replace(a, b)
assert '_ws' not in src.split('"""', 2)[2] and 'picks22_guided/22-' not in src.split('"""', 2)[2]
open(os.path.join(HERE, 'outlines_bench_final.py'), 'w', encoding='utf8', newline='\n').write(src)
print('written outlines_bench_final.py')
