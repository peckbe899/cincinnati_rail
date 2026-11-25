"""run_plate5.py (diag/verify, 25 Nov 2026): plate 5 end to end (bench_plate.py: the real merged outline step, step 4
and bench44's scores, CPU) for each map folder diag/verify/plate5/maps/<TAG>/ (5_area.png, 5_lines.png), against
diag/verify/plate5/streetmap_5.json (bench_plate --make-truth 5 from Ben's edges_ben.json; same as ben-labels'
map_now/5_streetmap.json). One tile grid only (the batch's). Writes diag/verify/plate5/runs/<TAG>/ and prints the headline.
    python -B run_plate5.py TAG [TAG ...]
"""
import json, os, subprocess, sys, time
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
TOOLS = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/tools/sanborn/unet/'
D = SP + 'bench_2026-11-25/diag/verify/plate5/'
for tag in sys.argv[1:]:
    m = D + f'maps/{tag}/'
    if os.path.exists(D + f'runs/{tag}/bench_plate.json'): print('skip', tag); continue
    t0 = time.time()
    r = subprocess.run(['python', '-B', TOOLS + 'bench_plate.py', '--plate', '5', '--truth', D + 'streetmap_5.json', '--area', m + '5_area.png', '--lines', m + '5_lines.png',
                        '--tag', tag, '--runs', D + 'runs', '--no-pic'], cwd=SP, capture_output=True, text=True, encoding='utf8', errors='replace', env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
    open(D + f'runs/{tag}.stdout.txt', 'w', encoding='utf8').write(r.stdout[-50000:] + '\n---stderr---\n' + r.stderr[-20000:])
    print(tag, 'exit', r.returncode, f'{time.time() - t0:.0f}s', r.stdout.strip().splitlines()[-1][:400] if r.stdout.strip() else r.stderr[-800:], flush=True)
