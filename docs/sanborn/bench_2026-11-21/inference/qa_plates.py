"""Truth-free QA indicators of a batch plate's network maps under an inference setting, through the outline step.

    VENV_PYTHON qa_plates.py SETTING N [N ...] [--jobs 3]       (venv: its OpenCV has ximgproc.thinning)

SETTING 'batch' = the batch's own maps (unet_data/N_pred_area_ng1.png, N_lines_lines_ng1.png); otherwise
maps_plates/SETTING/N_area.png, N_lines.png (make_maps_plates.py).
Outline step: outlines_ccomp_mask_paths.py (visual-pdf's redirected copy of outlines.py, maps given as paths):
  - uncut PDF sheets (cufp/N/source.json): --ccomp --mask visual-pdf/maparea_check/N_mask8.png, so the margin ring
    and RETR_EXTERNAL do not hide what the networks found (visual-pdf finding pdf-1);
  - cut plates: no switches, which is the batch's own outline step (visual-pdf checked it reproduces the batch).
Indicators (map ground = the paper, and on PDF sheets map_area.py's map ground; half-size rasters):
  block_share, line_share     P > 0.5 share of the map ground
  line_skel_len_px            P(line) > 0.5 (> 110 at half size, as census_finish.py), thinned, x2
  regions                     area-network block regions in the map ground, nested ones included (RETR_TREE, even
                              depth), at least outlines.py's MIN_AREA (6000 full px); largest_region_share
  blocks, holes, exported_sides, exported_green, short_pieces   from the outline step
  editor_len_px               length of the exported sides (N_edges.json); editor_per_line = editor_len / line_skel_len
Writes qa/SETTING/N/ (outline outputs) and qa/SETTING/summary.json. Only inside this folder.
"""
import json, os, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
sys.dont_write_bytecode = True
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/') + '/'
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; U = SP + 'unet_data/'
VPDF = SP + 'bench_2026-11-21/visual-pdf/'
SYS_PY = 'C:/Users/peckb/AppData/Local/Programs/Python/Python312/python.exe'
MIN_AREA = 6000


def maps(setting, n):
    if setting == 'batch': return U + f'{n}_pred_area_ng1.png', U + f'{n}_lines_lines_ng1.png'
    return HERE + f'maps_plates/{setting}/{n}_area.png', HERE + f'maps_plates/{setting}/{n}_lines.png'


def regions(b, min_area_px):
    cs, hier = cv2.findContours(b.astype(np.uint8), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    if hier is None: return []
    hier = hier[0]
    def depth(i):
        d = 0
        while hier[i][3] >= 0: i = hier[i][3]; d += 1
        return d
    area = np.array([cv2.contourArea(c) for c in cs]); net = area.copy()
    for j in range(len(cs)):
        if hier[j][3] >= 0: net[hier[j][3]] -= area[j]          # a region's own ground: its outer contour less its holes
    return [float(net[i]) for i in range(len(cs)) if depth(i) % 2 == 0 and net[i] >= min_area_px]


def one(setting, n):
    t0 = time.time(); am, lm = maps(setting, n); od = HERE + f'qa/{setting}/{n}/'; os.makedirs(od, exist_ok=True)
    pdf = os.path.exists(SP + f'cufp/{n}/source.json')
    args = [SYS_PY, HERE + 'outlines_ccomp_mask_paths.py', n, am, lm, od]
    if pdf: args += ['--ccomp', '--mask', VPDF + f'maparea_check/{n}_mask8.png']
    r = subprocess.run(args, cwd=SP, capture_output=True, text=True, encoding='utf8', errors='replace')
    if r.returncode: return n, dict(error=(r.stderr.strip().splitlines() or ['?'])[-1])
    rep = json.loads(r.stdout.strip().splitlines()[-1])
    pa = cv2.imread(am, 0); pl = cv2.imread(lm, 0); H, W = pl.shape; h2, w2 = H // 2, W // 2
    pa = cv2.resize(pa, (w2, h2), interpolation=cv2.INTER_LINEAR) if pa.shape != (h2, w2) else pa
    half = cv2.resize(pl, (w2, h2), interpolation=cv2.INTER_AREA)
    ground = cv2.resize(np.load(SP + f'cufp/{n}/png_alpha_s4.npy').astype(np.uint8), (w2, h2), interpolation=cv2.INTER_NEAREST) > 0
    if pdf: ground &= cv2.resize(cv2.imread(VPDF + f'maparea_check/{n}_mask8.png', 0), (w2, h2), interpolation=cv2.INTER_NEAREST) > 127
    inner = cv2.erode(ground.astype(np.uint8), np.ones((15, 15), np.uint8)) > 0
    sk = cv2.ximgproc.thinning(((half > 110) & inner).astype(np.uint8) * 255) > 0
    blk = (pa > 127) & ground; rg = regions(blk, MIN_AREA / 4.0); g = max(1, int(ground.sum()))
    ed = json.load(open(od + f'{n}_edges.json', encoding='utf8'))
    elen = sum(float(np.hypot(e['b'][0] - e['a'][0], e['b'][1] - e['a'][1])) for e in ed)
    out = dict(plate=n, setting=setting, pdf=pdf, ground_share_of_image=round(g / (h2 * w2), 3),
               block_share=round(float(blk.sum() / g), 4), line_share=round(float(((half > 127) & ground).sum() / g), 5), line_skel_len_px=int(sk.sum()) * 2,
               regions=len(rg), largest_region_share=round(max(rg) / g, 3) if rg else 0.0,
               blocks=rep['blocks'], holes=rep.get('holes', 0), exported_sides=rep.get('exported_sides'), exported_green=rep.get('exported_green'), short_pieces=rep['short_pieces'],
               share_on_printed_line_by_length=rep['share_on_printed_line_by_length'], editor_len_px=round(elen),
               editor_per_line=round(elen / max(1, int(sk.sum()) * 2), 3), seconds=round(time.time() - t0, 1))
    return n, out


if __name__ == '__main__':
    a = [x for x in sys.argv[1:] if not x.startswith('--')]; setting, plates = a[0], a[1:]
    jobs = int(sys.argv[sys.argv.index('--jobs') + 1]) if '--jobs' in sys.argv else 3
    plates = [p for p in plates if p != str(jobs) or '--jobs' not in sys.argv]
    sp = HERE + f'qa/{setting}/summary.json'; os.makedirs(HERE + f'qa/{setting}', exist_ok=True)
    summ = json.load(open(sp)) if os.path.exists(sp) else {}
    with ThreadPoolExecutor(jobs) as ex:
        for n, r in ex.map(lambda n: one(setting, n), plates):
            summ[n] = r; print(json.dumps(r), flush=True); json.dump(summ, open(sp, 'w'), indent=1)
