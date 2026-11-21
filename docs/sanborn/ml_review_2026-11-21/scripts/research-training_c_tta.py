# read-only CPU check: does flip/transpose test-time augmentation help area_ng1 on held-out plate 44?
import sys, time, json, torch, numpy as np, cv2
torch.set_num_threads(6)
sys.argv = ['x', '--no-guide']
sys.path.insert(0, r'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/tools/sanborn/unet'); sys.path.insert(0, r'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/tools/sanborn')
import unet as A
OUT = r'C:/Users/peckb/AppData/Local/Temp/claude/8945a8e3044b4e4c/2a2bcb12-80e8-4366-9a59-3be15cce3445/scratchpad/ml_review/research-training/'
dev = torch.device('cpu'); net = A.UNet(); net.load_state_dict(torch.load(A.DATA + 'models/area_ng1.pt', map_location='cpu', weights_only=False)); net.eval()
img, lab = A.load('44'); wm, et = A.load_edge('44', lab)
T = [(lambda a: a, lambda a: a), (lambda a: a[:, ::-1], lambda a: a[:, ::-1]), (lambda a: a[::-1], lambda a: a[::-1]), (lambda a: a.transpose(1, 0, 2), lambda a: a.T)]
ps, es = [], []; t0 = time.time()
for f, g in T:
    p = A.predict_full(net, dev, np.ascontiguousarray(f(img))); ps.append(np.ascontiguousarray(g(p))); es.append(np.ascontiguousarray(g(A.predict_full.edge)))
    print('pass', len(ps), round(time.time() - t0), 's', json.dumps(A.score(ps[-1], lab, et, es[-1])), flush=True)
saved = cv2.imread(A.DATA + '44_pred_area_ng1.png', 0).astype(np.float32) / 255
print('saved png (GPU run) ', json.dumps(A.score(saved, lab, et)))
print('max |cpu id - saved png|', round(float(np.abs(ps[0] - saved).max()), 3), 'share differing > 0.02', round(float((np.abs(ps[0] - saved) > 0.02).mean()), 5))
m = np.mean(ps, 0); me = np.mean(es, 0)
print('TTA mean of 4        ', json.dumps(A.score(m, lab, et, me)))
np.save(OUT + 'c_tta_44_mean.npy', (m * 255).astype(np.uint8)); np.save(OUT + 'c_tta_44_id.npy', (ps[0] * 255).astype(np.uint8))
# disagreement between transforms as an uncertainty signal
v = np.std(ps, 0); ok = lab != 255; err = ((m > 0.5) != (lab == 1)) & ok
for thr in (0.05, 0.1, 0.2):
    hi = (v > thr) & ok; print(f'TTA std > {thr}: {hi.sum() / ok.sum():.3f} of ground, holds {err[hi].sum() / max(1, err.sum()):.3f} of the errors; error rate there {err[hi].mean():.3f} vs {err[ok & ~hi].mean():.4f} elsewhere')
