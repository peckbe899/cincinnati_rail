"""spot_pics.py (text_fix/step4, 27 Nov 2026): cut a window out of a plate for looking at by eye: scan | finder3 codes |
finder4 codes [| f3 bins | f4 bins of a run in runs/bins/<set>/]. Codes: 2 text sure magenta, 3 text by context pink,
1 line black, 4 shared blue, 5 other orange. Bins coloured as bins_compare.py (text magenta, railroad red, streetcar
orange-blue, lot line orange, block line green, building outline brown, pipe dark blue, sewer olive).
Also prints, for the window, the ink px (LAB L < 140) and the share called text (codes 2,3) by each mask, and the share in
bin 8 and bin 5 of each sort.
    cd data/sanborn; python -B bench_2026-11-26/text_fix/step4/code/spot_pics.py N X0 Y0 X1 Y1 OUT.png [RUN] [--zoom Z]"""
import sys, os
import numpy as np, cv2
SP = os.getcwd().replace('\\', '/') + '/'; ST = SP + 'bench_2026-11-26/text_fix/step4/'
a = sys.argv[1:]; zoom = float(a[a.index('--zoom') + 1]) if '--zoom' in a else 2.0
a = [x for i, x in enumerate(a) if x != '--zoom' and (i == 0 or a[i - 1] != '--zoom')]
N = a[0]; x0, y0, x1, y1 = map(int, a[1:5]); out = a[5]; run = a[6] if len(a) > 6 else None
assert os.path.normcase(os.path.abspath(out)).startswith(os.path.normcase(os.path.abspath(ST))), 'write only inside step4'
im = cv2.imread(SP + f'cufp/22-{N}.jpg'); sc = im[y0:y1, x0:x1]; ink = cv2.cvtColor(sc, cv2.COLOR_BGR2LAB)[..., 0] < 140
CC = {1: (0, 0, 0), 2: (255, 0, 255), 3: (203, 150, 255), 4: (255, 100, 0), 5: (0, 140, 255)}
BC = {1: (0, 150, 0), 2: (255, 140, 0), 3: (20, 70, 120), 4: (0, 0, 230), 5: (0, 150, 255), 6: (160, 0, 0), 7: (160, 170, 0), 8: (255, 0, 255), 9: (120, 120, 120)}
pics = [sc]; print(f'plate {N} window {x0},{y0},{x1},{y1}: ink {int(ink.sum())} px')
for S in ('f3', 'f4'):
    tc = cv2.imread(ST + f'masks/{S}/{N}_text.png', cv2.IMREAD_UNCHANGED)[y0:y1, x0:x1]; v = np.full_like(sc, 255)
    for k, c in CC.items(): v[tc == k] = c
    pics.append(v); t = np.isin(tc, (2, 3))
    print(f'  {S} mask: text {int(t.sum())} px; ink called text {(t & ink).sum() / max(1, ink.sum()):.3f}; codes ' + ' '.join(f'{k}:{int((tc == k).sum())}' for k in range(6)))
if run:
    for S in ('f3', 'f4'):
        b = cv2.imread(ST + f'runs/bins/{S}/{run}.png', 0)[y0:y1, x0:x1]; v = (sc * 0.4 + 150).astype(np.uint8)
        for k, c in BC.items(): v[b == k] = c
        pics.append(v); print(f'  {S} bins {run}: ' + ' '.join(f'{k}:{int((b == k).sum())}' for k in range(10)))
z = np.hstack([cv2.copyMakeBorder(p, 2, 2, 2, 2, cv2.BORDER_CONSTANT, value=(0, 200, 0)) for p in pics])
z = cv2.resize(z, None, fx=zoom, fy=zoom, interpolation=cv2.INTER_NEAREST); os.makedirs(os.path.dirname(out), exist_ok=True); cv2.imwrite(out, z); print('  wrote', out, z.shape)
