"""Health census of the 109 plates of the 21 Nov 2026 batch (run_plates.py). Read-only on the repo; writes only here.

Run order (all from this folder; PY = tools/sanborn/unet/.venv/Scripts/python.exe):
    python outlines_copy.py N area_ng1 lines_ng1 guided_ol   for N in 43 44 45 80 82A (the batch refused these)
    python census.py            -> census_raw.json
    python scale_find.py        -> scale/find.json, scale/notes_*.jpg (read by eye) ; scale_measure.py -> scale/measured.json
    python scale_table.py       -> scale/scale_table.json (the readings)
    PY census_finish.py         -> census_base.json (scale, ground area, line-net length, edge lines)
    python rail_key.py          -> rail_key.json (rule rail inside the printed KEY)
    python thumbs.py ...        -> thumbs/ ; the eye check is written into visual.json by hand
    python classify.py          -> classify.json, census.json, census.csv (failure modes, ranking, QA flag check)
    python anchor44.py          -> anchor44.json (PQ of the batch outline step on 44 against Ben's map)

    python census.py            -> census_raw.json (one record per plate; scale columns are added by census_finish.py)

Everything is computed from the batch's own outputs in data/sanborn/unet_data and picks22_guided/22-N/outlines.json:
  paper           cufp/N/png_alpha_s4.npy (quarter size)
  area net        N_pred_area_ng1.png  half size, P(block)*255
  line net        N_lines_lines_ng1.png full size, P(line)*255
  outline step    N_blockmask.png (half size, the block ground after the watershed, opening and MIN_AREA),
                  picks22_guided/22-N/outlines.json (every side, with state and paper_edge), N_outlines.json (counts)
  editor          N_edges.json (what the line editor shows), N_blocks_ng.json
  rail            N_bins.json (railroad / streetcar px), N_rail_rule.json (tracks)
  batch           run_plates.json (seconds, state), run_plates.log (the 21 Nov section of each plate)
For the five placed plates (43, 44, 45, 80, 82A) the batch wrote the two network maps but refused the outline step.
Their outline columns come from census/guided_ol/, where outlines_copy.py (outlines.py, outputs redirected) was run on
the batch's own ng1 maps, and step 4 of blocks_noguide.py is replayed here; they are marked outline_source='census copy'.
Definitions follow the 21 Nov review (critic c2, c8, c9, c12) so numbers are comparable:
  tinted_share    HSV saturation > 60 at 1/8 size, paper eroded 9 px (research-training b_colour.py)
  hole_share      length of hole contours (area >= MIN_AREA) / (hole + outer contour length), RETR_CCOMP (c9)
  nested_dropped  outer block contours at even depth > 0 in RETR_TREE: blocks inside a hole, dropped by RETR_EXTERNAL (c12)
"""
import json, os, re, sys, time
import numpy as np, cv2

HERE = os.path.dirname(os.path.abspath(__file__))
D = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; U = D + 'unet_data/'
GUIDED = {'43', '44', '45', '80', '82A'}; MIN_AREA = 6000


def order(n): m = re.match(r'(\d+)(.*)', n); return int(m.group(1)), m.group(2)


def log_sections():
    """the 21 Nov section of run_plates.log per plate (ink_bins, rail_tracks and blocks_noguide output)"""
    txt = open(U + 'run_plates.log', encoding='utf8', errors='replace').read().replace('\x00', '')
    parts = re.split(r'^===== plate (\S+) (\S+) (\S+) rules (\S+) exit (\d+)$', txt, flags=re.M)
    out = {}
    for k in range(1, len(parts), 6):
        n, day, tm, rules, ex, body = parts[k:k + 6]
        if day == '2026-11-21': out[n] = dict(exit=int(ex), body=body)
    return out


def contour_stats(b, m_edge):
    """b: half-size block mask (uint8 0/1). Regions found, nested dropped, holes, largest region"""
    k, cc, st, _ = cv2.connectedComponentsWithStats(b, connectivity=4)
    areas = st[1:, cv2.CC_STAT_AREA] if k > 1 else np.array([0])
    big = int(np.argmax(areas)) + 1 if k > 1 else 0
    lab_big = (cc == big) if k > 1 else np.zeros(b.shape, bool)
    ext = cv2.findContours(b, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)[0]
    allc, hier = cv2.findContours(b, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)
    r = dict(regions_cc=int(k - 1), largest_px=int(areas.max()), exported_contours=len(ext))
    if hier is None:
        r.update(blocks_found=0, nested_dropped=0, nested_len=0, nested_area_px=0, holes=0, hole_len=0, ext_len=0, hole_share=0.0, hole_area_px=0); return r, lab_big
    hier = hier[0]
    dep = np.zeros(len(allc), int)
    for i in range(len(allc)):
        j, d = i, 0
        while hier[j][3] >= 0: j = hier[j][3]; d += 1
        dep[i] = d
    outer = [i for i in range(len(allc)) if dep[i] % 2 == 0]; nested = [i for i in outer if dep[i] > 0]
    r.update(blocks_found=len(outer), nested_dropped=len(nested), nested_len=round(sum(cv2.arcLength(allc[i], True) * 2 for i in nested)),
             nested_area_px=round(sum(cv2.contourArea(allc[i]) for i in nested) * 4))
    cs, h2 = cv2.findContours(b, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    h2 = h2[0]; e = hol = harea = 0.0; nh = 0
    for c, h in zip(cs, h2):
        L = cv2.arcLength(c, True) * 2
        if h[3] < 0: e += L
        elif cv2.contourArea(c) * 4 >= MIN_AREA: hol += L; nh += 1; harea += cv2.contourArea(c) * 4
    r.update(holes=nh, hole_len=round(hol), ext_len=round(e), hole_share=round(hol / max(1.0, hol + e), 3), hole_area_px=round(harea))
    return r, lab_big


def plate(n, logs, state):
    t0 = time.time(); r = dict(plate=n)
    src = D + f'cufp/{n}/source.json'
    r['source'] = 'pdf sheet' if os.path.exists(src) else 'cut plate'
    full8 = cv2.imread(D + f'cufp/22-{n}.jpg', cv2.IMREAD_REDUCED_COLOR_8)
    al = np.load(D + f'cufp/{n}/png_alpha_s4.npy').astype(np.uint8)
    pa = cv2.imread(U + f'{n}_pred_area_ng1.png', 0); Hh, Wh = pa.shape
    r['W'], r['H'] = int(Wh * 2), int(Hh * 2)
    pl = cv2.imread(U + f'{n}_lines_lines_ng1.png', 0); r['W'], r['H'] = int(pl.shape[1]), int(pl.shape[0])
    r['paper_share'] = round(float(al.mean()), 3); r['paper_mpx'] = round(float(al.sum()) * 16 / 1e6, 2)
    # tint, as research-training b_colour.py
    h8, w8 = full8.shape[:2]; a8 = cv2.erode((cv2.resize(al.astype(np.float32), (w8, h8)) > 0.5).astype(np.uint8), np.ones((9, 9), np.uint8)) > 0
    sat = cv2.cvtColor(full8, cv2.COLOR_BGR2HSV)[..., 1][a8]; r['tinted_share'] = round(float((sat > 60).mean()), 3)
    # area net
    mh = cv2.resize(al, (Wh, Hh), interpolation=cv2.INTER_NEAREST) > 0; p = pa[mh].astype(np.float32) / 255
    r['area_block_share'] = round(float((p > 0.5).mean()), 3); r['area_unsure_share'] = round(float(((p > 0.1) & (p < 0.9)).mean()), 3)
    # line net (full size, on the paper)
    mf = cv2.resize(al, (pl.shape[1], pl.shape[0]), interpolation=cv2.INTER_NEAREST) > 0
    r['line_net_share'] = round(float((pl[mf] > 127).mean()), 4)
    # outline step
    if n in GUIDED:
        r['outline_source'] = 'census copy (batch refused: plate has a guide)'
        bm = cv2.imread(HERE + f'/guided_ol/{n}_blockmask.png', 0); polys = json.load(open(HERE + f'/guided_ol/{n}_outlines_poly.json', encoding='utf8'))
        rep = json.load(open(HERE + f'/guided_ol/{n}_outlines.json', encoding='utf8'))
        edges = [dict(a=s['a'], b=s['b'], state='green' if s['state'] == 'on print' else 'orange') for poly in polys for s in poly if not (s['state'] == 'short' or s.get('paper_edge'))]
    else:
        r['outline_source'] = 'batch'
        bm = cv2.imread(U + f'{n}_blockmask.png', 0); polys = json.load(open(D + f'picks22_guided/22-{n}/outlines.json', encoding='utf8'))
        rep = json.load(open(U + f'{n}_outlines.json', encoding='utf8')); edges = json.load(open(U + f'{n}_edges.json', encoding='utf8'))
    b = (bm > 0).astype(np.uint8)
    mb = cv2.resize(al, (b.shape[1], b.shape[0]), interpolation=cv2.INTER_NEAREST) > 0
    edge = mb & ~(cv2.erode(mb.astype(np.uint8), np.ones((121, 121), np.uint8)) > 0)
    cst, lab_big = contour_stats(b, edge)
    paper_h = float(mb.sum())
    r['blockmask_share'] = round(float(b[mb].mean()), 3)
    r['regions_found'] = cst['blocks_found']; r['regions_cc'] = cst['regions_cc']
    r['largest_share'] = round(cst['largest_px'] / paper_h, 3)
    r['largest_on_edge_band'] = round(float(lab_big[edge].mean()), 3) if edge.any() else 0.0
    r['nested_dropped'] = cst['nested_dropped']; r['nested_len'] = cst['nested_len']; r['nested_area_share'] = round(cst['nested_area_px'] / 4 / paper_h, 4)
    r['holes'] = cst['holes']; r['hole_share'] = cst['hole_share']; r['hole_len'] = cst['hole_len']; r['ext_len'] = cst['ext_len']; r['hole_area_share'] = round(cst['hole_area_px'] / 4 / paper_h, 3)
    r['blocks_exported'] = len(polys)
    r['outer_contours'] = cst['exported_contours']                       # what RETR_EXTERNAL hands to straighten()
    r['dropped_by_straighten'] = cst['exported_contours'] - len(polys)  # outer regions with no fitted 'line' side or < 3 sides
    sides = [s for poly in polys for s in poly]
    r['sides_all'] = len(sides); r['sides_short'] = sum(s['state'] == 'short' for s in sides)
    r['sides_paper_edge'] = sum(bool(s.get('paper_edge')) and s['state'] != 'short' for s in sides)
    r['editor_lines'] = len(edges); g = sum(e['state'] == 'green' for e in edges); r['editor_green'] = g
    r['green_share'] = round(g / len(edges), 3) if edges else None
    L = lambda e: float(np.hypot(e['b'][0] - e['a'][0], e['b'][1] - e['a'][1]))
    r['editor_len_px'] = round(sum(L(e) for e in edges)); r['editor_green_len_px'] = round(sum(L(e) for e in edges if e['state'] == 'green'))
    r['on_print_share_len'] = rep.get('share_on_printed_line_by_length'); r['on_detected_share_len'] = rep.get('share_on_detected_line_by_length')
    r['short_pieces'] = rep.get('short_pieces')
    # editor lines per ground: per paper Mpx (scale applied later)
    r['editor_lines_per_mpx'] = round(len(edges) / max(0.01, r['paper_mpx']), 2)
    # rail
    bj = json.load(open(U + f'{n}_bins.json', encoding='utf8')); px = {v['name']: v['px'] for v in bj['bins'].values()}
    r['ink_px'] = bj['ink_px']; r['railroad_px'] = px.get('railroad', 0); r['streetcar_px'] = px.get('streetcar', 0)
    r['railroad_ink_share'] = round(r['railroad_px'] / max(1, r['ink_px']), 4); r['streetcar_ink_share'] = round(r['streetcar_px'] / max(1, r['ink_px']), 4)
    r['ben_rail'] = bool(bj.get('ben_rail'))
    rr = json.load(open(U + f'{n}_rail_rule.json', encoding='utf8'))['tracks']
    tl = lambda t: float(sum(np.hypot(*np.diff(np.array(t['pts'], float), axis=0).T))) if len(t['pts']) > 1 else 0.0
    for kind in ('railroad', 'streetcar'):
        ts = [t for t in rr if t.get('kind') == kind]; r[f'{kind}_tracks'] = len(ts); r[f'{kind}_track_len_px'] = round(sum(tl(t) for t in ts))
    # batch record and log
    s = state.get(n, {}); r['batch_state'] = s.get('state'); r['seconds'] = s.get('seconds'); r['batch_blocks_msg'] = s.get('blocks', '')
    lg = logs.get(n); issues = []
    if lg is None: issues.append('no 21 Nov log section')
    else:
        if lg['exit']: issues.append(f'ink_bins exit {lg["exit"]}')
        for pat in ('Traceback', 'FAILED', 'Error', 'Warning', 'warning', 'nan', 'refused'):
            if pat in lg['body']: issues.append(f"log mentions '{pat}'")
        if 'blocks' not in lg['body'] and 'block share' not in lg['body']: issues.append('no block step line')
    if s.get('error'): issues.append('run error: ' + s['error'])
    r['log_issues'] = '; '.join(issues)
    r['census_seconds'] = round(time.time() - t0, 1)
    return r


if __name__ == '__main__':
    state = json.load(open(U + 'run_plates.json', encoding='utf8')); logs = log_sections()
    want = sys.argv[1:] or sorted(state, key=order)
    out = json.load(open(HERE + '/census_raw.json')) if (sys.argv[1:] and os.path.exists(HERE + '/census_raw.json')) else {}
    for n in want:
        out[n] = plate(n, logs, state)
        r = out[n]; print(f"{n:4s} {r['source'][:3]} tint {r['tinted_share']:.2f} blk {r['area_block_share']:.2f} uns {r['area_unsure_share']:.2f} largest {r['largest_share']:.2f} found {r['regions_found']:3d} exp {r['blocks_exported']:3d} nested {r['nested_dropped']:2d} hole {r['hole_share']:.2f} ed {r['editor_lines']:4d} green {r['green_share']} {r['log_issues']} | {r['census_seconds']} s", flush=True)
    json.dump(out, open(HERE + '/census_raw.json', 'w'), indent=1)
