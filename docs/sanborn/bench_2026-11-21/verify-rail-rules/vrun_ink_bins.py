"""verify-rail-rules (21 Nov 2026): run ink_bins.py from this folder's orig/ (a plain cp of tools/sanborn/unet/ink_bins.py)
or patched/ (that cp with rail-rules/diffs/rail_rules.diff applied by `patch -p1`), with every write guarded so that only
paths inside verify-rail-rules are allowed. Written independently of rail-rules/run_ink_bins.py, same idea.

    cd data/sanborn
    python bench_2026-11-21/verify-rail-rules/vrun_ink_bins.py N OUT_BINS.png orig|patched [--nomap]

--nomap hides streetmap/22-N.json and unet_data/N_label.png (a plate never placed). Ben's tracks are always off (--no-ben)."""
import sys, os, builtins, importlib.util
import cv2

HERE = os.path.dirname(os.path.abspath(__file__)); SAFE = os.path.normcase(HERE)


def _safe(p):
    a = os.path.normcase(os.path.abspath(p))
    if not a.startswith(SAFE + os.sep): raise PermissionError(f'refusing to write outside verify-rail-rules: {p}')


_open = builtins.open
def _gopen(f, mode='r', *a, **k):
    if any(c in mode for c in 'wax+'): _safe(f)
    return _open(f, mode, *a, **k)
builtins.open = _gopen
_imw = cv2.imwrite
cv2.imwrite = lambda p, *a, **k: (_safe(p), _imw(p, *a, **k))[1]
_rep = os.replace
os.replace = lambda a, b: (_safe(a), _safe(b), _rep(a, b))[2]

N, out, which = sys.argv[1], sys.argv[2], sys.argv[3]; _safe(out); assert which in ('orig', 'patched')
if '--nomap' in sys.argv:
    _ex = os.path.exists
    os.path.exists = lambda p: False if (str(p).replace('\\', '/').startswith('streetmap/') or str(p).endswith('_label.png')) else _ex(p)
src = os.path.join(HERE, which, 'ink_bins.py')
spec = importlib.util.spec_from_file_location('ib_' + which, src); ib = importlib.util.module_from_spec(spec); spec.loader.exec_module(ib)
sys.argv = [src, N, '--no-ben', '--save', out]
print('module', src, '| python', sys.executable, '| cv2', cv2.__version__, flush=True)
ib.main()
