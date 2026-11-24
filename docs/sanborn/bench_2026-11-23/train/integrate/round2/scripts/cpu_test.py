"""Integrator, round 2 (24 Nov 2026): the staged trainers after the review fixes, on the CPU (the device function is
replaced; no GPU), on the real data/sanborn/train_v2: 3 iterations each, checks every iteration, into
integrate/round2/cpu_test/. Checks: --area-blank (the 7th input of a blanked plate is 128 everywhere, of an unblanked one
not; a plate with validation pixels may not be blanked; a name matching nothing is refused); the model json (meta.json
now checked against the manifest, content_sha256 recorded, area_blank recorded); the atomic writes (no .tmp left).
cd data/sanborn; ../../tools/sanborn/unet/.venv/Scripts/python.exe -B bench_2026-11-23/train/integrate/round2/scripts/cpu_test.py"""
import glob, json, os, sys
import numpy as np
REPO = os.path.abspath('../..'); STAGED = os.path.normpath(os.path.join(REPO, 'data/sanborn/bench_2026-11-23/train/staged/tools/sanborn/unet'))
sys.path.insert(0, os.path.join(REPO, 'tools/sanborn')); sys.path.insert(0, STAGED)
import torch  # noqa: E402
import unet as U, edgenet as E  # noqa: E402
assert os.path.normcase(os.path.dirname(os.path.abspath(U.__file__))) == os.path.normcase(STAGED)
torch.set_num_threads(8)
def cpu(): return torch.device('cpu')
cpu.name = 'cpu (integrator round-2 test)'
U.device = cpu; E.device = cpu
OUT = os.path.abspath('bench_2026-11-23/train/integrate/round2/cpu_test') + os.sep; os.makedirs(OUT, exist_ok=True)
root = os.path.abspath('train_v2'); R = {}


def call(f, *a, **k):
    try: return f(*a, **k)
    except SystemExit as e: return 'SystemExit: ' + str(e.code)[:200]


S0, h0 = E.load_data(root, '58', False); S1, h1 = E.load_data(root, '58', True)
R['58_area_in_loaded'] = dict(has_area=h0, ch7_all_128=bool((S0[:, :, 3] == 128).all()), ch7_mean=round(float(S0[:, :, 3].mean()), 2))
R['58_area_blank'] = dict(has_area=h1, ch7_all_128=bool((S1[:, :, 3] == 128).all()), rgb_and_target_equal=bool(np.array_equal(S0[:, :, [0, 1, 2, 4]], S1[:, :, [0, 1, 2, 4]])))
del S0, S1
R['blank_val_plate_refused'] = call(E.train_data, 'x', root, ['1A'], 1, 1, {}, OUT, 1, ['map'])
R['blank_unknown_refused'] = call(E.train_data, 'x', root, ['1A', '58'], 1, 1, {}, OUT, 1, ['label'])
print(json.dumps(R), flush=True)
E.train_data('lines_t', root, ['1A', '58'], 3, 1, {'58': 0.4545}, OUT, 1, ['pseudo'])
U.train_data('area_t', root, ['1A', '58'], 3, 1, {'58': 0.4545}, OUT, 1)
for n in ('lines_t', 'area_t'):
    d = json.load(open(OUT + n + '.json', encoding='utf8'))
    R[n] = dict(manifest_sha256=d['manifest_sha256'][:16], manifest_content_sha256=(d.get('manifest_content_sha256') or '')[:16], seed=d['seed'],
                meta_json_in_manifest={p['plate']: p['files'].get('meta.json', {}).get('in_manifest') for p in d['plates']},
                files_in_manifest={p['plate']: all(v.get('in_manifest', True) for k, v in p['files'].items() if k != 'scan') for p in d['plates']},
                area_blank=d.get('area_blank'), area_blank_plates=d.get('area_blank_plates'), area_in={p['plate']: p.get('area_in') for p in d['plates']},
                best=d.get('best'), history_iters=[h['iter'] for h in d['history']], val_scope=bool(d.get('val_scope')), crops_drawn=d.get('crops_drawn'))
R['tmp_files_left'] = glob.glob(OUT + '*.tmp')
man = json.load(open(root + '/manifest.json', encoding='utf8')); R['manifest_content_sha256'] = man['content_sha256'][:16]
json.dump(R, open(OUT + 'cpu_test.json', 'w'), indent=1); print(json.dumps(R, indent=1))
