"""merge/v-eye: run the staged ink_bins.py with the shim _ws loaded first (21 Nov 2026).

    python -B run_ink.py N [ink_bins args ...]      (run from data/sanborn, as the batch runs it)

ink_bins.py's fallback imports street_map.py, which imports the repo's edit_server.py, which puts tools/sanborn on
sys.path[0] and imports _ws: that would be the repo's _ws.py, whose _mirror() makes folders under data/sanborn. With the
shim already in sys.modules, edit_server gets the shim (same DATA and CODE, no _mirror). Every output is checked to lie
in merge/v-eye before the run.
"""
import os, runpy, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import common as C  # noqa: E402
sys.path.insert(0, C.SHIM)
import _ws  # noqa: E402,F401
assert os.path.abspath(_ws.__file__).replace('\\', '/').startswith(C.SHIM), _ws.__file__
args = sys.argv[1:]
assert '--save' in args, 'without --save ink_bins.py writes unet_data/N_bins.png'
for k in ('--save', '--json', '--pic'):
    if k in args: C.must_be_mine(args[args.index(k) + 1])
sys.path.append(C.RU)
sys.argv = [C.SU + 'ink_bins.py'] + args
runpy.run_path(C.SU + 'ink_bins.py', run_name='__main__')
assert sys.modules['_ws'] is _ws
