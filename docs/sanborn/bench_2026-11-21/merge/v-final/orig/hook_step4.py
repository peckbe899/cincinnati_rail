"""v-final --step4 hook for the ORIGINAL bench44 harness: the applied merged blocks_noguide.step4 (drops short, paper_edge,
'not on a line' and 'on rail' sides)."""
import os, sys
V = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-21/merge/v-final/'
sys.path.insert(0, V + 'shim'); sys.path.insert(1, V + 'apply/tools/sanborn/unet')
import _ws  # noqa: E402,F401  (the shim)
import blocks_noguide as _BN  # noqa: E402
assert os.path.abspath(_BN.__file__).replace(os.sep, '/').startswith(V + 'apply/'), _BN.__file__
def step4(polys): return _BN.step4(polys)
