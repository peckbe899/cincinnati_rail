"""Run ink_bins.py (the repo's own, copied to orig/, or the proposed one in proposed/) with every write redirected into
this folder (rail-rules, 21 Nov 2026). The module's code is not edited: this wrapper imports it, guards every file write
(only paths inside bench_2026-11-21/rail-rules are allowed, anything else raises), and calls its main().

    cd data/sanborn
    python bench_2026-11-21/rail-rules/run_ink_bins.py N OUT_BINS.png [--orig] [--nomap] [--rail JSON]

  --orig    orig/ink_bins.py (byte-identical copy of tools/sanborn/unet/ink_bins.py, sha de9b79144123, the batch's)
            instead of proposed/ink_bins.py
  --nomap   run as on a plate that was never placed: streetmap/22-N.json and unet_data/N_label.png are hidden from it
            (as the batch ran 104 of its plates; plate 44 and 1A are run this way for the benchmark)
  --rail    RAIL settings, passed on to ink_bins.py's own --rail
Ben's own tracks are always switched off (--no-ben), so the bins are the rules' alone."""
import sys, os, builtins, importlib.util
import cv2

HERE = os.path.dirname(os.path.abspath(__file__)); SAFE = os.path.normcase(HERE)


def _safe(p):
    a = os.path.normcase(os.path.abspath(p))
    if not a.startswith(SAFE + os.sep): raise PermissionError(f'run_ink_bins.py: refusing to write outside rail-rules: {p}')


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

N, out = sys.argv[1], sys.argv[2]; _safe(out); NOMAP = '--nomap' in sys.argv
src = os.path.join(HERE, 'orig' if '--orig' in sys.argv else 'proposed', 'ink_bins.py')
if NOMAP:
    _ex = os.path.exists
    os.path.exists = lambda p: False if (str(p).replace('\\', '/').startswith('streetmap/') or str(p).endswith('_label.png')) else _ex(p)
spec = importlib.util.spec_from_file_location('ink_bins_under_test', src); ib = importlib.util.module_from_spec(spec); spec.loader.exec_module(ib)
argv = [src, N, '--no-ben', '--save', out]
if '--rail' in sys.argv: argv += ['--rail', sys.argv[sys.argv.index('--rail') + 1]]
sys.argv = argv
print('module', src, '| nomap' if NOMAP else '', flush=True)
ib.main()
