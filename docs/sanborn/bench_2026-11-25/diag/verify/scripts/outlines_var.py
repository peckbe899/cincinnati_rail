"""outlines_var.py (diag/verify, 25 Nov 2026): bench44.py --outlines hook. Runs the REAL tools/sanborn/unet/outlines.py
(read, not changed) with some of its constants overridden from the environment variable OUTLINE_VAR, e.g.
OUTLINE_VAR="SEED_B=10" or "MK_SEED_MIN=4000". The override is inserted right after the constants' lines in memory; the
file on disk is untouched, and everything is written into RUN_DIR (outlines.py --out).
    (called by bench44.py as)  PY outlines_var.py 44 AREA_PNG LINES_PNG RUN_DIR
"""
import os, re, sys
ORIG = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/tools/sanborn/unet/outlines.py'
N, AREA, LINES, RUN = sys.argv[1:5]
var = os.environ.get('OUTLINE_VAR', '').strip()
code = open(ORIG, encoding='utf8').read()
anchor = 'MK_CUT, MK_SEED_MIN = 3, 2000'
assert code.count(anchor) == 1, 'outlines.py changed: the constants line is not there once'
over = ''
if var:
    for kv in var.split(','):
        k, v = kv.split('=')
        assert re.fullmatch(r'[A-Z_]+', k.strip()) and re.fullmatch(r'[0-9.]+', v.strip()), kv
        over += chr(10) + f'{k.strip()} = {v.strip()}'
i = code.index(anchor); j = code.index('\n', i)
code = code[:j] + over + code[j:]
sys.argv = [ORIG, N, 'area_ng1', 'lines_ng1', '--area-png', AREA, '--lines-png', LINES, '--out', RUN]
g = {'__name__': '__main__', '__file__': ORIG}
exec(compile(code, ORIG, 'exec'), g)
