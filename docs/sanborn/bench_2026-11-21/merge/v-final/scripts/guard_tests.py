"""v-final: guard and option tests of the APPLIED code on a FAKE data tree (v-final/fake/data, plate 60B's real inputs
copied in), so nothing a test could write lands in the repo. The fake _ws (v-final/shim_fake) has DATA = the fake tree.
    python -B guard_tests.py -> v-final/guard_tests.json"""
import hashlib, json, os, shutil, subprocess, sys
V = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-21/merge/v-final/'
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; RU = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/tools/sanborn/unet'
AU = V + 'apply/tools/sanborn/unet/'; F = V + 'fake/data/'; VPY = RU + '/.venv/Scripts/python.exe'
N = '60B'
FILES = [f'cufp/22-{N}.jpg', f'cufp/{N}/png_alpha_s4.npy', f'unet_data/{N}_pred_area_ng1.png', f'unet_data/{N}_lines_lines_ng1.png', f'unet_data/{N}_edges.json',
         f'unet_data/{N}_bins.png', f'unet_data/{N}_bins.json', f'unet_data/{N}_outlines.json', f'unet_data/{N}_blockmask.png', f'picks22_guided/22-{N}/outlines.json']
OWN = [f'unet_data/{N}_edges.json', f'unet_data/{N}_outlines.json', f'unet_data/{N}_blockmask.png', f'picks22_guided/22-{N}/outlines.json', f'unet_data/{N}_blocks_ng.json', f'unet_data/{N}_outlines.jpg']
def build():
    if os.path.exists(V + 'fake'): shutil.rmtree(V + 'fake')
    for f in FILES: os.makedirs(os.path.dirname(F + f), exist_ok=True); shutil.copy2(SP + f, F + f)
    os.makedirs(V + 'shim_fake', exist_ok=True)
    open(V + 'shim_fake/_ws.py', 'w').write(f"DATA = '{F}'\nCODE = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/tools/sanborn/'\n")
def env(): return dict(os.environ, PYTHONPATH=V + 'shim_fake' + os.pathsep + RU, PYTHONDONTWRITEBYTECODE='1')
def sh(): return {f: (hashlib.sha256(open(F + f, 'rb').read()).hexdigest()[:16] if os.path.exists(F + f) else None) for f in OWN}
def run(cmd, cwd=F): r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding='utf8', errors='replace', env=env()); return dict(exit=r.returncode, out=(r.stdout + r.stderr).strip()[-600:])
def listing(): return sorted(os.path.relpath(os.path.join(d, f), F).replace(os.sep, '/') for d, _, fs in os.walk(F) for f in fs)
R = {}
build(); base = listing()
# 1. Ben has edited the plate's lines (edges_ben.json AND N_edges.json): steps 3, 4 go to unet_data/N_new/, the plate's own files stay
json.dump(dict(lines=[]), open(F + f'picks22_guided/22-{N}/edges_ben.json', 'w')); s0 = sh()
r = run([VPY, '-B', AU + 'blocks_noguide.py', N, '--outlines-only']); s1 = sh()
R['protected_blocks_noguide'] = dict(r, own_files_unchanged=s0 == s1, new_dir=sorted(os.listdir(F + f'unet_data/{N}_new')) if os.path.isdir(F + f'unet_data/{N}_new') else None,
                                     new_equals_out_run=open(F + f'unet_data/{N}_new/outlines.json', 'rb').read() == open(V + f'plates/{N}/outlines.json', 'rb').read() if os.path.isdir(F + f'unet_data/{N}_new') else None)
r = run([VPY, '-B', AU + 'outlines.py', N, 'area_ng1', 'lines_ng1']); R['protected_outlines_py'] = dict(r, own_files_unchanged=sh() == s0)
# 2. a placed plate (a guide): blocks_noguide leaves it, outlines.py refuses without --force
shutil.copy2(F + f'unet_data/{N}_blockmask.png', F + f'unet_data/{N}_guide.png'); os.remove(F + f'picks22_guided/22-{N}/edges_ben.json'); s0 = sh()
R['placed_blocks_noguide'] = dict(run([VPY, '-B', AU + 'blocks_noguide.py', N, '--outlines-only']), own_files_unchanged=sh() == s0)
R['placed_outlines_py'] = dict(run([VPY, '-B', AU + 'outlines.py', N, 'area_ng1', 'lines_ng1']), own_files_unchanged=sh() == s0)
os.remove(F + f'unet_data/{N}_guide.png')
# 3. option slips stop before anything runs
s0 = sh(); l0 = listing()
R['blocks_noguide_typo'] = run([VPY, '-B', AU + 'blocks_noguide.py', N, '--outline-only'])
R['outlines_typo'] = run([VPY, '-B', AU + 'outlines.py', N, 'area_ng1', 'lines_ng1', '--bogus'])
R['ink_bins_typo'] = run(['python', '-B', AU + 'ink_bins.py', N, '--nomap'])
R['ink_bins_test_opt_without_save'] = run(['python', '-B', AU + 'ink_bins.py', N, '--no-map'])
R['ink_bins_json_without_save'] = run(['python', '-B', AU + 'ink_bins.py', N, '--json', V + 'fake/x.json'])
R['ink_bins_stray_arg'] = run(['python', '-B', AU + 'ink_bins.py', N, '44'])
R['option_slips_changed_nothing'] = dict(own=sh() == s0, listing=listing() == l0)
# 4. edges_ben.json but no N_edges.json: the plate's own lines are written (his edits can only be drawn or sheet-edge lines)
json.dump(dict(lines=[]), open(F + f'picks22_guided/22-{N}/edges_ben.json', 'w')); os.remove(F + f'unet_data/{N}_edges.json'); shutil.rmtree(F + f'unet_data/{N}_new')
r = run([VPY, '-B', AU + 'blocks_noguide.py', N, '--outlines-only'])
R['edges_ben_no_edges'] = dict(r, wrote_own=os.path.exists(F + f'unet_data/{N}_edges.json'), N_new=os.path.isdir(F + f'unet_data/{N}_new'),
                               same_as_out_run=open(F + f'picks22_guided/22-{N}/outlines.json', 'rb').read() == open(V + f'plates/{N}/outlines.json', 'rb').read() if os.path.exists(F + f'picks22_guided/22-{N}/outlines.json') else None)
# 5. a lower-case plate id
r = run([VPY, '-B', AU + 'blocks_noguide.py', N.lower(), '--outlines-only', '--out', V + 'fake/lc'])
R['lower_case'] = dict(r, same=open(V + 'fake/lc/outlines.json', 'rb').read() == open(V + f'plates/{N}/outlines.json', 'rb').read() if os.path.exists(V + 'fake/lc/outlines.json') else None,
                       files=sorted(os.listdir(V + 'fake/lc')) if os.path.isdir(V + 'fake/lc') else None)
json.dump(R, open(V + 'guard_tests.json', 'w'), indent=1)
for k, v in R.items(): print(k, json.dumps(v)[:700])
