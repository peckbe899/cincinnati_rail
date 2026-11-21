"""v-44 hook for the ORIGINAL bench44.py --step4: the STAGED blocks_noguide.step4 with its defaults
(KEEP_UNLINED = False, RAIL_DROP = True). Variants by environment V44_STEP4:
  default     step4(polys)                          (the staged step 4 as it ships)
  railshow    step4(polys, rail_drop=False)         ('on rail' sides shown orange)
  norail      'on rail' sides given back their 'was' state, then step4(polys)   (as if there were no rail test)
  keepunlined step4(polys, keep_unlined=True)       (option 2)
The module is loaded from the staged file by path and checked to be it."""
import copy, importlib.util, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import STAGED, SHIM  # noqa: E402
sys.path.insert(0, SHIM)
import _ws  # noqa: E402,F401   (the shim, so blocks_noguide's import of _ws never reaches the repo's)
assert os.path.abspath(_ws.__file__).replace('\\', '/').startswith(SHIM), _ws.__file__
_spec = importlib.util.spec_from_file_location('bn_staged', STAGED + 'blocks_noguide.py'); BN = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(BN)
MODE = os.environ.get('V44_STEP4', 'default')


def step4(polys):
    if MODE == 'default': return BN.step4(polys)
    if MODE == 'railshow': return BN.step4(polys, rail_drop=False)
    if MODE == 'keepunlined': return BN.step4(polys, keep_unlined=True)
    if MODE == 'norail':
        P = copy.deepcopy(polys)
        for p in P:
            for s in p:
                if s['state'] == 'on rail': s['state'] = s['was']
        return BN.step4(P)
    raise SystemExit(f'unknown V44_STEP4 {MODE}')
