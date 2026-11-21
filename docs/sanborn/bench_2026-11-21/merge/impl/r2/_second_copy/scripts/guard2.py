"""merge/impl/r2: the guards and option checks of the round-2 staged code, in a fake data tree (21 Nov 2026).

    python -B guard2.py          -> merge/impl/r2/guard2.json

The fake tree r2/fake/data/ (shim_fake/_ws.py points DATA at it) holds copies of real plates under made-up names:
  Z1 = 60B with a test edges_ben.json ({"lines": []}, not Ben's) and an existing Z1_edges.json and outlines.json
  Z3 = 60B with a test edges_ben.json and no Z3_edges.json;  Z4 = 60B;  Z5 = 90 (an uncut PDF sheet);  Z6 = 64A (rail)
Nothing outside merge/impl/r2 is written: every run's cwd is the fake tree, every import of _ws gets the fake shim.
"""
import hashlib, json, os, shutil, subprocess, sys
import common as C
FK = C.IMPL + 'fake/data/'; SHF = C.IMPL + 'shim_fake'; NT = C.IMPL + 'notpl/tools/sanborn/unet/'
ENV = dict(os.environ, PYTHONPATH=SHF + os.pathsep + C.RU, PYTHONDONTWRITEBYTECODE='1')
H = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()[:16] if os.path.exists(p) else None
res = {}


def run(cmd, py=C.VPY):
    r = subprocess.run([py, '-B'] + cmd, cwd=FK, capture_output=True, text=True, encoding='utf8', errors='replace', env=ENV)
    return dict(rc=r.returncode, out=(r.stdout + r.stderr).strip().splitlines()[-3:])


def ink(args):
    """the staged ink_bins.py in the fake tree, the fake shim imported first"""
    code = ("import sys,runpy; sys.path.insert(0, %r); import _ws; sys.path.remove(%r); sys.path.append(%r); sys.argv=[%r]+%r; runpy.run_path(%r, run_name='__main__')"
            % (SHF, SHF, C.RU, C.SU + 'ink_bins.py', args, C.SU + 'ink_bins.py'))
    r = subprocess.run(['python', '-B', '-c', code], cwd=FK, capture_output=True, text=True, encoding='utf8', errors='replace', env=ENV)
    return dict(rc=r.returncode, out=(r.stdout + r.stderr).strip().splitlines()[-4:])


BN = C.SU + 'blocks_noguide.py'; OL = C.SU + 'outlines.py'
for d in ('Z1_new', 'Z4_out'): shutil.rmtree(FK + 'unet_data/' + d, ignore_errors=True)
z1 = {f: H(FK + f) for f in ('unet_data/Z1_edges.json', 'picks22_guided/22-Z1/outlines.json', 'unet_data/Z1_outlines.json')}
# T1 a plate Ben has edited: everything new into unet_data/Z1_new/, the plate's own files untouched
r = run([BN, 'Z1', '--outlines-only'])
res['T1_protected'] = dict(run=r, own_files_unchanged={f: H(FK + f) == h for f, h in z1.items()}, new_dir=sorted(os.listdir(FK + 'unet_data/Z1_new')) if os.path.isdir(FK + 'unet_data/Z1_new') else None)
# T4 outlines.py run by hand on that plate: refused
r = run([OL, 'Z1', 'area_ng1', 'lines_ng1']); res['T4_outlines_by_hand_refused'] = dict(run=r, own_files_unchanged={f: H(FK + f) == h for f, h in z1.items()})
# T2 edges_ben.json but no Z3_edges.json: written normally (nothing of his is keyed to it)
for f in ('unet_data/Z3_edges.json', 'picks22_guided/22-Z3/outlines.json'):
    if os.path.exists(FK + f): os.remove(FK + f)
r = run([BN, 'Z3', '--outlines-only']); res['T2_edges_ben_no_edges'] = dict(run=r, wrote=[os.path.exists(FK + 'unet_data/Z3_edges.json'), os.path.exists(FK + 'picks22_guided/22-Z3/outlines.json')], no_new_dir=not os.path.isdir(FK + 'unet_data/Z3_new'))
# T3 a plain plate
r = run([BN, 'Z4', '--outlines-only']); res['T3_plain'] = dict(run=r, edges=H(FK + 'unet_data/Z4_edges.json'))
# T5 a typo: refused before anything runs
before = sorted(os.listdir(FK + 'unet_data')); r = run([BN, 'Z4', '--outline-only']); res['T5_typo'] = dict(run=r, unet_data_unchanged=sorted(os.listdir(FK + 'unet_data')) == before)
# T6 --out=DIR form
r = run([BN, 'Z4', '--outlines-only', '--out=' + FK + 'unet_data/Z4_out']); res['T6_out_equals'] = dict(run=r, out_dir=sorted(os.listdir(FK + 'unet_data/Z4_out')) if os.path.isdir(FK + 'unet_data/Z4_out') else None,
                                                                                         same_edges=H(FK + 'unet_data/Z4_out/Z4_edges.json') == H(FK + 'unet_data/Z4_edges.json'))
# T7 ink_bins option checks: nothing written
for k, args in (('unknown', ['Z4', '--bogus']), ('test_without_save', ['Z4', '--no-map']), ('edges_without_save', ['Z4', '--edges', 'x.json']), ('json_without_save', ['Z4', '--json', 'x.json'])):
    r = ink(args); res[f'T7_ink_{k}'] = dict(run=r, no_bins_written=not os.path.exists(FK + 'unet_data/Z4_bins.png'))
# T8 an uncut sheet with no templates: the step stops (exit 1), nothing written
for f in ('unet_data/Z5_edges.json', 'picks22_guided/22-Z5/outlines.json', 'unet_data/Z5_outlines.json'):
    if os.path.exists(FK + f): os.remove(FK + f)
assert not os.path.isdir(NT + 'templates')
r = run([NT + 'blocks_noguide.py', 'Z5', '--outlines-only'])
res['T8_no_templates'] = dict(run=r, nothing_written=not any(os.path.exists(FK + f) for f in ('unet_data/Z5_edges.json', 'picks22_guided/22-Z5/outlines.json', 'unet_data/Z5_outlines.json', 'unet_data/Z5_mapground.png')))
# T9 the same sheet with the templates: runs, map ground found
r = run([BN, 'Z5', '--outlines-only']); rep = json.load(open(FK + 'unet_data/Z5_outlines.json')) if os.path.exists(FK + 'unet_data/Z5_outlines.json') else {}
res['T9_with_templates'] = dict(run=r, map_ground=rep.get('map_ground'), suspect_why=rep.get('suspect_why'), mapground_png=os.path.exists(FK + 'unet_data/Z5_mapground.png'))
# T10 rail: the step on Z6 (64A) runs the rule; ink_bins sorts from it (ground 'nets', its outline version); the step run
# again takes the bins' railroad (same version) and must give the same outlines.json byte for byte
for f in ('unet_data/Z6_bins.png', 'unet_data/Z6_bins.json'):
    if os.path.exists(FK + f): os.remove(FK + f)
r1 = run([BN, 'Z6', '--outlines-only']); o1 = H(FK + 'picks22_guided/22-Z6/outlines.json'); rail1 = json.load(open(FK + 'unet_data/Z6_outlines.json'))['rail']
ri = ink(['Z6']); bj = json.load(open(FK + 'unet_data/Z6_bins.json')) if os.path.exists(FK + 'unet_data/Z6_bins.json') else {}
r2 = run([BN, 'Z6', '--outlines-only']); o2 = H(FK + 'picks22_guided/22-Z6/outlines.json'); rail2 = json.load(open(FK + 'unet_data/Z6_outlines.json'))['rail']
res['T10_rail_same_either_way'] = dict(first=r1, rail_first=rail1, ink=ri, bins_ground_from=bj.get('ground_from'), bins_outline_version=bj.get('outline_version'), second=r2, rail_second=rail2, outlines_identical=o1 == o2,
                                       railroad_px=(bj.get('bins') or {}).get('4', {}).get('px'))
json.dump(res, open(C.IMPL + 'guard2.json', 'w'), indent=1)
for k, v in res.items(): print(k, json.dumps(v)[:400])
