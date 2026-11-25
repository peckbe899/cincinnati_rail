"""outlines_text.py (text/effect, 25 Nov 2026): bench44.py --outlines hook. Runs the REAL tools/sanborn/unet/outlines.py
(read, not changed) with a text mask applied in memory, from two environment variables:
  TEXT_MASK  a full-size 0/255 PNG (masks/...)
  TEXT_MODE  'lines': P(line) = 0 on the mask, right after the line map is read (so the seeds' cuts, the watershed, the
                      slide onto the line and the 'detected line' test all see the masked map)
             'ink':   the mask's pixels are not ink for the outline step's ink test (on_ink: 'on print' / 'not on a line')
             'both':  both;  'none': nothing (control: must give the stored runs)
Everything is written into RUN_DIR (outlines.py --out). Anchors are asserted to appear once.
    (called by bench44.py as)  PY outlines_text.py 44 AREA_PNG LINES_PNG RUN_DIR"""
import os, sys
ORIG = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/tools/sanborn/unet/outlines.py'
N, AREA, LINES, RUN = sys.argv[1:5]
mode = os.environ.get('TEXT_MODE', 'none'); mask = os.environ.get('TEXT_MASK', '')
assert mode in ('lines', 'ink', 'both', 'none'), mode
code = open(ORIG, encoding='utf8').read()
A1 = "pl = cv2.imread(ARG.lines_png or U + f'{N}_lines_{LINES}.png', 0)\n"
A2 = "hsv = cv2.cvtColor(full, cv2.COLOR_BGR2HSV); ink = (hsv[:, :, 2] < 120) | ((hsv[:, :, 1] < 90) & (hsv[:, :, 2] < 170))\n"
for a in (A1, A2): assert code.count(a) == 1, 'outlines.py changed: anchor not there once: ' + a
if mode != 'none':
    code = code.replace(A1, A1 + f"_TM = cv2.imread({mask!r}, 0) > 0; assert _TM.shape == pl.shape, (_TM.shape, pl.shape)\n"
                        + ("pl = pl.copy(); pl[_TM] = 0\n" if mode in ('lines', 'both') else ''))
    if mode in ('ink', 'both'): code = code.replace(A2, A2 + "ink &= ~_TM\n")
sys.argv = [ORIG, N, 'area_ng1', 'lines_ng1', '--area-png', AREA, '--lines-png', LINES, '--out', RUN]
g = {'__name__': '__main__', '__file__': ORIG}
exec(compile(code, ORIG, 'exec'), g)
