"""The staged trainers WITHOUT --data still run (the unet_data path), 10 iterations each, GPU.

    VENV -B legacy_check.py

The staged unet.py / edgenet.py are imported and their DATA (unet_data/) is pointed at legacy_data/ beside this file,
which holds copies of plate 80's unet_data files, so the models go to legacy_data/models/ and nothing is written into
unet_data. Runs unet.train('legacy_area', ['80'], 10) (right-quarter hold-out, --no-guide: no guide move, no squares)
and edgenet.train('legacy_lines', ['80'], 10) (--no-guide --area area_ng1). Writes legacy_check.json.
"""
import importlib.util, json, os, shutil, sys, time
sys.dont_write_bytecode = True
REPO = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/'
HERE = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/') + '/'
STAGED = REPO + 'data/sanborn/bench_2026-11-23/train/staged/tools/sanborn/unet/'
sys.argv = [sys.argv[0], '--no-guide', '--area', 'area_ng1']
sys.path.insert(0, REPO + 'tools/sanborn'); sys.path.insert(0, STAGED)
import unet as UN, edgenet as EN
D = HERE + 'legacy_data/'; os.makedirs(D + 'models', exist_ok=True)
for f in ('80_img.jpg', '80_guide.png', '80_label.png', '80_edge.png', '80_verified.json', '80_pred_area_ng1.png'): shutil.copyfile(REPO + 'data/sanborn/unet_data/' + f, D + f)
UN.DATA = D; EN.DATA = D
out = {}
t0 = time.time(); UN.train('legacy_area', ['80'], 10); out['area'] = dict(seconds=round(time.time() - t0, 1), json=json.load(open(D + 'models/legacy_area.json'))['history'][-1], pt=os.path.exists(D + 'models/legacy_area.pt'))
t0 = time.time(); EN.train('legacy_lines', ['80'], 10); out['lines'] = dict(seconds=round(time.time() - t0, 1), json=json.load(open(D + 'models/legacy_lines.json'))['history'][-1], pt=os.path.exists(D + 'models/legacy_lines.pt'))
out['flags'] = dict(unet_NOGUIDE=UN.NOGUIDE, unet_LEGACY=UN.LEGACY_NOGUIDE, edgenet_NOGUIDE=EN.NOGUIDE, edgenet_AREA=EN.AREA)
json.dump(out, open(HERE + 'legacy_check.json', 'w'), indent=1); print(json.dumps(out, indent=1))
