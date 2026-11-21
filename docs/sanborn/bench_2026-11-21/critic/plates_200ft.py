"""critic: do the plate-44 marker gains transfer to 200-ft cut plates, where visual-cut counted many missed alleys?

1. Runs the repo's outline step (harness/outlines_copy.py) and outline-quality's proposal
   (variants/oq_outlines_redirected.py) on the batch's own maps of 60B and 66 (unet_data, read-only), writing only to
   critic/plates/N_{cur,oq}/, in the networks' venv on the CPU. Prints the block counts.
2. Probes one missed alley that visual-cut marked on 60B (block 67, 'merged across alley', full px x 2100-2300,
   y 1150-1700): share of P(line) > 0.5 and P(block) in the strip, and writes plates/60B_alley_67_scan_lines_area.jpg
   (scan | P(line) | P(block)).
    cd data/sanborn; python bench_2026-11-21/critic/plates_200ft.py
"""
import json, os, subprocess
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/') + '/'
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
VPY = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/tools/sanborn/unet/.venv/Scripts/python.exe'
res = {}
for N in ('60B', '66'):
    for v, f in (('cur', HERE + 'harness/outlines_copy.py'), ('oq', HERE + 'variants/oq_outlines_redirected.py')):
        out = HERE + f'plates/{N}_{v}'
        if not os.path.exists(out + '/outlines.json'):
            subprocess.run([VPY, f, N, f'unet_data/{N}_pred_area_ng1.png', f'unet_data/{N}_lines_lines_ng1.png', out], cwd=SP, check=True,
                           env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'), capture_output=True)
        rep = json.load(open(out + f'/{N}_outlines.json')); res[f'{N}_{v}'] = {k: rep.get(k) for k in ('blocks', 'sides', 'short_pieces', 'bridges')}
    res[f'{N}_batch_record'] = {k: json.load(open(SP + f'unet_data/{N}_outlines.json')).get(k) for k in ('blocks', 'sides', 'short_pieces')}
L = cv2.imread(SP + 'unet_data/60B_lines_lines_ng1.png', 0); A = cv2.imread(SP + 'unet_data/60B_pred_area_ng1.png', 0); im = cv2.imread(SP + 'cufp/22-60B.jpg')
x0, x1, y0, y1 = 2100, 2300, 1150, 1700
g = cv2.cvtColor(im[y0:y1, x0:x1], cv2.COLOR_BGR2GRAY); col = g.mean(0); xa = x0 + int(np.argmax(col))       # the alley: brightest column
Ls = L[y0:y1, xa - 12:xa + 13]; As = A[y0 // 2:y1 // 2, (xa - 12) // 2:(xa + 13) // 2]
res['60B_alley67'] = dict(alley_x=xa, line_share_p05_in_alley_strip=round(float((Ls > 127).mean()), 4), block_share_p05_in_alley_strip=round(float((As > 127).mean()), 4))
cv2.imwrite(HERE + 'plates/60B_alley_67_scan_lines_area.jpg', np.hstack([im[y0:y1, x0:x1], cv2.cvtColor(L[y0:y1, x0:x1], cv2.COLOR_GRAY2BGR),
            cv2.cvtColor(cv2.resize(A[y0 // 2:y1 // 2, x0 // 2:x1 // 2], (x1 - x0, y1 - y0), interpolation=cv2.INTER_NEAREST), cv2.COLOR_GRAY2BGR)]))
json.dump(res, open(HERE + 'plates_200ft.json', 'w'), indent=1); print(json.dumps(res, indent=1))
