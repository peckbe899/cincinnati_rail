"""v-code: the staged run_plates.plan() on the repo's real data and run_plates.json, read only (main() is never called)."""
import collections, hashlib, json, os, sys
R = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/'; SU = R + 'data/sanborn/bench_2026-11-21/merge/staged/tools/sanborn/unet/'
sys.path.insert(0, SU); import run_plates as RP   # noqa
RP.REPO = os.path.normpath(R); RP.DATA = os.path.join(RP.REPO, 'data', 'sanborn')
RP.NETS = [os.path.join(RP.DATA, 'unet_data', 'models', m + '.pt') for m in ('area_ng1', 'lines_ng1')]; RP.VPY = R + 'tools/sanborn/unet/.venv/Scripts/python.exe'
RP.STATE = os.path.join(RP.DATA, 'unet_data', 'run_plates.json')
from blocks_noguide import outline_version
rules = hashlib.sha256(b''.join(open(os.path.join(SU if os.path.exists(SU + f) else R + 'tools/sanborn/unet/', f), 'rb').read() for f in RP.RULES)).hexdigest()[:12]; outver = outline_version()
P = RP.plates(RP.png_dir()); state = json.load(open(RP.STATE, encoding='utf8'))
nets = all(os.path.exists(f) for f in RP.NETS) and os.path.exists(RP.NETS[1][:-3] + '.done') and os.path.exists(RP.VPY); netid = '+'.join(str(int(os.path.getmtime(f))) for f in RP.NETS) if nets else ''
c = collections.Counter(); ex = {}
for n in sorted(P, key=RP.order):
    st = RP.plan(n, state.get(n, {}), rules, outver, nets, netid, False)
    key = ' + '.join(k for k, _ in st) or 'nothing'; c[key] += 1; ex.setdefault(key, []).append(n)
    if n in ('90', '44', '43', '1A', '93B'): print(n, st)
print(json.dumps(dict(plates=len(P), rules=rules, outline=outver, nets=nets, netid=netid, plan=dict(c), examples={k: v[:8] for k, v in ex.items()})))
# second pass: as if this run had finished (each record updated as main() would), what would the NEXT run do?
c2 = collections.Counter()
for n in P:
    s = dict(state.get(n, {})); st = dict(RP.plan(n, s, rules, outver, nets, netid, False))
    if 'nets' in st or 'outline' in st: s.update(blocks_nets=netid, outline=outver)
    if 'bins' in st: s.update(rules=rules, bins_from=RP.bins_from(n), state='done')
    st2 = RP.plan(n, s, rules, outver, nets, netid, False); c2[' + '.join(k for k, _ in st2) or 'nothing'] += 1
print('next run (files as now):', dict(c2))
