"""Where the Sanborn pipeline's files are (the scripts' only path module).

The scripts were written in the Topography conversation's workspace, where every file sat under one root
(`/tmp/claude-0/-home-claude/9669db83-.../scratchpad/`, named SP or S in the scripts) and Ben's scans were
uploads under `/mnt/user-data/uploads/`. In the repo the same tree is split in two, each keeping the workspace's
relative paths:

    tools/sanborn/<path>   the scripts (.py, .sh, .js)                      CODE
    data/sanborn/<path>    everything else (picks, config, models, inputs)  DATA

so `SP + 'cufp/config.json'` is now `data/sanborn/cufp/config.json`, and `sys.path.insert(0, SP + 'cuf')` became
`sys.path.insert(0, _ws.CODE + 'cuf')`. Ben's local folders, and what each `/mnt/user-data/...` path stands for,
are in `configs/sanborn_paths.json`; `ext()` maps them.

Run scripts with data/sanborn as the working directory, as they were run from the workspace root:

    cd data/sanborn
    python ../../tools/sanborn/cuf/x1904.py ...

`python tools/sanborn/_ws.py` prints the resolved roots and checks the mapped folders exist.
"""
import json
import os

CODE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(CODE_DIR, '..', '..'))
CONFIG_FILE = os.path.join(REPO, 'configs', 'sanborn_paths.json')
CFG = json.load(open(CONFIG_FILE, encoding='utf8'))


_VARS = {k: v for k, v in CFG.items() if isinstance(v, str) and k != 'about'}
for _ in range(5):   # entries may name other entries ({cincinnati_rail}/Historic_Topo)
    _VARS = {k: v.format(**_VARS) for k, v in _VARS.items()}


def _abs(p):
    p = p.format(**_VARS)
    return os.path.normpath(p if os.path.isabs(p) else os.path.join(REPO, p)).replace('\\', '/')


DATA = _abs(CFG['workspace']) + '/'     # was the workspace root SP / S (with its trailing slash)
CODE = _abs(CFG['tools']) + '/'         # the same tree's scripts

_MNT = sorted(((k, _abs(v)) for k, v in CFG['mnt'].items()), key=lambda kv: -len(kv[0]))


def ext(p):
    """a path the scripts knew as /mnt/user-data/... -> Ben's local copy (configs/sanborn_paths.json, "mnt");
    anything else is returned unchanged"""
    if not isinstance(p, str) or not p.startswith('/mnt/user-data/'):
        return p
    for k, v in _MNT:
        kk = k.rstrip('/')
        if p == kk or p.startswith(kk + '/'):
            return v + p[len(kk):]
    raise KeyError(f'{p}: no local folder for it in {CONFIG_FILE} ("mnt")')


def _rel(p, root):
    p = os.path.abspath(p).replace('\\', '/')
    r = root.rstrip('/')
    pc, rc = os.path.normcase(p).replace('\\', '/'), os.path.normcase(r).replace('\\', '/')
    if pc != rc and not pc.startswith(rc + '/'):
        raise ValueError(f'{p} is not under {r}')
    return p[len(r):]


def data_dir(p):
    """a folder of tools/sanborn -> the same folder of data/sanborn (for scripts that found their data beside them)"""
    return DATA.rstrip('/') + _rel(p, CODE)


def code_dir(p):
    """a folder of data/sanborn -> the same folder of tools/sanborn (for sys.path and script paths)"""
    return CODE.rstrip('/') + _rel(p, DATA)


def _mirror():
    """every scripts folder has its data folder, as it did in the workspace (a script may write into a folder that
    held only scripts)"""
    for d, _, _ in os.walk(CODE):
        rel = _rel(d, CODE)
        if '__pycache__' in rel:
            continue
        os.makedirs(DATA.rstrip('/') + rel, exist_ok=True)


_mirror()

if __name__ == '__main__':
    print('DATA', DATA)
    print('CODE', CODE)
    for k, v in _MNT:
        print(('ok     ' if os.path.exists(v) else 'MISSING'), k, '->', v)
