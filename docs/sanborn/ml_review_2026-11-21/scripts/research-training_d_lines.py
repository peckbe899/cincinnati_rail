# read-only CPU check on plate 44: (1) saved lines_v2 (guided, 15 Nov) scored against TODAY's target;
# (2) lines_ng1 rerun (identity) and a threshold sweep; (3) 4-way TTA on a 3328 x 3328 window
import sys, time, json, torch, numpy as np, cv2
torch.set_num_threads(8)
sys.argv = ['x', '--no-guide', '--area', 'area_ng1']
sys.path.insert(0, r'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/tools/sanborn/unet'); sys.path.insert(0, r'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/tools/sanborn')
import edgenet as E, unet as A
OUT = r'C:/Users/peckb/AppData/Local/Temp/claude/8945a8e3044b4e4c/2a2bcb12-80e8-4366-9a59-3be15cce3445/scratchpad/ml_review/research-training/'
t0 = time.time(); x, t, _ = E.load('44'); print('loaded', x.shape, round(time.time() - t0), 's', flush=True)
v2 = cv2.imread(E.DATA + '44_lines_lines_v2.png', 0).astype(np.float32) / 255
print('lines_v2 (guided, saved 15 Nov) vs current target:', json.dumps(E.score(v2, t)), flush=True)
net = A.UNet(classes=2, in_ch=7); net.load_state_dict(torch.load(E.DATA + 'models/lines_ng1.pt', map_location='cpu', weights_only=False)); net.eval(); dev = torch.device('cpu')
p = E.predict_full(net, dev, x); np.save(OUT + 'd_lines_ng1_44.npy', (p * 255).astype(np.uint8))
print('lines_ng1 rerun cpu:', json.dumps(E.score(p, t)), round(time.time() - t0), 's', flush=True)
for thr in (0.3, 0.4, 0.5, 0.6, 0.7, 0.8):
    s = E.score((p > thr).astype(np.float32), t); f1 = 2 * s['precision'] * s['recall'] / max(1e-9, s['precision'] + s['recall'])
    s2 = E.score((v2 > thr).astype(np.float32), t); f2 = 2 * s2['precision'] * s2['recall'] / max(1e-9, s2['precision'] + s2['recall'])
    print(f'thr {thr}: ng1 P {s["precision"]:.3f} R {s["recall"]:.3f} F1 {f1:.3f} | v2 P {s2["precision"]:.3f} R {s2["recall"]:.3f} F1 {f2:.3f}', flush=True)
# TTA on a window
y0, x0, S = 1800, 3600, 3328; xs = x[y0:y0 + S, x0:x0 + S]; ts = t[y0:y0 + S, x0:x0 + S]
T = [(lambda a: a, lambda a: a), (lambda a: a[:, ::-1], lambda a: a[:, ::-1]), (lambda a: a[::-1], lambda a: a[::-1]), (lambda a: a.transpose(1, 0, 2), lambda a: a.T)]
ps = [np.ascontiguousarray(g(E.predict_full(net, dev, np.ascontiguousarray(f(xs))))) for f, g in T]
print('window line px', int((ts == 1).sum()), 'id:', json.dumps(E.score(ps[0], ts)), '| TTA4 mean:', json.dumps(E.score(np.mean(ps, 0), ts)), round(time.time() - t0), 's', flush=True)
