"""v-final: run the APPLIED ink_bins.py with the v-final shim _ws loaded first (so no import reaches the repo's _ws.py,
whose _mirror() makes folders under data/sanborn). --save is required and every output must lie in merge/v-final.
    python -B run_ink.py N [ink_bins args ...]      (cwd data/sanborn)"""
import os, runpy, sys
V = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-21/merge/v-final/'
AU = V + 'apply/tools/sanborn/unet/'; RU = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/tools/sanborn/unet'
sys.path.insert(0, V + 'shim')
import _ws  # noqa: E402
assert os.path.abspath(_ws.__file__).replace(os.sep, '/').startswith(V + 'shim'), _ws.__file__
args = sys.argv[1:]
assert '--save' in args, 'without --save ink_bins.py writes unet_data/N_bins.png'
for k in ('--save', '--json', '--pic'):
    if k in args: assert os.path.abspath(args[args.index(k) + 1]).replace(os.sep, '/').startswith(V), args[args.index(k) + 1]
sys.path.remove(V + 'shim'); sys.path.insert(0, AU); sys.path.append(RU)
sys.argv = [AU + 'ink_bins.py'] + args
runpy.run_path(AU + 'ink_bins.py', run_name='__main__')
assert sys.modules['_ws'] is _ws
