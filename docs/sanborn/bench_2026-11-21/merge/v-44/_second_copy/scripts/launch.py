"""v-44 launcher: python -B launch.py SCRIPT.py ARGS...  runs SCRIPT as __main__ after importing the v-44 shim as _ws, so
nothing the script imports (street_map -> edit_server -> _ws) can reach the repo's _ws.py, whose import makes folders
under data/sanborn. Run with cwd data/sanborn and PYTHONDONTWRITEBYTECODE=1."""
import os, runpy, sys
SHIM = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-21/merge/v-44/shim'
sys.path.insert(0, SHIM)
import _ws  # noqa: E402,F401
assert os.path.abspath(_ws.__file__).replace('\\', '/').startswith(SHIM), _ws.__file__
sys.path.remove(SHIM)
target = os.path.abspath(sys.argv[1]); sys.argv = sys.argv[1:]
runpy.run_path(target, run_name='__main__')
