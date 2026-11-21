"""merge/v-eye: how the staged merge is run for the eye check (21 November 2026). Read-only on the repo.

Every staged script runs with
  - the working directory data/sanborn (as the batch runs them; ink_bins.py reads relative paths),
  - PYTHONPATH = v-eye/shim (a copy of merge/impl/shim/_ws.py: the repo's DATA and CODE, no _mirror()) and then the
    repo's tools/sanborn/unet (edit_server.py etc.: read only, after the staged folder),
  - PYTHONDONTWRITEBYTECODE=1 and -B, so no __pycache__ is written beside the staged or the repo files,
  - every output redirected into merge/v-eye (outlines.py --out, blocks_noguide.py --out, ink_bins.py --save/--json).
"""
import os, subprocess, sys, json, hashlib
REPO = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/'
DATA = REPO + 'data/sanborn/'; U = DATA + 'unet_data/'; BENCH = DATA + 'bench_2026-11-21/'
MERGE = BENCH + 'merge/'; ME = MERGE + 'v-eye/'; STAGED = MERGE + 'staged/'; SU = STAGED + 'tools/sanborn/unet/'
SHIM = ME + 'shim'; RU = REPO + 'tools/sanborn/unet'
VPY = REPO + 'tools/sanborn/unet/.venv/Scripts/python.exe'; SYSPY = 'python'
A_CODE = BENCH + 'outline-quality/proposed/outlines_redirected.py'      # outline-quality (A), outputs to argv[4]
PLATES = ['90', '30', '23', '47', '21', '60B', '64A', '1B', '3', '5', '44']
GUIDED = {'43', '44', '45', '80', '82A'}


def env():
    e = dict(os.environ); e['PYTHONPATH'] = SHIM + os.pathsep + RU; e['PYTHONDONTWRITEBYTECODE'] = '1'; return e


def must_be_mine(p):
    a = os.path.abspath(p).replace('\\', '/')
    assert a.startswith(ME.rstrip('/')), f'output outside merge/v-eye: {a}'
    return a


def run(cmd, py):
    r = subprocess.run([py, '-B'] + cmd, cwd=DATA, capture_output=True, text=True, encoding='utf8', errors='replace', env=env())
    return r.returncode, r.stdout, r.stderr


def merged(N, out):
    """the staged block step 3+4 on the saved maps, every output into out"""
    must_be_mine(out)
    if N in GUIDED:   # blocks_noguide refuses a placed plate: run the staged outlines.py itself (as bench44 does)
        return run([SU + 'outlines.py', N, 'area_ng1', 'lines_ng1', '--out', out], VPY)
    return run([SU + 'blocks_noguide.py', N, '--outlines-only', '--out', out], VPY)


def run_A(N, out):
    must_be_mine(out); os.makedirs(out, exist_ok=True)
    return run([A_CODE, N, 'area_ng1', 'lines_ng1', out], VPY)


def ink_bins(N, save, edges, outlines, extra=()):
    must_be_mine(save); js = save[:-4] + '.json'; must_be_mine(js)
    return run([SU + 'ink_bins.py', N, '--save', save, '--json', js, '--edges', edges, '--outlines', outlines] + list(extra), SYSPY)


def sha16(p): return hashlib.sha256(open(p, 'rb').read()).hexdigest()[:16] if os.path.exists(p) else None


def step4_mod():
    """the staged blocks_noguide module (step4), imported without torch"""
    sys.path.insert(0, SHIM); sys.path.insert(1, SU); sys.path.append(RU)
    import _ws  # noqa: F401
    import blocks_noguide as BN
    assert os.path.abspath(BN.__file__).replace('\\', '/').startswith(SU.rstrip('/')), BN.__file__
    return BN
