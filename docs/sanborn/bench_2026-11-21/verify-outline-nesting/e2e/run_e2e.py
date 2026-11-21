"""verify-outline-nesting: end-to-end run of the PATCHED repo files, unmodified (21 Nov 2026).

    <venv python> run_e2e.py 44 90

The patched tools/sanborn/unet/outlines.py and blocks_noguide.py (outline-nesting.diff applied with patch -p1 to copies,
see ../repo_copy) are copied here under e2e/tools/sanborn/unet/. A FAKE _ws.py (e2e/tools/sanborn/_ws.py) points DATA at
e2e/data/sanborn/, which holds copies of the inputs. blocks_noguide.run() is called with the two networks replaced by
the batch's own saved maps (unet_data/N_pred_area_ng1.png, N_lines_lines_ng1.png), so steps 3 and 4 run exactly as
the patched code would run them, and every output lands under e2e/data/sanborn/. No network is run or trained.
"""
import os, sys, json
import numpy as np
import cv2
E = os.path.dirname(os.path.abspath(__file__))
REAL_UNET = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/tools/sanborn/unet'
sys.path.insert(0, REAL_UNET)                                  # unet.py, edgenet.py imported as modules (no writes on import)
sys.path.insert(0, os.path.join(E, 'tools', 'sanborn', 'unet'))  # the PATCHED blocks_noguide.py comes before the real one
sys.path.insert(0, os.path.join(E, 'tools', 'sanborn'))        # the fake _ws comes first
import _ws  # noqa: E402
assert _ws.DATA.lower().startswith(E.replace('\\', '/').lower()), _ws.DATA
import blocks_noguide as BN  # noqa: E402   (e2e/tools/sanborn/unet/blocks_noguide.py)
assert os.path.normcase(os.path.dirname(os.path.abspath(BN.__file__))) == os.path.normcase(os.path.join(E, 'tools', 'sanborn', 'unet')), BN.__file__
assert BN.SP == _ws.DATA and BN.U == _ws.DATA + 'unet_data/'
REAL_U = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/unet_data/'
CUR = {}


def fake_area(net, dev, x):
    m = cv2.imread(REAL_U + f"{CUR['N']}_pred_area_ng1.png", 0); assert m.shape == x.shape[:2], (m.shape, x.shape)
    return (m.astype(np.float32) + 0.5) / 255.0


def fake_lines(net, dev, x):
    m = cv2.imread(REAL_U + f"{CUR['N']}_lines_lines_ng1.png", 0); assert m.shape == x.shape[:2], (m.shape, x.shape)
    return (m.astype(np.float32) + 0.5) / 255.0


BN.A.predict_full = fake_area; BN.E.predict_full = fake_lines
BN.E.ink_image = lambda full: (np.zeros(full.shape[:2], np.uint8), None)
for N in sys.argv[1:]:
    CUR['N'] = N
    BN.run(N, ('cpu', None, None), False)
    for k in ('pred_area_ng1', 'lines_lines_ng1'):
        f = f'{N}_{k}.png' if k.startswith('pred') else f'{N}_{k}.png'
        a = cv2.imread(BN.U + (f'{N}_pred_area_ng1.png' if k.startswith('pred') else f'{N}_lines_lines_ng1.png'), 0)
        b = cv2.imread(REAL_U + (f'{N}_pred_area_ng1.png' if k.startswith('pred') else f'{N}_lines_lines_ng1.png'), 0)
        print(N, k, 'rewritten map identical to the batch map:', bool((a == b).all()), flush=True)
