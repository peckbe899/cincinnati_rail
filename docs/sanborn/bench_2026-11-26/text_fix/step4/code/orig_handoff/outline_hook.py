"""outline_hook.py (text_v1/handoff, 26 Nov 2026): the --outlines hook for bench44.py / bench_plate_text.py. Runs the hand-off
copy of the outline step (outlines_text.py, beside this file) on the given maps into RUN_DIR, with the text mask taken
from two environment variables:
  HANDOFF_TEXT_MASK   a finder hand-off code PNG (handoff/masks/N_text.png); empty or unset: no mask (the control run,
                      which must give the stored runs of the real outlines.py)
  HANDOFF_TEXT_DROP   --text-drop for the copy (default 0.5; 0: the on-ink test only, no 'on text' drop)
  HANDOFF_TEXT_WHERE  --text-where for the copy (default both; states: the shape step keeps the unmasked ink)
    (called by bench44.py as)  PY outline_hook.py N AREA_PNG LINES_PNG RUN_DIR"""
import os, sys, runpy
HERE = os.path.dirname(os.path.abspath(__file__))
N, AREA, LINES, RUN = sys.argv[1:5]
mask = os.environ.get('HANDOFF_TEXT_MASK', ''); drop = os.environ.get('HANDOFF_TEXT_DROP', '0.5')
argv = [os.path.join(HERE, 'outlines_text.py'), N, 'area_ng1', 'lines_ng1', '--area-png', AREA, '--lines-png', LINES, '--out', RUN]
if mask: argv += ['--text-mask', mask, '--text-drop', drop, '--text-where', os.environ.get('HANDOFF_TEXT_WHERE', 'both')]
sys.argv = argv
runpy.run_path(argv[0], run_name='__main__')
