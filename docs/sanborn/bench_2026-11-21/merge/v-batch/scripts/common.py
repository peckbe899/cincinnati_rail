"""merge/v-batch: how the staged merge is run in this check (21 November 2026). Read-only on the repo.

Every staged script runs with
  - the working directory data/sanborn (as run_plates.py runs them),
  - PYTHONPATH = v-batch/shim (a _ws.py with the repo's DATA and CODE but no _mirror()) then the repo's
    tools/sanborn/unet (edit_server.py, read only; the staged folder comes first, the scripts put it on sys.path),
  - PYTHONDONTWRITEBYTECODE=1 and -B (no __pycache__ beside the staged or repo files), CUDA hidden,
  - every output redirected into merge/v-batch (blocks_noguide.py --out, ink_bins.py --save/--json).
"""
import hashlib, json, os, re, subprocess, sys
REPO = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/'
DATA = REPO + 'data/sanborn/'; U = DATA + 'unet_data/'; G = DATA + 'picks22_guided/'
BENCH = DATA + 'bench_2026-11-21/'; MERGE = BENCH + 'merge/'; ME = MERGE + 'v-batch/'
STAGED = MERGE + 'staged/'; SU = STAGED + 'tools/sanborn/unet/'
SHIM = ME + 'shim'; RU = REPO + 'tools/sanborn/unet'
VPY = REPO + 'tools/sanborn/unet/.venv/Scripts/python.exe'; SYSPY = 'python'
PLACED = {'43', '44', '45', '80', '82A'}


def env():
    e = dict(os.environ); e['PYTHONPATH'] = SHIM + os.pathsep + RU; e['PYTHONDONTWRITEBYTECODE'] = '1'; e['CUDA_VISIBLE_DEVICES'] = ''
    return e


def mine(p):
    a = os.path.abspath(p).replace('\\', '/')
    assert a.startswith(ME.rstrip('/')), f'output outside merge/v-batch: {a}'
    return a


def order(n):
    m = re.match(r'(\d+)(.*)', n); return int(m.group(1)), m.group(2)


def plates104():
    st = json.load(open(U + 'run_plates.json', encoding='utf8'))
    return sorted((n for n in st if n not in PLACED), key=order)


def is_pdf(n):
    f = DATA + f'cufp/{n}/source.json'
    return os.path.exists(f) and json.load(open(f, encoding='utf8')).get('source') == 'pdf'


SCALE = json.load(open(STAGED + 'data/sanborn/scale_table.json', encoding='utf8'))


def group(n):
    ft = (SCALE.get(n) or {}).get('ft_per_inch')
    if ft == 400: return '400 ft'
    return f"{'PDF' if is_pdf(n) else 'cut'} {ft} ft"


def sha16(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()[:16] if os.path.exists(p) else None


def step4_mod():
    """the staged blocks_noguide module (step4), imported without torch, with the shim _ws"""
    for p in (SU, SHIM):
        if p not in sys.path: sys.path.insert(0, p)
    if RU not in sys.path: sys.path.append(RU)
    import _ws  # noqa: F401
    assert os.path.abspath(_ws.__file__).replace('\\', '/').startswith(ME.rstrip('/')), _ws.__file__
    import blocks_noguide as BN
    assert os.path.abspath(BN.__file__).replace('\\', '/').startswith(SU.rstrip('/')), BN.__file__
    return BN


def edit_server():
    step4_mod()
    import edit_server as ES  # the repo's (read only); the shim _ws is already imported, so no _mirror()
    import _ws
    assert os.path.abspath(_ws.__file__).replace('\\', '/').startswith(ME.rstrip('/')), _ws.__file__
    return ES
