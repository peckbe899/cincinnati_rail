"""Run a copy of ink_bins.py on a plate with Ben's rail switched off and every write kept inside diag/rail5 (25 Nov 2026).

    cd data/sanborn
    python -B bench_2026-11-25/diag/rail5/code/run_ink_bins5.py N OUT_BINS.png --which orig|proposed --ground nets|nets_ben|none

  --which orig       code/orig/ink_bins.py: byte copy of tools/sanborn/unet/ink_bins.py (sha256 3b461d06..., commit 0c4c205)
  --which proposed   code/proposed/ink_bins.py: the same with rail_rules.diff (bench_2026-11-21/rail-rules/diffs) applied
  --ground nets      ground and block lines from the networks' block step as it stood on 21 Nov (copies in inputs/:
                     5_edges.json, outlines.json, 5_outlines.json), WITHOUT Ben's line edits (passed as --edges/--outlines,
                     which ink_bins.py documents as 'Ben's edits are not applied'). This is how the rule tracks Ben saw
                     in the editor were made (checked: see the log)
  --ground nets_ben  the plain run of today: the same, but with Ben's line edits (edges_ben.json) applied by ink_bins.py
  --ground none      no ground at all (as the batch of 21 Nov morning ran the plates never placed): --edges points at a
                     file that does not exist, so ink_bins.py finds no block step and no label
Ben's rail is always off (--no-ben). The module is imported, not edited; open/cv2.imwrite/os.replace are guarded so that
only paths inside diag/rail5 can be written. tools/sanborn/unet is put on sys.path (after the copy's own folder) for
the read-only imports ink_bins.py makes (blocks_noguide.outline_version, street_map.editor_lines). Run with python -B."""
import sys, os, builtins, importlib.util
sys.dont_write_bytecode = True
import cv2

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); SAFE = os.path.normcase(ROOT)
TOOLS = os.path.normpath(os.path.join(ROOT, '..', '..', '..', '..', '..', 'tools', 'sanborn', 'unet'))


def _safe(p):
    a = os.path.normcase(os.path.abspath(p))
    if not a.startswith(SAFE + os.sep): raise PermissionError(f'run_ink_bins5.py: refusing to write outside diag/rail5: {p}')


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

opt = lambda k, d=None: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d
N, out = sys.argv[1], sys.argv[2]; _safe(out); which = opt('--which', 'orig'); ground = opt('--ground', 'nets')
assert which in ('orig', 'proposed') and ground in ('nets', 'nets_ben', 'none')
assert os.path.isdir(TOOLS), TOOLS
sys.path.append(TOOLS)
src = os.path.join(HERE, which, 'ink_bins.py')
spec = importlib.util.spec_from_file_location('ink_bins_under_test', src); ib = importlib.util.module_from_spec(spec); spec.loader.exec_module(ib)
inp = os.path.join(ROOT, 'inputs')
argv = [src, N, '--no-ben', '--save', out, '--json', out[:-4] + '.json']
if ground == 'nets': argv += ['--edges', os.path.join(inp, f'{N}_edges.json'), '--outlines', os.path.join(inp, 'outlines.json')]
if ground == 'none': argv += ['--edges', os.path.join(inp, 'no_such_file.json')]
sys.argv = argv
print('module', src, '| ground', ground, '| argv', argv[1:], flush=True)
ib.main()
