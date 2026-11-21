"""v-44: paths and the safe way to run the staged merge code (21 Nov 2026). Read-only on the repo.

Every staged run: cwd data/sanborn, PYTHONPATH = v-44/shim (+ the repo's tools/sanborn/unet for edit_server only, after
the staged folder), PYTHONDONTWRITEBYTECODE=1 and -B, every output into v-44 (checked by mine())."""
import os, json, hashlib
REPO = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/'
DATA = REPO + 'data/sanborn/'; U = DATA + 'unet_data/'
BENCH = DATA + 'bench_2026-11-21/'; MERGE = BENCH + 'merge/'; V = MERGE + 'v-44/'
STAGED = MERGE + 'staged/tools/sanborn/unet/'; SHIM = V + 'shim'; RU = REPO + 'tools/sanborn/unet'
VPY = REPO + 'tools/sanborn/unet/.venv/Scripts/python.exe'; SYSPY = 'python'
GRIDS = ['batch'] + [f'off{i}_tta1' for i in range(1, 6)]
MAPS = BENCH + 'inference/maps/'


def mine(p):
    a = os.path.abspath(p).replace('\\', '/')
    assert a.startswith(V.rstrip('/')), f'output outside v-44: {a}'
    return a


def env(extra_path=()):
    e = dict(os.environ); e['PYTHONPATH'] = os.pathsep.join([SHIM, *extra_path, RU]); e['PYTHONDONTWRITEBYTECODE'] = '1'; return e


def sha16(p): return hashlib.sha256(open(p, 'rb').read()).hexdigest()[:16] if os.path.exists(p) else None
