"""merge/impl/r2: what a plain run of the staged run_plates.py would do on the real data (21 Nov 2026). Reads only.

    python -B dryrun2.py        -> merge/impl/r2/dryrun2.json

The staged run_plates.py is imported (its main() is not run); its paths are pointed at the real repo (REPO, DATA, the
state file run_plates.json, the networks and the venv), then plan() is asked for every plate with a scan, as main()
asks it, with the staged rules hash and outline version. A second pass pretends every planned step ran (the record
gets the new rules, outline version, bins_from as main() writes them) to show the plan then empties.
"""
import importlib.util, json, os, sys
import common as C
sys.path.insert(0, C.SHIM); import _ws  # noqa: E402,F401
AP = C.IMPL + 'applied/tools/sanborn/unet/'   # the repo's unet scripts with the staged files laid over them (as after git apply); rebuilt by the caller
sys.path.insert(1, AP)
spec = importlib.util.spec_from_file_location('rp', AP + 'run_plates.py'); rp = importlib.util.module_from_spec(spec); spec.loader.exec_module(rp)
REPO = C.REPO.rstrip('/'); rp.REPO = REPO; rp.DATA = os.path.join(REPO, 'data', 'sanborn'); rp.STATE = os.path.join(rp.DATA, 'unet_data', 'run_plates.json')
rp.NETS = [os.path.join(rp.DATA, 'unet_data', 'models', m + '.pt') for m in ('area_ng1', 'lines_ng1')]; rp.VPY = C.VPY
from blocks_noguide import outline_version  # noqa: E402
assert os.path.abspath(sys.modules['blocks_noguide'].__file__).replace('\\', '/').startswith(AP.rstrip('/'))
import filecmp  # noqa: E402
assert all(filecmp.cmp(AP + f, C.SU + f, shallow=False) for f in os.listdir(C.SU) if f.endswith('.py')), 'applied/ is older than staged/: rebuild it'
rules = rp.rules_hash(); outver = outline_version(); P = rp.plates(rp.png_dir()); state = json.load(open(rp.STATE, encoding='utf8'))
nets = all(os.path.exists(f) for f in rp.NETS) and os.path.exists(rp.NETS[1][:-3] + '.done') and os.path.exists(rp.VPY)
netid = '+'.join(str(int(os.path.getmtime(f))) for f in rp.NETS) if nets else ''
plan1 = {n: rp.plan(n, state.get(n, {}), rules, outver, nets, netid, False) for n in sorted(P, key=rp.order)}
count = {}
for st in plan1.values():
    key = ' + '.join(k for k, _ in st) or 'nothing'; count[key] = count.get(key, 0) + 1
placed = {n: plan1[n] for n in ('43', '44', '45', '80', '82A')}
# second pass: as if every planned step had run (main() writes these into the record); files on disk are as they are now
state2 = {}
for n, st in plan1.items():
    s = dict(state.get(n, {})); steps = dict(st)
    if 'nets' in steps or 'outline' in steps: s.update(blocks_nets=netid, outline=outver)
    if 'bins' in steps: s.update(rules=rules, bins_from=rp.bins_from(n), state='done')
    state2[n] = s
plan2 = {n: rp.plan(n, state2[n], rules, outver, nets, netid, False) for n in plan1}
res = dict(rules=rules, outline_version=outver, nets_on=nets, netid=netid, record_netid=state.get('5', {}).get('blocks_nets'), plates=len(P), steps_count=count,
           placed=placed, sample={n: plan1.get(n) for n in ('90', '5', '1A', '15B', '60B')}, second_pass_nonempty={n: v for n, v in plan2.items() if v},
           note='second pass: blocks and bins as recorded after the run; the files on disk are as now, so a plate whose block step would change N_edges.json would still show bins here only if bins_from changed')
json.dump(res, open(C.IMPL + 'dryrun2.json', 'w'), indent=1); print(json.dumps({k: v for k, v in res.items() if k != 'note'}, indent=1)[:3000])
