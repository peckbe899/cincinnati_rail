"""merge/impl/r2: run the staged ink_bins.py with the shim _ws loaded first (21 Nov 2026; as merge/v-eye/scripts/run_ink.py).

    python -B run_ink.py N [ink_bins args ...]      (cwd data/sanborn, as the batch runs it)

ink_bins.py's fallback imports blocks_noguide.py and street_map.py; street_map imports the repo's edit_server.py, which
puts tools/sanborn on sys.path[0] and imports _ws: that would be the repo's _ws.py, whose _mirror() makes folders under
data/sanborn. With the shim already in sys.modules every import gets the shim (same DATA and CODE, no _mirror). --save
is required and every output must lie in merge/impl/r2.
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
sys.path.remove(HERE); sys.path.remove(C.SHIM); sys.path.append(C.RU)
sys.argv = [C.SU + 'ink_bins.py'] + args
runpy.run_path(C.SU + 'ink_bins.py', run_name='__main__')
assert sys.modules['_ws'] is _ws
