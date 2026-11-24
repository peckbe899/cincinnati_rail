"""review-code: the staged trainers' --data path on the CPU, on review-code/testdata (small crops, small batches).

    VENV -B test_train.py [area|lines|sampler|all]

Checks, each for unet.train_data (area) and edgenet.train_data (lines):
  - same seed twice -> identical NAME.pt and NAME_last.pt; another seed -> different;
  - NAME.pt rescored on the validation pixels = the best history entry, NAME_last.pt = the last entry, and the best
    entry is the first maximum of the history;
  - no training crop touches a validation pixel (every crop drawn is checked against the full valmask);
  - the model json's seed, manifest sha, git and plate records.
sampler: a 1-conv stand-in network, many iterations: the crops per plate against the --weights shares.
Writes review-code/test_train.json. Nothing outside review-code/ is written.
"""
import hashlib, json, os, sys, time
sys.dont_write_bytecode = True
REPO = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/'
STAGED = REPO + 'data/sanborn/bench_2026-11-23/train/staged/tools/sanborn/unet/'
RC = REPO + 'data/sanborn/bench_2026-11-23/train/review-code/'
sys.argv = [sys.argv[0]] + sys.argv[1:]
WHAT = sys.argv[1] if len(sys.argv) > 1 else 'all'
sys.argv = [sys.argv[0]]
sys.path.insert(0, REPO + 'tools/sanborn'); sys.path.insert(0, STAGED)
import numpy as np, cv2, torch
import unet as U, edgenet as E
torch.set_num_threads(8)
D = RC + 'testdata/'; OUT = RC + 'test_models/'; os.makedirs(OUT, exist_ok=True)


def cpu():
    return torch.device('cpu')
cpu.name = 'cpu (review-code test)'
U.device = cpu; E.device = cpu
U.CROP, U.BATCH = 128, 4
E.CROP, E.BATCH = 192, 2

# every crop drawn is recorded with its plate
CROPS = []
_ud, _ed = U.draw_crop, E.draw_crop
def ud(rng, P):
    y, x = _ud(rng, P); CROPS.append(('area', P['plate'], int(y), int(x))); return y, x
def ed(rng, P):
    y, x = _ed(rng, P); CROPS.append(('lines', P['plate'], int(y), int(x))); return y, x
U.draw_crop = ud; E.draw_crop = ed


def sd_sha(f):
    s = torch.load(f, map_location='cpu', weights_only=True); h = hashlib.sha256()
    for k in sorted(s): h.update(k.encode()); h.update(s[k].numpy().tobytes())
    return h.hexdigest()[:16]


def crops_clean(kind, plate):
    """no crop of this kind on this plate touches a validation pixel (full-size valmask for lines)"""
    v = cv2.imread(D + plate + '/valmask.png', 0)
    if v is None: return None
    v = v > 0; bad = 0; n = 0
    if kind == 'lines':
        full = cv2.imread(D + plate + '/full.jpg'); H, W = full.shape[:2]; vf = cv2.resize(v.astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST) > 0; C = E.CROP
        for k, p, y, x in CROPS:
            if k == 'lines' and p == plate: n += 1; bad += bool(vf[y:y + C, x:x + C].any())
        closest = min((int(np.nonzero(vf.any(0))[0][0]) - (x + C)) for k, p, y, x in CROPS if k == 'lines' and p == plate)
    else:
        C = U.CROP
        for k, p, y, x in CROPS:
            if k == 'area' and p == plate: n += 1; bad += bool(v[y:y + C, x:x + C].any())
        closest = min((int(np.nonzero(v.any(0))[0][0]) - (x + C)) for k, p, y, x in CROPS if k == 'area' and p == plate)
    return dict(crops=n, touching_val=bad, closest_gap_px=closest)


def area_rescore(pt, plate='T1'):
    x, lab, wm, et, _ = U.load_data(D, plate); vm = U.read_valmask(D, plate, lab.shape)
    y0, y1, x0, x1 = U.bbox(vm); lv = lab[y0:y1, x0:x1].copy(); lv[~vm[y0:y1, x0:x1]] = 255
    net = U.UNet(); net.load_state_dict(torch.load(pt, map_location='cpu', weights_only=True)); c = U.counts(U.predict_full(net, cpu(), np.ascontiguousarray(x[y0:y1, x0:x1])), lv)
    return round(float(c[4] / max(1, c[5])), 6), round(float(c[1] / max(1, c[0])), 6)


def lines_rescore(pt, plate='T1'):
    S, _ = E.load_data(D, plate); H, W = S.shape[:2]; vh = U.read_valmask(D, plate, (H // 2, W // 2))
    vf = cv2.resize(vh.astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST) > 0
    y0, y1, x0, x1 = U.bbox(vf); xv, tv, _ = E.build(S, y0, y1, x0, x1); mv = vf[y0:y1, x0:x1]; tv[~mv] = 255
    net = U.UNet(classes=2, in_ch=7); net.load_state_dict(torch.load(pt, map_location='cpu', weights_only=True))
    return E.prf(E.line_counts(E.predict_full(net, cpu(), xv), tv, mv))['f1']


res = {}
if WHAT in ('area', 'all'):
    r = {}
    for tag, seed in (('a1', 1), ('a1b', 1), ('a2', 2)):
        t0 = time.time(); U.train_data(tag, D, ['T1', 'T2'], 30, seed, {}, OUT, 5); r[tag] = dict(seconds=round(time.time() - t0, 1), best=sd_sha(OUT + tag + '.pt'), last=sd_sha(OUT + tag + '_last.pt'))
    j = json.load(open(OUT + 'a1.json', encoding='utf8')); hist = j['history']
    vals = [(h['iter'], h['val_pooled']['iou_street'], h['val_pooled']['accuracy']) for h in hist]
    r['history'] = vals; r['json_best'] = j['best']
    first_max = max(vals, key=lambda v: (v[1], v[2], -v[0]))
    r['best_is_first_max'] = j['best']['iter'] == first_max[0]
    r['rescore_best'] = area_rescore(OUT + 'a1.pt'); r['rescore_last'] = area_rescore(OUT + 'a1_last.pt')
    r['rescore_best_matches'] = r['rescore_best'] == (j['best']['iou_street'], j['best']['accuracy'])
    r['rescore_last_matches'] = r['rescore_last'][0] == round(hist[-1]['val_pooled']['iou_street'], 6)
    r['same_seed_identical'] = r['a1']['best'] == r['a1b']['best'] and r['a1']['last'] == r['a1b']['last']
    r['other_seed_differs'] = r['a1']['last'] != r['a2']['last']
    r['crops_T1'] = crops_clean('area', 'T1')
    r['json_fields'] = {k: j.get(k) for k in ('seed', 'manifest_sha256', 'git', 'device', 'crops_drawn')}
    r['json_plates'] = [{k: v for k, v in p.items() if k != 'files'} for p in j['plates']]
    res['area'] = r; print(json.dumps(r, indent=1)[:4000], flush=True)
if WHAT in ('lines', 'all'):
    CROPS.clear(); r = {}
    for tag, seed in (('l1', 1), ('l1b', 1), ('l2', 2)):
        t0 = time.time(); E.train_data(tag, D, ['T1', 'T2'], 20, seed, {}, OUT, 5); r[tag] = dict(seconds=round(time.time() - t0, 1), best=sd_sha(OUT + tag + '.pt'), last=sd_sha(OUT + tag + '_last.pt'))
    j = json.load(open(OUT + 'l1.json', encoding='utf8')); hist = j['history']
    vals = [(h['iter'], h['val_pooled']['f1']) for h in hist]; r['history'] = vals; r['json_best'] = j['best']
    r['rescore_best'] = lines_rescore(OUT + 'l1.pt'); r['rescore_last'] = lines_rescore(OUT + 'l1_last.pt')
    r['rescore_best_matches'] = r['rescore_best'] == j['best']['f1']; r['rescore_last_matches'] = r['rescore_last'] == hist[-1]['val_pooled']['f1']
    r['same_seed_identical'] = r['l1']['best'] == r['l1b']['best'] and r['l1']['last'] == r['l1b']['last']
    r['other_seed_differs'] = r['l1']['last'] != r['l2']['last']
    r['crops_T1'] = crops_clean('lines', 'T1')
    r['json_fields'] = {k: j.get(k) for k in ('seed', 'manifest_sha256', 'device', 'crops_drawn')}
    res['lines'] = r; print(json.dumps(r, indent=1)[:4000], flush=True)
if WHAT in ('sampler', 'all'):
    import torch.nn as nn
    class Tiny(nn.Module):
        def __init__(self, classes=3, in_ch=5, **k): super().__init__(); self.c = nn.Conv2d(in_ch, classes, 1)
        def forward(self, x): return self.c(x)
    UN0, EN0 = U.UNet, E.UNet; U.UNet = Tiny; E.UNet = Tiny; r = {}
    for kind, mod, iters, B in (('area', U, 400, U.BATCH), ('lines', E, 400, E.BATCH)):
        CROPS.clear(); w = {'T1': 1.0, 'T2': 0.5, 'T3': 0.5}
        mod.train_data('samp_' + kind, D, ['T1', 'T2', 'T3'], iters, 7, w, OUT, 10 ** 9)
        j = json.load(open(OUT + f'samp_{kind}.json', encoding='utf8')); n = sum(j['crops_drawn'].values())
        r[kind] = dict(crops_drawn=j['crops_drawn'], share={k: round(v / n, 3) for k, v in j['crops_drawn'].items()}, expected={k: v / sum(w.values()) for k, v in w.items()}, crops_T1=crops_clean(kind, 'T1'))
    U.UNet, E.UNet = UN0, EN0
    res['sampler'] = r; print(json.dumps(r, indent=1), flush=True)
json.dump(res, open(RC + f'test_train_{WHAT}.json', 'w'), indent=1)
