"""run_bins.py (text/effect, 25 Nov 2026): run a COPY of today's ink_bins.py (code/orig, byte copy of
tools/sanborn/unet/ink_bins.py, sha256 3b461d06..., commit 0c4c205) with an optional text mask taken out FIRST.
Every write is guarded: only paths inside bench_2026-11-25/text/effect can be written.

    cd data/sanborn
    python -B bench_2026-11-25/text/effect/code/run_bins.py N OUT.png --ground G [--ben] [--text MASK.png] [--norail]

  --ground nets     plate 5: the networks' block step as Ben saw it on 21 Nov (rail5/inputs copies: 5_edges.json,
                    outlines.json, 5_outlines.json), WITHOUT his line edits (as diag/rail5 run_ink_bins5.py --ground nets)
  --ground none     no ground at all (--edges points at a file that does not exist; plate 5)
  --ground map      plate 44: Ben's street map (streetmap/22-44.json), as unet_data/44_bins.png was made
  --ground nomap    plate 44: --no-map (no street map, no label: no ground)
  --ground nets44   plate 44 sorted as a plate with no street map: from the outline step's own lines and blocks (bench/base__none__none
                    grid 0: the baseline networks' maps, the real outline step), as ink_bins.py sorts plates never placed
  --ben             Ben's rail on (rail_ben.json). Default: off (--no-ben), so the rule's own rail is measured
  --text MASK.png   text first: MASK > 0 and ink is bin 8 before anything else runs; that ink is taken out of the ink
                    the railroad rule, the streetcar rule, the small-piece sorting and the line sorting see
  --norail          the railroad rule's result is thrown away (rr = 0) but its streetcar rows (carrow) are kept: what
                    the text rules call text when rail has not taken its ink first (mask S1)
The patch is inserted in memory at three anchors that must each appear exactly once (asserted)."""
import sys, os, builtins
sys.dont_write_bytecode = True
import numpy as np, cv2

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); SAFE = os.path.normcase(ROOT)
TOOLS = os.path.normpath(os.path.join(ROOT, '..', '..', '..', '..', '..', 'tools', 'sanborn', 'unet'))
R5 = os.path.normpath(os.path.join(ROOT, '..', '..', 'diag', 'rail5', 'inputs'))


def _safe(p):
    a = os.path.normcase(os.path.abspath(p))
    if not a.startswith(SAFE + os.sep): raise PermissionError(f'run_bins.py: refusing to write outside text/effect: {p}')


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
N, out = sys.argv[1], sys.argv[2]; _safe(out); ground = opt('--ground'); TXTF = opt('--text'); NORAIL = '--norail' in sys.argv
assert ground in ('nets', 'none', 'map', 'nomap', 'nets44'), ground
NB = os.path.normpath(os.path.join(ROOT, 'bench', 'base__none__none', 'runs44', 'v2__grid0'))   # nets44: the outline step's own lines and blocks of 44 (baseline maps, grid 0)
sys.path.append(TOOLS)
src = os.path.join(HERE, 'orig', 'ink_bins.py'); code = open(src, encoding='utf8').read()
A1 = "    ink = (L < INK_L) & paper\n"
A2 = "    out = np.zeros((h, w), np.uint8)\n    rr, RAILINFO = railroad(ink, closed, paper); ink0 = ink; carrow = RAILINFO['carrow']\n"
for a in (A1, A2): assert code.count(a) == 1, 'ink_bins.py changed: anchor not there once: ' + a
code = code.replace(A1, A1 + "    TXT = (_TEXT_MASK[y0:y1, x0:x1] if _TEXT_MASK is not None else np.zeros((h, w), bool)) & ink; ink = ink & ~TXT\n")
code = code.replace(A2, "    out = np.zeros((h, w), np.uint8); out[TXT] = 8\n    rr, RAILINFO = railroad(ink, closed, paper); ink0 = ink | TXT; carrow = RAILINFO['carrow']\n"
                        "    if _NORAIL: rr = np.zeros_like(rr)\n")
mask = None
if TXTF and TXTF != 'none':
    mask = cv2.imread(TXTF, cv2.IMREAD_UNCHANGED); assert mask is not None, TXTF; mask = mask > 0
g = {'__name__': 'ink_bins_textfirst', '__file__': src, '_TEXT_MASK': mask, '_NORAIL': NORAIL}
exec(compile(code, src, 'exec'), g)
argv = [src, N, '--save', out, '--json', out[:-4] + '.json']
if '--ben' not in sys.argv: argv.insert(2, '--no-ben')
if ground == 'nets': argv += ['--edges', os.path.join(R5, f'{N}_edges.json'), '--outlines', os.path.join(R5, 'outlines.json')]
if ground == 'none': argv += ['--edges', os.path.join(R5, 'no_such_file.json')]
if ground == 'nomap': argv += ['--no-map']
if ground == 'nets44': argv += ['--no-map', '--edges', os.path.join(NB, '44_edges.json'), '--outlines', os.path.join(NB, 'outlines.json')]
sys.argv = argv
print('copy', src, '| ground', ground, '| text', TXTF, '| norail', NORAIL, '| argv', argv[1:], flush=True)
g['main']()
