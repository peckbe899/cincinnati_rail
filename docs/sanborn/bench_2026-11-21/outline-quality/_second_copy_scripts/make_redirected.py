"""outline-quality: make a runnable, output-redirected copy of a proposed outlines.py, by the same edits that turned
tools/sanborn/unet/outlines.py into the bench's outlines_copy.py (no `import _ws`, SP written out, AREA/LINES may be PNG
paths, a 4th argument OUTDIR takes every output). Every edit must apply exactly once.
    python make_redirected.py proposed/outlines.py proposed/outlines_redirected.py
The redirected copy is what check_proposed.py runs; the proposal itself is never run."""
import sys
src, dst = sys.argv[1], sys.argv[2]; s = open(src, encoding='utf8').read()
EDITS = [
    ("sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))\nimport _ws  # noqa: E402\nN, AREA, LINES = sys.argv[1], sys.argv[2], sys.argv[3]; SP = _ws.DATA; U = SP + 'unet_data/'\n",
     "N, AREA, LINES = sys.argv[1], sys.argv[2], sys.argv[3]; SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; U = SP + 'unet_data/'\n"
     "OUT = os.path.abspath(sys.argv[4]).replace('\\\\', '/') + '/'\n"
     "AREA_PNG = AREA if AREA.lower().endswith('.png') else U + f'{N}_pred_{AREA}.png'; LINES_PNG = LINES if LINES.lower().endswith('.png') else U + f'{N}_lines_{LINES}.png'\n"),
    ("pa = cv2.resize(cv2.imread(U + f'{N}_pred_{AREA}.png', 0), (W, H), interpolation=cv2.INTER_LINEAR)", "pa = cv2.resize(cv2.imread(AREA_PNG, 0), (W, H), interpolation=cv2.INTER_LINEAR)"),
    ("pl = cv2.imread(U + f'{N}_lines_{LINES}.png', 0)", "pl = cv2.imread(LINES_PNG, 0)"),
    ("os.makedirs(SP + f'picks22_guided/22-{N}', exist_ok=True)\njson.dump(polys, open(SP + f'picks22_guided/22-{N}/outlines.json', 'w', encoding='utf8', newline='\\n'))",
     "os.makedirs(OUT, exist_ok=True)\njson.dump(polys, open(OUT + 'outlines.json', 'w', encoding='utf8', newline='\\n'))"),
    ("json.dump(rep, open(U + f'{N}_outlines.json'", "json.dump(rep, open(OUT + f'{N}_outlines.json'"),
    ("cv2.imwrite(U + f'{N}_outlines.jpg'", "cv2.imwrite(OUT + f'{N}_outlines.jpg'"),
    ("cv2.imwrite(U + f'{N}_blockmask.png'", "cv2.imwrite(OUT + f'{N}_blockmask.png'"),
]
for a, b in EDITS:
    assert s.count(a) == 1, ('edit does not apply exactly once', a[:80], s.count(a))
    s = s.replace(a, b)
assert '_ws' not in s.split('"""', 2)[2] and "SP + f'picks22" not in s and "U + f'{N}_outlines" not in s and "U + f'{N}_blockmask" not in s
open(dst, 'w', encoding='utf8', newline='\n').write(s); print('wrote', dst)
