"""prep_var.py (diag/verify, 25 Nov 2026): map folders for the outline-step robustness test. For each pair as the run
made its maps (train_v2_runs/eval/S/maps44) and the baseline (bench44_maps), copies the six grids' maps into
diag/verify/mix/<M>__<VAR>/maps44/gridK, where VAR names an outline-step setting (run with outlines_var.py).
    python -B prep_var.py VAR [VAR ...]
"""
import os, shutil, sys
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
D = SP + 'bench_2026-11-25/diag/verify/mix/'
SRC = {'base': SP + 'bench44_maps/grid{g}/'}
for s in ('V1S1', 'V1S2', 'V2S1', 'V2S2'): SRC[s] = SP + f'train_v2_runs/eval/{s}/maps44/grid{{g}}/'
for var in sys.argv[1:]:
    for m, src in SRC.items():
        for g in range(6):
            d = D + f'{m}__{var}/maps44/grid{g}/'; os.makedirs(d, exist_ok=True)
            for f in ('44_area.png', '44_lines.png'):
                if not os.path.exists(d + f): shutil.copyfile(src.format(g=g) + f, d + f)
            open(d + 'source.txt', 'w').write(f'maps {src.format(g=g)}\noutline setting {var}\n')
print('ok')
