"""Integrator (24 Nov 2026): checks on the real data folder data/sanborn/train_v2/.
  1. 44 and 90 are not in it (folders, manifest), and every plate folder is in the manifest with matching sha256s.
  2. No 1A validation pixel is taught: the staged trainers' own crop samplers (unet.draw_crop, edgenet.draw_crop) on the
     real 1A, N crops each; the area trainer's training label has 255 under valmask; the line crops never reach it.
  3. The format of every plate folder (sizes, values) and the counts per source.
Run with the networks' venv and PYTHONPATH=tools/sanborn:  python -B check_data.py [N]   -> ../check_data.json"""
import hashlib, json, os, sys
import numpy as np, cv2
T = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')) + '/'
REPO = os.path.normpath(T + '../../../../'); SP = REPO + '/data/sanborn/'; D = SP + 'train_v2/'
sys.path.insert(0, T + 'staged/tools/sanborn/unet')
import unet as U, edgenet as E  # noqa: E402  (the staged trainers)
N = int(sys.argv[1]) if len(sys.argv) > 1 else 50000
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
out = {}
man = json.load(open(D + 'manifest.json', encoding='utf8')); dirs = sorted(d for d in os.listdir(D) if os.path.isdir(D + d))
out['folders'] = dirs; out['manifest_plates'] = sorted(man['plates'])
out['forbidden_absent'] = not ({'44', '90'} & (set(dirs) | set(man['plates'])))
bad = []
for p in dirs:
    for f, s in man['plates'][p]['files'].items():
        if sha(D + p + '/' + f) != s: bad.append(f'{p}/{f}')
out['manifest_sha_mismatches'] = bad
out['content_sha256_ok'] = hashlib.sha256(json.dumps(man['plates'], sort_keys=True).encode()).hexdigest() == man['content_sha256']
# per plate format and counts
fmt = {}
for p in dirs:
    lab = cv2.imread(D + p + '/label.png', cv2.IMREAD_UNCHANGED); t = cv2.imread(D + p + '/lines.png', cv2.IMREAD_UNCHANGED); im = cv2.imread(D + p + '/img.jpg'); ai = cv2.imread(D + p + '/area_in.png', 0); e = cv2.imread(D + p + '/edge.png', 0)
    m = json.load(open(D + p + '/meta.json', encoding='utf8'))
    fmt[p] = dict(source=m['source'], ft=m.get('ft_per_inch'), half=list(lab.shape[::-1]), full=list(t.shape[::-1]), img_ok=im.shape[:2] == lab.shape, area_in_ok=ai.shape == lab.shape, edge_ok=e.shape == lab.shape,
                  label_values=sorted(np.unique(lab).tolist()), lines_values=sorted(np.unique(t).tolist()), block=int((lab == 1).sum()), street=int((lab == 0).sum()), line_pos=int((t == 1).sum()), line_neg=int((t == 0).sum()),
                  edge_px=int((e > 0).sum()), valmask=os.path.exists(D + p + '/valmask.png'))
out['plates'] = fmt
# 1A: validation ground never in a training crop
lab = cv2.imread(D + '1A/label.png', 0); vm = cv2.imread(D + '1A/valmask.png', 0) > 0; h, w = lab.shape
xs = np.where(vm.any(0))[0]; out['1A_valmask'] = dict(x_from_half=int(xs.min()), x_to_half=int(xs.max()) + 1, width_half=w, val_px=int(vm.sum()), val_taught_area=int(((lab != 255) & vm).sum()),
                                                     val_block=int(((lab == 1) & vm).sum()), val_street=int(((lab == 0) & vm).sum()), rows_full=bool(vm[:, xs.min():].all()))
tl = lab.copy(); tl[vm] = 255; vint = cv2.integral(vm.astype(np.uint8))
P = dict(plate='1A', lab=tl, vint=vint); rng = np.random.default_rng(7); hit = 0; maxx = 0
for _ in range(N):
    y, x = U.draw_crop(rng, P); hit += int(vm[y:y + U.CROP, x:x + U.CROP].any()); maxx = max(maxx, int(x) + U.CROP)
out['area_crops'] = dict(n=N, touching_validation=hit, max_right_edge_half=maxx, val_starts_half=int(xs.min()))
S, _ = E.load_data(D, '1A'); H, W = S.shape[:2]; vf = cv2.resize(vm.astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST) > 0
Q = dict(plate='1A', S=S, vint=vint); rng = np.random.default_rng(8); hit = 0; maxx = 0
for _ in range(N):
    y, x = E.draw_crop(rng, Q); hit += int(vf[y:y + E.CROP, x:x + E.CROP].any()); maxx = max(maxx, int(x) + E.CROP)
fx = np.where(vf.any(0))[0]
out['line_crops'] = dict(n=N, touching_validation=hit, max_right_edge_full=maxx, val_starts_full=int(fx.min()))
# the 1A lines taught inside the validation ground (scored there, never trained)
t = S[:, :, 4]; out['1A_val_lines'] = dict(pos=int(((t == 1) & vf).sum()), neg=int(((t == 0) & vf).sum()))
json.dump(out, open(T + 'integrate/check_data.json', 'w'), indent=1); print(json.dumps({k: v for k, v in out.items() if k != 'plates'}, indent=1))
