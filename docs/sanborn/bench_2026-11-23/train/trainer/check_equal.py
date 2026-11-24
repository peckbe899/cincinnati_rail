"""Checks of the staged trainers' --data loaders and crop sampler (no GPU, no training).

    VENV -B check_equal.py [DATA_DIR] [PLATE ...]       default: testdata/ and plate 80 (a labelled plate)

1. area net: the REPO's unet.load(N) + load_edge (--no-guide) against the STAGED unet.load_data(DIR, N): the 5-channel
   input, the label, the edge weight map and target must be equal pixel for pixel.
2. line net: the REPO's edgenet.load(N) (--no-guide --area area_ng1) against the STAGED edgenet.load_data + build() over
   the whole plate: the 7-channel input, the target and the weights must be equal pixel for pixel. (The target is
   DIR/N/lines.png; for a labelled plate it must be what load() builds.)
3. no training crop touches a validation pixel: 50,000 crops drawn by each staged sampler (draw_crop) on every plate with
   a valmask.png, each tested directly against the valmask (half size for the area net, the valmask resized to full size
   as the label is for the line net). Also how near the crops come to the validation ground.
Writes check_equal.json beside this file.
"""
import importlib.util, json, os, sys, time
sys.dont_write_bytecode = True
REPO = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/'
HERE = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/') + '/'
STAGED = REPO + 'data/sanborn/bench_2026-11-23/train/staged/tools/sanborn/unet/'
args = [a for a in sys.argv[1:]]
DIR = os.path.abspath(args[0]) if args else HERE + 'testdata'; PLATES = args[1:] or ['80']
sys.argv = [sys.argv[0], '--no-guide', '--area', 'area_ng1']
sys.path.insert(0, REPO + 'tools/sanborn')
import numpy as np, cv2


def mod(name, path):
    spec = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(spec); sys.modules[name] = m; spec.loader.exec_module(m); return m


UN = mod('unet', STAGED + 'unet.py'); EN = mod('edgenet', STAGED + 'edgenet.py')                   # staged (new)
UO = mod('unet_repo', REPO + 'tools/sanborn/unet/unet.py'); EO = mod('edgenet_repo', REPO + 'tools/sanborn/unet/edgenet.py')   # repo (today)
res = dict(data=DIR, plates={})


def eq(a, b): return bool(a.shape == b.shape and a.dtype == b.dtype and np.array_equal(a, b))


for p in PLATES:
    r = {}; t0 = time.time()
    if os.path.exists(UO.DATA + f'{p}_label.png'):
        x0, l0 = UO.load(p); w0, e0 = UO.load_edge(p, l0)
        x1, l1, w1, e1, known = UN.load_data(DIR, p)
        r['area'] = dict(x=eq(x0, x1), label=eq(l0, l1), edge_weights=eq(w0, w1), edge_target=eq(e0, e1), edge_known=known, shape=list(x1.shape))
        del x0, x1
        X0, T0, W0 = EO.load(p)
        S, has_area = EN.load_data(DIR, p); H, W = S.shape[:2]
        X1, T1, W1 = EN.build(S, 0, H, 0, W)
        r['lines'] = dict(x=eq(X0, X1), target=eq(T0, T1), weights=eq(W0, W1), x_channels_equal=[bool(np.array_equal(X0[:, :, c], X1[:, :, c])) for c in range(7)],
                          stored_bytes_per_px=S.nbytes / (H * W), load_bytes_per_px=(X0.nbytes + T0.nbytes + W0.nbytes) / (H * W), line_px=int((T1 == 1).sum()))
        # a window build is the same as the whole-plate build cut to that window (the ink image is made pixel by pixel)
        rng = np.random.default_rng(7); ok = True
        for _ in range(20):
            y, x = int(rng.integers(0, H - 448)), int(rng.integers(0, W - 448)); a, b, c = EN.build(S, y, y + 448, x, x + 448)
            ok &= np.array_equal(a, X1[y:y + 448, x:x + 448]) and np.array_equal(b, T1[y:y + 448, x:x + 448]) and np.array_equal(c, W1[y:y + 448, x:x + 448])
        r['lines']['window_builds_equal_whole_plate'] = bool(ok)
        del X0, T0, W0, X1, T1, W1, S
    else: r['note'] = 'not a labelled plate of unet_data: equality not tested'
    r['seconds'] = round(time.time() - t0, 1); res['plates'][p] = r; print(p, json.dumps(r), flush=True)

# 3. the samplers never touch the validation ground
ov = {}
for p in sorted(d for d in os.listdir(DIR) if os.path.exists(os.path.join(DIR, d, 'valmask.png'))):
    x, lab, wm, et, _ = UN.load_data(DIR, p); vm = UN.read_valmask(DIR, p, lab.shape); tl = lab.copy(); tl[vm] = 255
    P = dict(plate=p, x=x, lab=tl, wm=wm, et=et, vint=cv2.integral(vm.astype(np.uint8))); rng = np.random.default_rng(1); bad = 0; xmax = 0; C = UN.CROP
    for _ in range(50000):
        y, xx = UN.draw_crop(rng, P); bad += bool(vm[y:y + C, xx:xx + C].any()); xmax = max(xmax, int(xx) + C)
    cut = int(np.nonzero(vm.any(0))[0][0]) if vm.any() else None
    a = dict(crops=50000, touching_val=bad, val_starts_at_x=cut, furthest_crop_right_edge=xmax)
    S, _ = EN.load_data(DIR, p); H, W = S.shape[:2]; vf = cv2.resize(vm.astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST) > 0
    Q = dict(plate=p, S=S, vint=cv2.integral(vm.astype(np.uint8))); rng = np.random.default_rng(2); badl = 0; xmaxl = 0; C = EN.CROP
    for _ in range(50000):
        y, xx = EN.draw_crop(rng, Q); badl += bool(vf[y:y + C, xx:xx + C].any()); xmaxl = max(xmaxl, int(xx) + C)
    cutl = int(np.nonzero(vf.any(0))[0][0])
    ov[p] = dict(area=a, lines=dict(crops=50000, touching_val=badl, val_starts_at_x=cutl, furthest_crop_right_edge=xmaxl))
    print(p, json.dumps(ov[p]), flush=True); del S, vf
res['no_overlap'] = ov
json.dump(res, open(HERE + 'check_equal.json', 'w'), indent=1)
