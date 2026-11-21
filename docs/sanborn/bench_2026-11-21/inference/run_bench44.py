"""Score map variants of plate 44 end to end with the bench44 harness (a copy in bench/, so runs/ land in this folder).

    python run_bench44.py [VARIANT ...] [--jobs 3] [--reuse] [--maps-root maps] [--out summary44.json]

For every maps/V/ (44_area.png, 44_lines.png) it runs
    python bench/bench44_copy.py --area maps/V/44_area.png --lines maps/V/44_lines.png --tag V
(the outline step is the batch's, outlines_copy.py under the networks' venv, as the batch runs it; then step 4 of
blocks_noguide.py and the editor's clean() + sheet()), and gathers the headline, fold and closure numbers into
summary44.json. bench44_copy.py is an unchanged copy of bench44/bench44.py; outlines_copy.py of bench44/outlines_copy.py.
"""
import json, os, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/') + '/'
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
args = sys.argv[1:]
def opt(k, d):
    return args[args.index(k) + 1] if k in args else d
JOBS = int(opt('--jobs', 3)); ROOT = opt('--maps-root', 'maps'); OUT = opt('--out', 'summary44.json')
skip = {opt('--jobs', None), opt('--maps-root', None), opt('--out', None)}
names = [a for a in args if not a.startswith('--') and a not in skip] or sorted(d for d in os.listdir(HERE + ROOT) if os.path.exists(HERE + f'{ROOT}/{d}/44_lines.png'))
names = [n for n in names if n != 'repro']


def one(n):
    t0 = time.time(); cmd = [sys.executable, HERE + 'bench/bench44_copy.py', '--area', HERE + f'{ROOT}/{n}/44_area.png', '--lines', HERE + f'{ROOT}/{n}/44_lines.png', '--tag', n]
    if '--reuse' in args: cmd.append('--reuse')
    r = subprocess.run(cmd, cwd=SP, capture_output=True, text=True, encoding='utf8', errors='replace')
    if r.returncode: print('FAILED', n, r.stderr[-1500:], flush=True); return n, None
    print('done', n, round(time.time() - t0), 's', flush=True)
    return n, json.load(open(HERE + f'bench/runs/{n}/bench44.json'))


def pick(b):
    h = b['headline']; c = b['closure']
    out = {f: {k: h[f][k] for k in ('PQ', 'SQ', 'RQ', 'matched', 'merges', 'fp', 'PQ_decided', 'recall_interior', 'precision', 'precision_green', 'precision_orange', 'ben_blocks_closed', 'intact_rings', 'delete_len', 'draw_len') if k in h[f]} for f in ('all', 'A', 'B')}
    out['closed_snap40_shown'] = c['faces']['4_editor_shows_snap40']['closure']['all']['ben_blocks_closed_iou80']
    out['closed_snap10_whatif_all_sides'] = c['faces']['whatif_all_outline_sides_kept_snap10']['closure']['all']['ben_blocks_closed_iou80']
    out['stage1_watershed'] = {k: b['stages']['1_watershed_regions']['blocks']['all'][k] for k in ('PQ', 'matched', 'merges', 'fp')} if '1_watershed_regions' in b['stages'] else None
    out['stage0_area_alone_PQ'] = b['stages']['0_area_map_alone']['blocks']['all']['PQ']
    out['recall_8px'] = b['lines_shown']['all']['tol_sensitivity']['8px']
    out['outline_step_seconds'] = b['meta'].get('outline_step_seconds')
    return out


if __name__ == '__main__':
    with ThreadPoolExecutor(JOBS) as ex: res = dict(ex.map(one, names))
    prev = json.load(open(HERE + OUT)) if os.path.exists(HERE + OUT) else {}
    for n, b in res.items():
        if b is not None: prev[n] = pick(b)
    json.dump(prev, open(HERE + OUT, 'w'), indent=1)
    print('%-22s %6s %6s %6s %4s %4s %3s %6s %6s %6s | A: %6s B: %6s' % ('variant', 'PQ', 'PQdec', 'RQ', 'tp', 'mrg', 'fp', 'rec', 'prec', 'pgrn', 'PQ', 'PQ'))
    for n in sorted(prev):
        s = prev[n]; a = s['all']
        print('%-22s %6.4f %6.4f %6.4f %4d %4d %3d %6.4f %6.4f %6.4f | A: %6.4f B: %6.4f | closed40 %d' % (n, a['PQ'], a['PQ_decided'], a['RQ'], a['matched'], a['merges'], a['fp'], a['recall_interior'], a['precision'], a['precision_green'] or 0, s['A']['PQ'], s['B']['PQ'], s['closed_snap40_shown']))
