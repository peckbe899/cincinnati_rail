"""merge/impl: how the staged code is run in tests (21 November 2026). Read-only on the repo.

Every staged script runs with
  - the working directory data/sanborn (as the batch runs them; ink_bins.py reads relative paths),
  - PYTHONPATH = impl/shim (a _ws.py with the repo's DATA and CODE but no _mirror(), so nothing is made under
    data/sanborn) and then the repo's tools/sanborn/unet (edit_server.py, unet.py: read only, after the staged folder),
  - PYTHONDONTWRITEBYTECODE=1 and -B, so no __pycache__ is written beside the staged or the repo files,
  - every output redirected into merge/impl (outlines.py --out, ink_bins.py --save/--json, blocks_noguide.py --out).
"""
import os, subprocess, sys, json, hashlib
REPO = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/'
DATA = REPO + 'data/sanborn/'; U = DATA + 'unet_data/'
MERGE = DATA + 'bench_2026-11-21/merge/'; IMPL = MERGE + 'impl/'; STAGED = MERGE + 'staged/'; SU = STAGED + 'tools/sanborn/unet/'
SHIM = IMPL + 'shim'; RU = REPO + 'tools/sanborn/unet'
VPY = REPO + 'tools/sanborn/unet/.venv/Scripts/python.exe'; SYSPY = 'python'


def env():
    e = dict(os.environ); e['PYTHONPATH'] = SHIM + os.pathsep + RU; e['PYTHONDONTWRITEBYTECODE'] = '1'; return e


def must_be_mine(p):
    a = os.path.abspath(p).replace('\\', '/')
    assert a.startswith(IMPL.rstrip('/')), f'output outside merge/impl: {a}'
    return a


def outlines(N, out, area=None, lines=None, extra=(), py=VPY, code=SU + 'outlines.py'):
    """the staged outline step on plate N, every output into `out`"""
    must_be_mine(out); cmd = [py, '-B', code, N, 'area_ng1', 'lines_ng1', '--out', out] + (['--area-png', area] if area else []) + (['--lines-png', lines] if lines else []) + list(extra)
    r = subprocess.run(cmd, cwd=DATA, capture_output=True, text=True, encoding='utf8', errors='replace', env=env())
    if r.returncode: raise RuntimeError(f'outlines {N}: ' + (r.stderr + r.stdout)[-3000:])
    return json.loads(r.stdout.strip().splitlines()[-1])


def ink_bins(N, save, extra=(), py=SYSPY, code=SU + 'ink_bins.py'):
    """the staged ink sorting with --save (never N_bins.json), counts to save[:-4] + '.json'"""
    must_be_mine(save); js = save[:-4] + '.json'
    cmd = [py, '-B', code, N, '--save', save, '--json', js] + list(extra)
    r = subprocess.run(cmd, cwd=DATA, capture_output=True, text=True, encoding='utf8', errors='replace', env=env())
    if r.returncode: raise RuntimeError(f'ink_bins {N}: ' + (r.stderr + r.stdout)[-3000:])
    return r.stdout, (json.load(open(js, encoding='utf8')) if os.path.exists(js) else None)


def sha16(p): return hashlib.sha256(open(p, 'rb').read()).hexdigest()[:16] if os.path.exists(p) else None


def step4_mod():
    """the staged blocks_noguide module (step4, outline_version), imported without torch"""
    sys.path.insert(0, SHIM); sys.path.insert(1, SU); sys.path.append(RU)
    import _ws  # noqa: F401  (the shim)
    import blocks_noguide as BN
    assert os.path.abspath(BN.__file__).replace('\\', '/').startswith(SU.rstrip('/')), BN.__file__
    return BN


def edit_server():
    step4_mod()
    import edit_server as ES  # the repo's (read only), with the shim _ws already imported
    return ES
