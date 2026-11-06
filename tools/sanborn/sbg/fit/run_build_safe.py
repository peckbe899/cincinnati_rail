try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..', '..'))); import _ws
# runs build.py with a load() that skips picks files still being written (agents at work)
import sys, os, json, glob, runpy
HERE = _ws.data_dir(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, _ws.code_dir(HERE)); sys.path.insert(0, _ws.code_dir(os.path.dirname(HERE)))
import load as L
_orig_glob = glob.glob
SKIP = set(os.environ.get('SBG_ONLY_EXIST', '').split(',')) if os.environ.get('SBG_ONLY_EXIST') else None
def safe_glob(p, *a, **k):
    out = _orig_glob(p, *a, **k)
    if p.endswith('s*.json'):
        ok = []
        for f in out:
            try: json.load(open(f)); ok.append(f)
            except Exception: print('skip unreadable', f)
        return ok
    return out
L.glob.glob = safe_glob
sys.argv = [os.path.join(_ws.code_dir(HERE), 'build.py')]
runpy.run_path(os.path.join(_ws.code_dir(HERE), 'build.py'), run_name='__main__')
