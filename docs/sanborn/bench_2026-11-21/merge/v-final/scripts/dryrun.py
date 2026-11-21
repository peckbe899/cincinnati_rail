"""v-final: what a plain run of the APPLIED run_plates.py would do on the repo as it is now, read only. run_plates.py is
imported from a sandbox copy of tools/sanborn/unet (v-final/code: the repo's files with the applied ones over them, and
the shim _ws), its paths pointed at the real data/sanborn, and only main() --list (which returns before writing) and
plan() are called.
    python -B dryrun.py -> v-final/dryrun.json"""
import collections, io, json, os, sys, contextlib
V = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-21/merge/v-final/'
R = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/'
CU = V + 'code/tools/sanborn/unet/'
sys.path.insert(0, V + 'code/tools/sanborn'); sys.path.insert(0, CU)
import _ws  # noqa: E402
assert _ws.__file__.replace(os.sep, '/').startswith(V), _ws.__file__
import run_plates as RP  # noqa: E402
assert RP.__file__.replace(os.sep, '/').startswith(CU)
RP.REPO = os.path.normpath(R); RP.DATA = os.path.join(RP.REPO, 'data', 'sanborn')
RP.NETS = [os.path.join(RP.DATA, 'unet_data', 'models', m + '.pt') for m in ('area_ng1', 'lines_ng1')]; RP.VPY = R + 'tools/sanborn/unet/.venv/Scripts/python.exe'
RP.STATE = os.path.join(RP.DATA, 'unet_data', 'run_plates.json'); RP.LOG = V + 'never_written.log'
st0 = os.path.getmtime(RP.STATE)
buf = io.StringIO(); sys.argv = ['run_plates.py', '--list']
with contextlib.redirect_stdout(buf): RP.main()
txt = buf.getvalue()
from blocks_noguide import outline_version  # noqa: E402
rules, outver = RP.rules_hash(), outline_version()
P = RP.plates(RP.png_dir()); state = json.load(open(RP.STATE, encoding='utf8'))
nets = all(os.path.exists(f) for f in RP.NETS) and os.path.exists(RP.NETS[1][:-3] + '.done') and os.path.exists(RP.VPY); netid = '+'.join(str(int(os.path.getmtime(f))) for f in RP.NETS) if nets else ''
plans = {n: RP.plan(n, state.get(n, {}), rules, outver, nets, netid, False) for n in sorted(P, key=RP.order)}
c = collections.Counter(tuple(k for k, _ in v) for v in plans.values())
res = dict(rules=rules, outline_version=outver, nets=nets, plates=len(P), step_sets={'+'.join(k) or 'nothing': v for k, v in c.items()},
           placed={n: plans.get(n) for n in ('43', '44', '45', '80', '82A')}, sample={n: plans.get(n) for n in ('90', '30', '47', '1B', '60B', '5', '26A', '2', '1A')},
           state_untouched=os.path.getmtime(RP.STATE) == st0, log_written=os.path.exists(RP.LOG), list_output=txt[-3000:])
json.dump(res, open(V + 'dryrun.json', 'w'), indent=1)
print(json.dumps({k: res[k] for k in res if k != 'list_output'}, indent=1)); print(txt[:1500])
