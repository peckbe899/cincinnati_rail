"""v-44 hook for the ORIGINAL bench44.py --outlines: PY FILE 44 AREA_PNG LINES_PNG RUN_DIR  ->  the STAGED outlines.py
run as  PY -B outlines.py 44 area_ng1 lines_ng1 --area-png AREA_PNG --lines-png LINES_PNG --out RUN_DIR  (+ extra options).

Environment (optional):
  V44_OUTLINES_PY    another outlines.py (an ablation copy in v-44); default the staged one
  V44_OUTLINE_ARGS   JSON list of extra outlines.py options, e.g. ["--hole-parent", "1e-9"] or ["--bins-png", "none"]
  V44_EXTRA_PATH     JSON list of folders put on PYTHONPATH after the shim (for an ablation copy: the staged folder)
Writes RUN_DIR/hook.json (the command). Nothing outside RUN_DIR (which must be in v-44)."""
import json, os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import STAGED, DATA, mine, env, sha16  # noqa: E402

N, AREA, LINES, RUN = sys.argv[1:5]; RUN = mine(RUN) + '/'
code = os.environ.get('V44_OUTLINES_PY', STAGED + 'outlines.py')
extra = json.loads(os.environ.get('V44_OUTLINE_ARGS', '[]')); xp = json.loads(os.environ.get('V44_EXTRA_PATH', '[]'))
cmd = [sys.executable, '-B', code, N, 'area_ng1', 'lines_ng1', '--area-png', AREA, '--lines-png', LINES, '--out', RUN] + extra
r = subprocess.run(cmd, cwd=DATA, capture_output=True, text=True, encoding='utf8', errors='replace', env=env(xp))
json.dump(dict(cmd=cmd, code_sha=sha16(code), returncode=r.returncode, extra_path=xp), open(RUN + 'hook.json', 'w'), indent=1)
sys.stdout.write(r.stdout); sys.stderr.write(r.stderr); sys.exit(r.returncode)
