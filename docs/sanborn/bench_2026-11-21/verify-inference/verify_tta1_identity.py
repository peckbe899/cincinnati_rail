"""verify-inference: does the patched predict_full with tta=1 give exactly what today's repo predict_full gives?
(CPU, on a crop of plate 44 so it is quick.) Both functions are cut out with ast: the ORIGINAL from
tools/sanborn/unet/unet.py and edgenet.py (read only), the PATCHED from applytest/default/ (diffs applied to copies).
Also checks that tta=8 on a crop is invariant to turning the input (the answer for a turned crop, turned back, must
equal the answer for the crop up to float rounding), which is what an exact D4 average must satisfy.

    VENV_PYTHON verify_tta1_identity.py
"""
import ast, json, sys, time
sys.dont_write_bytecode = True
import numpy as np, cv2, torch, torch.nn as nn, torch.nn.functional as F
torch.set_num_threads(4)
V = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-21/verify-inference/'
R = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/tools/sanborn/unet/'
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'


def cut(path, names):
    src = open(path, encoding='utf8').read(); keep = []
    for node in ast.parse(src).body:
        nm = node.name if isinstance(node, (ast.FunctionDef, ast.ClassDef)) else (getattr(node.targets[0], 'id', None) if isinstance(node, ast.Assign) else None)
        if nm in names: keep.append(ast.get_source_segment(src, node))
    return '\n'.join(keep)


base = dict(np=np, cv2=cv2, torch=torch, nn=nn, F=F)
o_u = dict(base); exec(cut(R + 'unet.py', {'block', 'UNet', 'norm', 'predict_full'}), o_u)
p_u = dict(base); exec(cut(V + 'applytest/default/tools/sanborn/unet/unet.py', {'TTA', 'turn', 'unturn', 'norm', 'predict_full'}), p_u)
o_e = dict(base); exec(cut(R + 'edgenet.py', {'norm', 'predict_full', 'ink_image'}), o_e)
p_e = dict(base, TTA=p_u['TTA'], turn=p_u['turn'], unturn=p_u['unturn']); exec(cut(V + 'applytest/default/tools/sanborn/unet/edgenet.py', {'norm', 'predict_full'}), p_e)
dev = torch.device('cpu')
na = o_u['UNet'](); na.load_state_dict(torch.load(SP + 'unet_data/models/area_ng1.pt', map_location='cpu')); na.eval()
nl = o_u['UNet'](classes=2, in_ch=7); nl.load_state_dict(torch.load(SP + 'unet_data/models/lines_ng1.pt', map_location='cpu')); nl.eval()
full = cv2.imread(SP + 'cufp/22-44.jpg')[2000:4400, 3000:5800]          # a 2800 x 2400 crop
H, W = full.shape[:2]; img = cv2.resize(full, (W // 2, H // 2), interpolation=cv2.INTER_AREA); z = np.zeros(img.shape[:2], np.uint8)
xa = np.dstack([img[:, :, ::-1], z, z]); res = {}
a0 = o_u['predict_full'](na, dev, xa); e0 = o_u['predict_full'].edge
a1 = p_u['predict_full'](na, dev, xa, tta=1); e1 = p_u['predict_full'].edge
res['unet_tta1_identical'] = bool(np.array_equal(a0, a1)); res['unet_edge_tta1_identical'] = bool(np.array_equal(e0, e1))
pa = (a0 * 255).astype(np.uint8)
ink, _ = o_e['ink_image'](full); Z = np.zeros((H, W), np.uint8)
xl = np.dstack([full[:, :, ::-1], ink, Z, Z, cv2.resize(pa, (W, H), interpolation=cv2.INTER_LINEAR)])
l0 = o_e['predict_full'](nl, dev, xl); l1 = p_e['predict_full'](nl, dev, xl, tta=1)
res['edgenet_tta1_identical'] = bool(np.array_equal(l0, l1))
# D4 equivariance of one tile, using the patched TTA / turn / unturn exactly as predict_full's inner loop does
# (predict_full itself pads the image asymmetrically, so a whole-image test would mix in the padding).
TT, tn, un = p_u['TTA'], p_u['turn'], p_u['unturn']
def tile_mean(x, ts):
    with torch.no_grad():
        o = na(torch.cat([tn(x, k, f) for k, f in ts])); pb = F.softmax(o[:, :2], 1)[:, 1]
    return sum(un(pb[i], k, f) for i, (k, f) in enumerate(ts)) / len(ts)
x = p_u['norm'](xa[None, :768, :768]); xr = torch.rot90(x, 1, (-2, -1)); xf = torch.flip(x, (-1,))
for n_ in (1, 4, 8):
    q = tile_mean(x, TT[n_]); qr = torch.rot90(tile_mean(xr, TT[n_]), -1, (-2, -1)); qf = torch.flip(tile_mean(xf, TT[n_]), (-1,))
    res[f'tile_tta{n_}_rot90_max_abs'] = round(float((qr - q).abs().max()), 6); res[f'tile_tta{n_}_flip_max_abs'] = round(float((qf - q).abs().max()), 6)
    res[f'tile_tta{n_}_rot90_decision_flips'] = round(float(((qr > 0.5) != (q > 0.5)).float().mean()), 6)
res['tta8_set_is_D4'] = len(set(TT[8])) == 8 and all(k in range(4) for k, f in TT[8])
json.dump(res, open(V + 'logs/tta1_identity.json', 'w'), indent=1); print(json.dumps(res, indent=1))
