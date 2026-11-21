"""verify-inference (21 Nov 2026): make plate maps with the PATCHED repo code itself, on the CPU, with every output
redirected into this folder.

    VENV_PYTHON verify_maps_patched.py WHICH TAG AREA_TTA N [N ...] [--threads 8]

WHICH: 'default' (applytest/default: unet.py.diff + edgenet.py.diff + blocks_noguide.py.diff applied with GNU patch
to copies of today's repo files) or 'up400' (the same with blocks_noguide_with_400ft_option.py.diff).
The patched blocks_noguide.py is imported as a real module (so its imports of the patched unet.py and edgenet.py
run as they would in the repo); only `_ws` is replaced by a stub whose DATA is the real data/sanborn/ (it is the
only thing the three files take from _ws). Then:
  - U (the output folder of run()) is pointed at maps/TAG/ in this folder,
  - AREA_TTA is set from the command line (8 = the diff as written, 1 = the batch's single pass),
  - run(N, nets, pred_only=True) is called: it stops after the two networks, so nothing else is written.
Device: the CPU (this checker may not use the GPU). The batch ran on the GPU (DirectML).
"""
import importlib.util, json, os, sys, time, types
sys.dont_write_bytecode = True
V = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-21/verify-inference/'
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
argv = sys.argv[1:]; thr = 8
if '--threads' in argv:
    i = argv.index('--threads'); thr = int(argv[i + 1]); argv = argv[:i] + argv[i + 2:]
args = [a for a in argv if not a.startswith('--')]
which, tag, area_tta, plates = args[0], args[1], int(args[2]), args[3:]
ws = types.ModuleType('_ws'); ws.DATA = SP; sys.modules['_ws'] = ws
code = V + f'applytest/{which}/tools/sanborn/unet/'
sys.argv = [code + 'blocks_noguide.py']                 # edgenet reads sys.argv at import (--area, --no-guide)
spec = importlib.util.spec_from_file_location('blocks_noguide', code + 'blocks_noguide.py')
B = importlib.util.module_from_spec(spec); spec.loader.exec_module(B)
import torch
torch.set_num_threads(thr)
assert B.A.__file__.replace('\\', '/').startswith(V), B.A.__file__     # the patched copies, not the repo's
assert B.E.__file__.replace('\\', '/').startswith(V), B.E.__file__
out = V + f'maps/{tag}/'; os.makedirs(out, exist_ok=True)
B.U = out; B.AREA_TTA = area_tta
dev = torch.device('cpu')
na = B.A.UNet(); na.load_state_dict(torch.load(SP + f'unet_data/models/{B.AREA}.pt', map_location='cpu')); na.to(dev)
nl = B.A.UNet(classes=2, in_ch=7); nl.load_state_dict(torch.load(SP + f'unet_data/models/{B.LINES}.pt', map_location='cpu')); nl.to(dev)
log = {}
for n in plates:
    t0 = time.time(); B.run(n, (dev, na, nl), True); log[n] = dict(seconds=round(time.time() - t0, 1), which=which, area_tta=area_tta, device='cpu', threads=thr,
                                                                  unet=B.A.__file__, edgenet=B.E.__file__)
    print(n, json.dumps(log[n]), flush=True)
json.dump(log, open(out + 'made.json', 'w'), indent=1)
