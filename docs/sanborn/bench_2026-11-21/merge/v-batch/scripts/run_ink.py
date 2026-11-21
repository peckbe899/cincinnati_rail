"""merge/v-batch: run the staged ink_bins.py with the shim _ws already imported (21 November 2026).

    python -B run_ink.py N [ink_bins.py options]      (cwd data/sanborn; always with --save into merge/v-batch)

ink_bins.py imports street_map.py, which imports the repo's edit_server.py, which puts tools/sanborn first on sys.path
and imports _ws. The repo's _ws.py makes folders under data/sanborn on import (_mirror). With the shim imported first,
that import is the shim and nothing is made. Refuses to run without --save inside merge/v-batch (no N_bins.json then).
"""
import os, runpy, sys
ME = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-21/merge/v-batch/'
INK = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-21/merge/staged/tools/sanborn/unet/ink_bins.py'
sys.path.insert(0, ME + 'shim')
import _ws  # noqa: E402
assert os.path.abspath(_ws.__file__).replace('\\', '/').startswith(ME.rstrip('/')), _ws.__file__
a = sys.argv[1:]
assert '--save' in a and os.path.abspath(a[a.index('--save') + 1]).replace('\\', '/').startswith(ME.rstrip('/')), 'needs --save into merge/v-batch'
if '--json' in a: assert os.path.abspath(a[a.index('--json') + 1]).replace('\\', '/').startswith(ME.rstrip('/'))
assert '--pic' not in a or os.path.abspath(a[a.index('--pic') + 1]).replace('\\', '/').startswith(ME.rstrip('/'))
sys.path.remove(ME + 'shim'); sys.argv = [INK] + a
runpy.run_path(INK, run_name='__main__')
