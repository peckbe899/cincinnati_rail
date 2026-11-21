"""merge/v-batch: a sandbox copy of the repo for the staged run_plates.py (21 November 2026). Writes only under v-batch/sandbox/.

    python -B setup_sandbox.py

run_plates.py finds everything from where it lies (REPO = its folder/../../..), so the staged code is laid out as a
small repo of its own:
  sandbox/configs/sanborn_paths.json        copy (the raw PNG and PDF folders it names are only listed, never written)
  sandbox/tools/sanborn/_ws.py              copy of the repo's (its DATA is then sandbox/data/sanborn)
  sandbox/tools/sanborn/unet/               the staged files (outlines, blocks_noguide, ink_bins, map_area, run_plates,
                                            street_map, templates/) + the repo's rail_tracks, edit_server, unet, edgenet
  sandbox/tools/sanborn/unet/.venv/         a new venv on the same base Python, whose one .pth file reads the repo
                                            venv's site-packages (read only); torch_directml is stubbed out so the
                                            networks can only run on the CPU
  sandbox/data/sanborn/                     per plate of run_plates.json: real copies of the small files (N_edges.json,
                                            N_outlines.json, N_bins.json, N_label.png, outlines.json, rail_ben.json,
                                            edges_ben.json, source.json, the street map), and of the scans, maps and bins
                                            for the plates run for real (REAL); for the rest, empty files of the same
                                            names (run_plates.py --list only asks whether they exist). The plate with
                                            no maps (NOMAPS) gets none. models/ area_ng1 and lines_ng1 copied with
                                            their file times (run_plates.py keys the networks on them).
  GUARD: a test edges_ben.json (not Ben's: {"lines": []}) on plate 5, to test the guard that keeps N_edges.json.
"""
import json, os, shutil, subprocess, sys
import common as C
SB = C.mine(C.ME + 'sandbox') + '/'; SD = SB + 'data/sanborn/'; SU = SB + 'tools/sanborn/unet/'
REAL = ['60B', '44', '5', '90']; NOMAPS = ['15B']; GUARD = ['5']
assert not os.path.exists(SB), 'sandbox exists: remove it by hand first'


def cp(src, dst, real=True):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if real: shutil.copy2(src, dst)
    else: open(dst, 'wb').close()


os.makedirs(SB + 'configs'); shutil.copy2(C.REPO + 'configs/sanborn_paths.json', SB + 'configs/sanborn_paths.json')
cp(C.REPO + 'tools/sanborn/_ws.py', SB + 'tools/sanborn/_ws.py')
for f in ('outlines.py', 'blocks_noguide.py', 'ink_bins.py', 'map_area.py', 'run_plates.py', 'street_map.py'): cp(C.SU + f, SU + f)
shutil.copytree(C.SU + 'templates', SU + 'templates')
for f in ('rail_tracks.py', 'edit_server.py', 'unet.py', 'edgenet.py'): cp(C.RU + '/' + f, SU + f)
cp(C.STAGED + 'data/sanborn/scale_table.json', SD + 'scale_table.json')
# the venv
subprocess.run([sys.executable, '-m', 'venv', '--without-pip', SU + '.venv'], check=True)
sp = SU + '.venv/Lib/site-packages/'
open(sp + 'zz_repo_venv.pth', 'w').write(os.path.normpath(C.REPO + 'tools/sanborn/unet/.venv/Lib/site-packages') + '\n')
open(sp + 'torch_directml.py', 'w').write('raise ImportError("v-batch sandbox: no DirectML, the networks run on the CPU")\n')
# data
st = json.load(open(C.U + 'run_plates.json', encoding='utf8'))
cp(C.U + 'run_plates.json', SD + 'unet_data/run_plates.json')
for m in ('area_ng1.pt', 'lines_ng1.pt', 'lines_ng1.done', 'area_ng1.json', 'lines_ng1.json'):
    if os.path.exists(C.U + 'models/' + m): cp(C.U + 'models/' + m, SD + 'unet_data/models/' + m)
cp(C.DATA + 'streetmap/22-44.json', SD + 'streetmap/22-44.json')
made = {}
for n in st:
    real = n in REAL or n in NOMAPS
    big = [(f'cufp/22-{n}.jpg', True), (f'cufp/{n}/png_alpha_s4.npy', True), (f'unet_data/{n}_bins.png', True)]
    if n not in NOMAPS: big += [(f'unet_data/{n}_pred_area_ng1.png', True), (f'unet_data/{n}_lines_lines_ng1.png', True)]
    for f, _ in big:
        if os.path.exists(C.DATA + f): cp(C.DATA + f, SD + f, real)
    for f in (f'cufp/{n}/source.json', f'unet_data/{n}_edges.json', f'unet_data/{n}_outlines.json', f'unet_data/{n}_blocks_ng.json', f'unet_data/{n}_bins.json',
              f'unet_data/{n}_label.png', f'unet_data/{n}_rail_rule.json', f'picks22_guided/22-{n}/outlines.json', f'picks22_guided/22-{n}/rail_ben.json', f'picks22_guided/22-{n}/edges_ben.json'):
        if os.path.exists(C.DATA + f): cp(C.DATA + f, SD + f)
    if os.path.exists(C.U + f'{n}_guide.png'): cp(C.U + f'{n}_guide.png', SD + f'unet_data/{n}_guide.png', real)
    made[n] = 'real' if real else 'placeholders'
for n in GUARD:
    assert not os.path.exists(C.G + f'22-{n}/edges_ben.json')
    json.dump(dict(lines=[], note='v-batch sandbox test file, not Ben\'s: tests that blocks_noguide.py keeps N_edges.json on a plate with edges_ben.json'), open(SD + f'picks22_guided/22-{n}/edges_ben.json', 'w'))
json.dump(dict(real=REAL, nomaps=NOMAPS, guard=GUARD, plates=made), open(SB + 'sandbox_made.json', 'w'), indent=1)
print('sandbox at', SB, '| real:', REAL, '| no maps:', NOMAPS, '| guard test:', GUARD)
