"""Does taking the finder's text out first help the railroad rule? (25 Nov 2026, text/finder)

    cd data/sanborn
    python -B <this> N OUT_BINS.png [--mask FINDER_PNG]

Imports tools/sanborn/unet/ink_bins.py UNCHANGED and runs its main() with Ben's rail off (--no-ben) and --save, so the
plate's own N_bins.png is not touched. With --mask, the scan it reads (cufp/22-N.jpg) has every pixel the finder calls
text (codes 2, 3, 4) painted paper-white first, so ink_bins never sees that ink. Writes are guarded: only paths inside
text/finder may be written."""
import sys, os, builtins, importlib.util
sys.dont_write_bytecode = True
import numpy as np, cv2

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); SAFE = os.path.normcase(ROOT)
TOOLS = os.path.normpath(os.path.join(ROOT, '..', '..', '..', '..', '..', 'tools', 'sanborn', 'unet'))


def _safe(p):
    a = os.path.normcase(os.path.abspath(p))
    if not a.startswith(SAFE + os.sep): raise PermissionError(f'rail_with_mask.py: refusing to write outside text/finder: {p}')


_open = builtins.open
def _guarded_open(f, mode='r', *a, **k):
    if any(c in mode for c in 'wax+'): _safe(f)
    return _open(f, mode, *a, **k)
builtins.open = _guarded_open
_imw = cv2.imwrite
def _guarded_imwrite(p, *a, **k):
    _safe(p); return _imw(p, *a, **k)
cv2.imwrite = _guarded_imwrite
_rep = os.replace
def _guarded_replace(a, b):
    _safe(a); _safe(b); return _rep(a, b)
os.replace = _guarded_replace

N, out = sys.argv[1], sys.argv[2]; _safe(out)
mask = sys.argv[sys.argv.index('--mask') + 1] if '--mask' in sys.argv else None
_imr = cv2.imread
def _patched_imread(p, *a, **k):
    im = _imr(p, *a, **k)
    if mask and os.path.normcase(os.path.normpath(p)) == os.path.normcase(os.path.normpath(f'cufp/22-{N}.jpg')) and im is not None and im.ndim == 3:
        t = np.isin(_imr(mask, 0), (2, 3, 4)); im[t] = (232, 240, 246)   # paper (BGR), Lab L well above 140
        print(f'painted out {int(t.sum()):,} text px from {mask}', flush=True)
    return im
cv2.imread = _patched_imread
sys.path.append(TOOLS)
src = os.path.join(TOOLS, 'ink_bins.py')
spec = importlib.util.spec_from_file_location('ink_bins_under_test', src); ib = importlib.util.module_from_spec(spec); spec.loader.exec_module(ib)
sys.argv = [src, N, '--no-ben', '--save', out, '--json', out[:-4] + '.json']
print('module', src, '| argv', sys.argv[1:], '| mask', mask, flush=True)
ib.main()
