"""v-final hook for the ORIGINAL bench44 harness (bench_2026-11-21/bench44/bench44.py, copied unchanged into v-final/orig/):
    PY hook_outlines.py 44 AREA_PNG LINES_PNG RUN_DIR
runs the APPLIED merged outlines.py (merge/v-final/apply/..., byte-identical to merge/staged) with every output in RUN_DIR."""
import os, subprocess, sys
V = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-21/merge/v-final/'
N, area, lines, run = sys.argv[1:5]
assert os.path.abspath(run).replace(os.sep, '/').startswith(V), run
env = dict(os.environ, PYTHONPATH=V + 'shim' + os.pathsep + 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/tools/sanborn/unet', PYTHONDONTWRITEBYTECODE='1')
r = subprocess.run([sys.executable, '-B', V + 'apply/tools/sanborn/unet/outlines.py', N, 'area_ng1', 'lines_ng1', '--area-png', area, '--lines-png', lines, '--out', run],
                   capture_output=True, text=True, encoding='utf8', errors='replace', env=env)
sys.stdout.write(r.stdout); sys.stderr.write(r.stderr); sys.exit(r.returncode)
