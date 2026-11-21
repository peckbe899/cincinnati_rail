"""Network maps of plate 44 under test-time options (GPU, DirectML; no training).

    VENV_PYTHON make_maps44.py [VARIANT ...] [--cpu] [--force]      (no VARIANT: all of VARIANTS)

Each variant is an area option set and a line option set (infer_lib.area_map / lines_map). The line network's 7th
input is the variant's own area map (as blocks_noguide.py feeds it), unless the line spec says 'stored_area'.
Writes maps/V/44_area.png (half size, P(block)*255) and maps/V/44_lines.png (full size, P(line)*255), and
maps/V/info.json (options, seconds). Only inside this folder.

Plate 44 is at 100 ft to the inch (census scale table, measured 101.1 ft/in); the 200-ft training scale is s = 0.5.
"""
import json, os, sys, time
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, cv2, torch
import infer_lib as L

A0 = dict()                                   # the batch: crop tiles, one pass, native scale
VARIANTS = {
    # name: (area options, line options, extra)
    'batch':            (A0, {}, {}),
    'a_tta4':           (dict(tta=4), {}, {}),
    'a_tta8':           (dict(tta=8), {}, {}),
    'a_hann':           (dict(blend='hann'), {}, {}),
    'a_hann_tta8':      (dict(blend='hann', tta=8), {}, {}),
    'l_tta8':           (A0, dict(tta=8), {}),
    'l_hann':           (A0, dict(blend='hann'), {}),
    'l_hann_tta8':      (A0, dict(blend='hann', tta=8), {}),
    'a_tta8_l_tta8':    (dict(tta=8), dict(tta=8), {}),
    'both_hann_tta8':   (dict(blend='hann', tta=8), dict(blend='hann', tta=8), {}),
    # the area map changed, but the line map left as the batch made it: isolates the outline-step seeds
    'a_hann_tta8_lstored': (dict(blend='hann', tta=8), 'stored', {}),
    # scale normalisation: 44 is a 100-ft plate, s = 0.5 brings it to the 200-ft training scale
    'a_s0.5':           (dict(scale=0.5), {}, {}),
    'l_s0.5':           (A0, dict(scale=0.5), {}),
    'both_s0.5':        (dict(scale=0.5), dict(scale=0.5), {}),
    'a_s0.71':          (dict(scale=0.71), {}, {}),
    'a_ms_1+0.5':       ('multiscale', {}, dict(scales=(1.0, 0.5))),
    'a_s0.5_hann_tta8': (dict(scale=0.5, blend='hann', tta=8), {}, {}),
    # the other way: the area network at a LARGER scale than the plate's own (does it see narrow alleys better?)
    'a_s1.41':          (dict(scale=1.41), {}, {}),
    'a_s2':             (dict(scale=2.0), {}, {}),
    'a_s2_tta4':        (dict(scale=2.0, tta=4), {}, {}),
    'a_ms_1+2_tta4':    ('multiscale', {}, dict(scales=(1.0, 2.0), tta=4)),
    'a_tta4_l_s0.5':    (dict(tta=4), dict(scale=0.5), {}),
    'a_tta8_l_s0.5':    (dict(tta=8), dict(scale=0.5), {}),
}
# noise floor: the same settings with the tile grids of both networks moved (area offsets in half-size px, line offsets
# in full-size px; the repo's steps are 640 and 832 px). Any of these grids is as valid as the batch's.
OFFS = [((160, 400), (300, 700)), ((320, 160), (640, 200)), ((480, 560), (100, 450)), ((240, 0), (520, 0)), ((0, 240), (0, 520))]
for i, (oa, ol) in enumerate(OFFS, 1):
    VARIANTS[f'off{i}_tta1'] = (dict(offset=oa), dict(offset=ol), {})
    VARIANTS[f'off{i}_a_tta4'] = (dict(offset=oa, tta=4), dict(offset=ol), {})
    VARIANTS[f'off{i}_a_tta8'] = (dict(offset=oa, tta=8), dict(offset=ol), {})
    VARIANTS[f'off{i}_a_hann'] = (dict(offset=oa, blend='hann'), dict(offset=ol), {})


# grid ensembles: the area map averaged over the 6 tile grids above (the batch's and off1..off5), lines re-run on it
VARIANTS['a_tta1_grid6'] = ('grid', {}, dict(members=['batch'] + [f'off{i}_tta1' for i in range(1, 6)]))
VARIANTS['a_tta8_grid6'] = ('grid', {}, dict(members=['a_tta8'] + [f'off{i}_a_tta8' for i in range(1, 6)]))


# thicker pen at the plate's own scale (a 3x3 or 5x5 minimum filter widens every dark line by 2 or 4 px): separates the
# pen width from the street width, which resampling changes together. A 400-ft plate resampled x2 has 200-ft streets
# but pen lines twice as wide as any training plate.
VARIANTS['pen_min3'] = (A0, {}, dict(erode=3))
VARIANTS['pen_min5'] = (A0, {}, dict(erode=5))
VARIANTS['pen_min3_a_tta8'] = (dict(tta=8), {}, dict(erode=3))
VARIANTS['pen_max3'] = (dict(pen=3), dict(pen=3), {})          # thinner pen at the plate's own scale (the other direction)
VARIANTS['pen_max2'] = (dict(pen=2), dict(pen=2), {})


def make(nets, full, name, force=False):
    out = L.HERE + f'maps/{name}/'
    if os.path.exists(out + 'info.json') and not force: print('have', name, file=sys.stderr); return json.load(open(out + 'info.json'))
    os.makedirs(out, exist_ok=True); ao, lo, ex = VARIANTS[name]; dev, na, nl = nets; t = {}
    if ex.get('erode'): full = cv2.erode(full, np.ones((ex['erode'], ex['erode']), np.uint8))
    t0 = time.time()
    if ao == 'multiscale':
        ps = [L.area_map(na, dev, full, scale=s, tta=ex.get('tta', 1)) for s in ex['scales']]; pa = L.u8(np.mean(ps, 0))
    elif ao == 'grid':
        pa = L.u8(np.mean([cv2.imread(L.HERE + f'maps/{m}/44_area.png', 0).astype(np.float32) / 255.0 for m in ex['members']], 0))
    else: pa = L.u8(L.area_map(na, dev, full, **ao))
    t['area_s'] = round(time.time() - t0, 2); t1 = time.time()
    if lo == 'stored': pl = cv2.imread(L.U + '44_lines_lines_ng1.png', 0)
    else: pl = L.u8(L.lines_map(nl, dev, full, pa, **lo))
    t['lines_s'] = round(time.time() - t1, 2)
    cv2.imwrite(out + '44_area.png', pa); cv2.imwrite(out + '44_lines.png', pl)
    st = cv2.imread(L.U + '44_pred_area_ng1.png', 0); sl = cv2.imread(L.U + '44_lines_lines_ng1.png', 0)
    info = dict(name=name, area=ao if isinstance(ao, dict) else {ao: ex}, lines=lo, device=str(dev), seconds=t,
                area_block_share=round(float((pa > 127).mean()), 4), line_share=round(float((pl > 127).mean()), 5),
                area_decision_differs_from_batch=round(float(((pa > 127) != (st > 127)).mean()), 5),
                lines_decision_differs_from_batch=round(float(((pl > 127) != (sl > 127)).mean()), 6))
    json.dump(info, open(out + 'info.json', 'w'), indent=1); print(json.dumps(info), flush=True)
    return info


if __name__ == '__main__':
    names = [a for a in sys.argv[1:] if not a.startswith('--')] or list(VARIANTS)
    dev = torch.device('cpu') if '--cpu' in sys.argv else L.device()
    nets = L.load_nets(dev); full = cv2.imread(L.SP + 'cufp/22-44.jpg')
    for n in names: make(nets, full, n, '--force' in sys.argv)
