"""Check the patched predict code (patched/unet.py, patched/edgenet.py) without importing the repo modules.

    VENV_PYTHON test_patch.py [--cpu]

The functions TTA, turn, unturn, norm, predict_full are cut out of the patched files with ast and run in a plain
namespace (so _ws is not imported and nothing is written under tools/). On plate 44:
  - unet.predict_full(tta=1) and edgenet.predict_full(tta=1) must equal the batch's stored maps byte for byte;
  - unet.predict_full(tta=8) must match infer_lib's a_tta8 map (maps/a_tta8/44_area.png) to within 1/255.
Writes logs/test_patch.json.
"""
import ast, json, os, sys, time
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, cv2, torch, torch.nn.functional as F
import infer_lib as L


def cut(path, names):
    src = open(path, encoding='utf8').read(); tree = ast.parse(src); keep = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.Assign)):
            nm = node.name if isinstance(node, ast.FunctionDef) else getattr(node.targets[0], 'id', None)
            if nm in names: keep.append(ast.get_source_segment(src, node))
    return '\n'.join(keep)


ns_u = dict(np=np, cv2=cv2, torch=torch, F=F); exec(cut(L.HERE + 'patched/unet.py', {'TTA', 'turn', 'unturn', 'norm', 'predict_full'}), ns_u)
ns_e = dict(np=np, cv2=cv2, torch=torch, F=F, TTA=ns_u['TTA'], turn=ns_u['turn'], unturn=ns_u['unturn'])
exec(cut(L.HERE + 'patched/edgenet.py', {'norm', 'predict_full'}), ns_e)
dev = torch.device('cpu') if '--cpu' in sys.argv else L.device(); dev, na, nl = L.load_nets(dev)
full = cv2.imread(L.SP + 'cufp/22-44.jpg'); H, W = full.shape[:2]
img = cv2.resize(full, (W // 2, H // 2), interpolation=cv2.INTER_AREA); z = np.zeros(img.shape[:2], np.uint8); xa = np.dstack([img[:, :, ::-1], z, z])
res = {}
t0 = time.time(); p1 = ns_u['predict_full'](na, dev, xa); res['unet_tta1_s'] = round(time.time() - t0, 2)
res['unet_tta1_equals_batch'] = bool((L.u8(p1) == cv2.imread(L.U + '44_pred_area_ng1.png', 0)).all())
t0 = time.time(); p8 = ns_u['predict_full'](na, dev, xa, tta=8); res['unet_tta8_s'] = round(time.time() - t0, 2)
ref8 = cv2.imread(L.HERE + 'maps/a_tta8/44_area.png', 0); d = np.abs(L.u8(p8).astype(int) - ref8.astype(int))
res['unet_tta8_vs_infer_lib'] = dict(max_abs=int(d.max()), share_differ=round(float((d > 0).mean()), 6), decision_differs=round(float(((L.u8(p8) > 127) != (ref8 > 127)).mean()), 7))
inkimg, _ = L.ink_image(full); Z = np.zeros((H, W), np.uint8)
xl = np.dstack([full[:, :, ::-1], inkimg, Z, Z, cv2.resize(cv2.imread(L.U + '44_pred_area_ng1.png', 0), (W, H), interpolation=cv2.INTER_LINEAR)])
t0 = time.time(); q1 = ns_e['predict_full'](nl, dev, xl); res['edgenet_tta1_s'] = round(time.time() - t0, 2)
res['edgenet_tta1_equals_batch'] = bool((L.u8(q1) == cv2.imread(L.U + '44_lines_lines_ng1.png', 0)).all())
json.dump(res, open(L.HERE + 'logs/test_patch.json', 'w'), indent=1); print(json.dumps(res, indent=1))
