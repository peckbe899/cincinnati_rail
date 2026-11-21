"""outlines.py's own code with SLIDE/TURN replaced (exec), polys to scratch. python run_ol_var.py N AREA LINES SLIDE TURN"""
import json, os, sys, time
import numpy as np, cv2
OUT = os.path.dirname(os.path.abspath(__file__)) + '/'
REPO = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/'
src = open(REPO + 'tools/sanborn/unet/outlines.py', encoding='utf8').read()
code = src[:src.index("os.makedirs(SP + f'picks22_guided")]
N, AREA, LINES, SL, TU = sys.argv[1:6]
old = 'SEED_B, SEED_S, TOL, MINLEN, SLIDE, TURN, CORNER, MIN_AREA, CUT = 14, 8, 8.0, 60.0, 12, 5, 120.0, 6000, 130.0'
assert old in code
code = code.replace(old, f'SEED_B, SEED_S, TOL, MINLEN, SLIDE, TURN, CORNER, MIN_AREA, CUT = 14, 8, 8.0, 60.0, {SL}, {TU}, 120.0, 6000, 130.0')
sys.argv = ['outlines.py', N, AREA, LINES]; ns = {'__file__': REPO + 'tools/sanborn/unet/outlines.py', '__name__': 'olx'}; t0 = time.time()
exec(compile(code, 'outlines.py', 'exec'), ns)
print(json.dumps(dict(SLIDE=SL, TURN=TU, blocks=len(ns['polys']), sides=ns['cnt']['sides'], secs=round(time.time() - t0))))
json.dump(ns['polys'], open(OUT + f'ol_{N}_{AREA}_{LINES}_s{SL}.json', 'w'))
