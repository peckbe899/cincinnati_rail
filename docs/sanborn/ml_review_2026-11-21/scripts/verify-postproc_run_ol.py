"""Run outlines.py's own code (exec of its source up to the writes) for plate N with AREA/LINES; dump polys + internals
to this scratch folder only. Reads the repo, writes nothing there.
python run_ol.py N AREA LINES"""
import json, os, sys, time, pickle
import numpy as np, cv2
OUT = os.path.dirname(os.path.abspath(__file__)) + '/'
REPO = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/'
src = open(REPO + 'tools/sanborn/unet/outlines.py', encoding='utf8').read()
cut = src.index("os.makedirs(SP + f'picks22_guided")
code = src[:cut]
assert 'json.dump' not in code and 'imwrite' not in code and 'os.replace' not in code
N, AREA, LINES = sys.argv[1:4]
sys.argv = ['outlines.py', N, AREA, LINES]
ns = {'__file__': REPO + 'tools/sanborn/unet/outlines.py', '__name__': 'olx'}
t0 = time.time()
exec(compile(code, 'outlines.py', 'exec'), ns)
polys = ns['polys']; cnt = ns['cnt']
share = round(cnt['len_ink'] / max(1.0, cnt['len_all']), 3)
print(json.dumps(dict(N=N, AREA=AREA, LINES=LINES, blocks=len(polys), sides=cnt['sides'], on_printed=cnt['on_printed_line'], short=cnt['short_pieces'], share=share, secs=round(time.time() - t0))))
json.dump(polys, open(OUT + f'ol_{N}_{AREA}_{LINES}.json', 'w'))
# also save the lp map and g (small: as png) for later gate tests
cv2.imwrite(OUT + f'lp_{N}_{LINES}.png', np.clip(ns['lp'], 0, 255).astype(np.uint8))
