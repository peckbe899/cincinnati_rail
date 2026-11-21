"""merge/v-batch: make plates of the sandbox real (scans and bins copied instead of empty placeholders). Writes only in v-batch/sandbox.
    python -B sandbox_add.py N [N ...]
"""
import json, os, shutil, sys
import common as C
SD = C.mine(C.ME + 'sandbox/data/sanborn') + '/'
made = json.load(open(C.ME + 'sandbox/sandbox_made.json'))
for n in sys.argv[1:]:
    for f in (f'cufp/22-{n}.jpg', f'cufp/{n}/png_alpha_s4.npy', f'unet_data/{n}_bins.png', f'unet_data/{n}_pred_area_ng1.png', f'unet_data/{n}_lines_lines_ng1.png', f'unet_data/{n}_guide.png'):
        if os.path.exists(C.DATA + f) and os.path.exists(SD + f): shutil.copy2(C.DATA + f, C.mine(SD + f))
    made['plates'][n] = 'real'; made['real'].append(n)
json.dump(made, open(C.ME + 'sandbox/sandbox_made.json', 'w'), indent=1); print('real now:', made['real'])
