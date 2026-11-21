"""verify-outline-quality: make a runnable, output-redirected copy of the PATCHED blocks_noguide.py
(patched/blocks_noguide.py) -> patched/blocks_noguide_redirected.py. Steps 1-2 (the networks, untouched by the diff)
are replaced by reading the batch's stored maps (unet_data/N_pred_area_ng1.png, N_lines_lines_ng1.png); step 3 calls
patched/outlines_redirected.py; every output (outlines, N_edges.json, N_blocks_ng.json) goes to bng_run/. --ignore-guide
lets it run on plate 44 (which has a guide). Each edit must apply exactly once.
    python redirect_bng.py
    VENV_PY patched/blocks_noguide_redirected.py 44 5 --ignore-guide"""
import os
HERE = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/') + '/'
s = open(HERE + 'patched/blocks_noguide.py', encoding='utf8').read()
E = [
    ("import torch\n", ""),
    ("import _ws  # noqa: E402\nimport unet as A, edgenet as E  # noqa: E402\n", ""),
    ("SP = _ws.DATA; U = SP + 'unet_data/';",
     "SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; U = SP + 'unet_data/'; OUT = HERE.replace(chr(92), '/') + '/../bng_run/'; os.makedirs(OUT, exist_ok=True);"),
    ("    p = A.predict_full(na, dev, np.dstack([img[:, :, ::-1], z, z])); pa = (p * 255).astype(np.uint8); cv2.imwrite(U + f'{N}_pred_{AREA}.png', pa)\n",
     "    pa = cv2.imread(U + f'{N}_pred_{AREA}.png', 0); p = pa / 255.0   # REDIRECTED: stored map instead of the network\n"),
    ("    inkimg, _ = E.ink_image(full); Z = np.zeros((H, W), np.uint8)\n", ""),
    ("    x = np.dstack([full[:, :, ::-1], inkimg, Z, Z, cv2.resize(pa, (W, H), interpolation=cv2.INTER_LINEAR)])\n", ""),
    ("    q = E.predict_full(nl, dev, x); cv2.imwrite(U + f'{N}_lines_{LINES}.png', (q * 255).astype(np.uint8))\n",
     "    q = cv2.imread(U + f'{N}_lines_{LINES}.png', 0) / 255.0   # REDIRECTED: stored map instead of the network\n"),
    ("    if os.path.exists(U + f'{N}_guide.png'):", "    if os.path.exists(U + f'{N}_guide.png') and '--ignore-guide' not in sys.argv:"),
    ("[sys.executable, os.path.join(HERE, 'outlines.py'), N, AREA, LINES]", "[sys.executable, os.path.join(HERE, 'outlines_redirected.py'), N, AREA, LINES, OUT + f'{N}/']"),
    ("open(SP + f'picks22_guided/22-{N}/outlines.json', encoding='utf8')", "open(OUT + f'{N}/outlines.json', encoding='utf8')"),
    ("open(U + f'{N}_edges.json.tmp', 'w', encoding='utf8', newline='\\n')); os.replace(U + f'{N}_edges.json.tmp', U + f'{N}_edges.json')",
     "open(OUT + f'{N}_edges.json.tmp', 'w', encoding='utf8', newline='\\n')); os.replace(OUT + f'{N}_edges.json.tmp', OUT + f'{N}_edges.json')"),
    ("open(U + f'{N}_blocks_ng.json', 'w'", "open(OUT + f'{N}_blocks_ng.json', 'w'"),
    ("    for m in (AREA, LINES):\n        if not os.path.exists(U + f'models/{m}.pt'): sys.exit(f'no network {m} yet (unet_data/models/{m}.pt): train it first with train_noguide.py')\n", ""),
    ("    dev = A.device()\n    na = A.UNet(); na.load_state_dict(torch.load(U + f'models/{AREA}.pt', map_location='cpu')); na.to(dev)\n    nl = A.UNet(classes=2, in_ch=7); nl.load_state_dict(torch.load(U + f'models/{LINES}.pt', map_location='cpu')); nl.to(dev)\n",
     "    dev = na = nl = None   # REDIRECTED: no networks\n"),
]
for a, b in E:
    assert s.count(a) == 1, (a[:90], s.count(a)); s = s.replace(a, b)
body = s.split('"""', 2)[2]
for bad in ('_ws', 'imwrite(U', "open(U + f'{N}_edges", "open(U + f'{N}_blocks", "picks22_guided/22-{N}/outlines.json', encoding", 'torch.load'):
    assert bad not in body, bad
open(HERE + 'patched/blocks_noguide_redirected.py', 'w', encoding='utf8', newline='\n').write(s); print('wrote patched/blocks_noguide_redirected.py')
