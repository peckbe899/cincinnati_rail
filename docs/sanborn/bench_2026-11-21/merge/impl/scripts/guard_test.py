"""merge/impl: the two guards of the merged step, run for real on a throwaway data tree (21 Nov 2026).

merge/impl/fake_data/ is a copy of what the step reads for plate 8B, under two made-up plate names, and
merge/impl/shim_fake/_ws.py points DATA there, so blocks_noguide.py and outlines.py run WITHOUT --out exactly as in the
repo but write only into fake_data:
  Z1  a plate never placed whose lines Ben has edited (picks22_guided/22-Z1/edges_ben.json, a dummy) and which has an
      N_edges.json: blocks_noguide.py Z1 --outlines-only must leave unet_data/Z1_edges.json as it is and write
      Z1_edges.new.json, and say why.
  Z2  a placed plate (unet_data/Z2_guide.png) with an outlines.json: outlines.py Z2 must refuse (exit 1, saying why) and
      leave it; with --force it writes.
    python -B guard_test.py   -> merge/impl/guard_test.json
"""
import json, os, shutil, subprocess, hashlib
import common as C
F = C.IMPL + 'fake_data/'; SH = C.IMPL + 'shim_fake/'
shutil.rmtree(F, ignore_errors=True); os.makedirs(SH, exist_ok=True)
open(SH + '_ws.py', 'w').write(f"DATA = {F!r}\nCODE = {C.REPO + 'tools/sanborn/'!r}\n")
for z in ('Z1', 'Z2'):
    for d in (f'cufp/{z}', 'unet_data', f'picks22_guided/22-{z}'): os.makedirs(F + d, exist_ok=True)
    shutil.copy(C.DATA + 'cufp/22-8B.jpg', F + f'cufp/22-{z}.jpg'); shutil.copy(C.DATA + 'cufp/8B/png_alpha_s4.npy', F + f'cufp/{z}/png_alpha_s4.npy')
    for m in ('pred_area_ng1', 'lines_lines_ng1'): shutil.copy(C.U + f'8B_{m}.png', F + f'unet_data/{z}_{m}.png')
json.dump([dict(src='read', name='', a=[1, 1], b=[100, 1], state='green')], open(F + 'unet_data/Z1_edges.json', 'w'))
json.dump(dict(plate='Z1', lines=[dict(a0=[1, 1], b0=[100, 1], a=[1, 1], b=[100, 1], verdict='ok')]), open(F + 'picks22_guided/22-Z1/edges_ben.json', 'w'))
shutil.copy(C.U + '44_guide.png', F + 'unet_data/Z2_guide.png'); open(F + 'picks22_guided/22-Z2/outlines.json', 'w').write('[]')
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()[:16] if os.path.exists(p) else None
env = dict(C.env(), PYTHONPATH=SH.rstrip('/') + os.pathsep + C.RU)
before = dict(edges=sha(F + 'unet_data/Z1_edges.json'), ben=sha(F + 'picks22_guided/22-Z1/edges_ben.json'), z2=sha(F + 'picks22_guided/22-Z2/outlines.json'))
r1 = subprocess.run([C.VPY, '-B', C.SU + 'blocks_noguide.py', 'Z1', '--outlines-only'], cwd=F, capture_output=True, text=True, env=env)
r2 = subprocess.run([C.VPY, '-B', C.SU + 'outlines.py', 'Z2', 'area_ng1', 'lines_ng1'], cwd=F, capture_output=True, text=True, env=env)
mid = sha(F + 'picks22_guided/22-Z2/outlines.json')
r3 = subprocess.run([C.VPY, '-B', C.SU + 'outlines.py', 'Z2', 'area_ng1', 'lines_ng1', '--force'], cwd=F, capture_output=True, text=True, env=env)
res = dict(Z1=dict(rc=r1.returncode, printed=(r1.stdout + r1.stderr).strip()[-900:], edges_json_unchanged=sha(F + 'unet_data/Z1_edges.json') == before['edges'],
                   edges_ben_unchanged=sha(F + 'picks22_guided/22-Z1/edges_ben.json') == before['ben'], edges_new_written=os.path.exists(F + 'unet_data/Z1_edges.new.json'),
                   edges_new_lines=len(json.load(open(F + 'unet_data/Z1_edges.new.json'))) if os.path.exists(F + 'unet_data/Z1_edges.new.json') else None,
                   blocks_ng=json.load(open(F + 'unet_data/Z1_blocks_ng.json')) if os.path.exists(F + 'unet_data/Z1_blocks_ng.json') else None),
           Z2=dict(rc_without_force=r2.returncode, said=(r2.stderr + r2.stdout).strip()[-600:], outlines_unchanged_without_force=mid == before['z2'],
                   rc_with_force=r3.returncode, written_with_force=sha(F + 'picks22_guided/22-Z2/outlines.json') != before['z2']))
json.dump(res, open(C.IMPL + 'guard_test.json', 'w'), indent=1); print(json.dumps(res, indent=1))
