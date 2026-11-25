"""How the maps of each pair on plate 44 sit against the outline step's fixed thresholds (127 for block and for the
line cut, 90 for the slide and the 'detected line' test), and the outline step's own counts. Reads only:
train_v2_runs/eval/<STEP>/maps44/gridK/44_area.png, 44_lines.png, runs44/v2__gridK/{44_outlines.json, outlines.json}
(the baseline's runs are bench_2026-11-23/.../runs_baseline44/base__gridK), streetmap/22-44.json (Ben's lines).
Writes map_calibration44.json beside this file. System python."""
import json, os, sys, numpy as np, cv2
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
EV = SP + 'train_v2_runs/eval/'; OUT = SP + 'bench_2026-11-25/diag/recipe/'
BASE_RUNS = SP + 'bench_2026-11-23/train/integrate/round2/driver_mini/eval/runs_baseline44/'
STEPS = ['baseline', 'V1S1', 'V2S1', 'V1S2', 'V2S2']
T = json.load(open(SP + 'streetmap/22-44.json', encoding='utf8')); H0, W0 = None, None
full_alpha = None
def ben_points(kinds, step=4.0):
    pts = []
    for l in T['lines']:
        if l['kind'] not in kinds: continue
        a, b = np.array(l['a'], float), np.array(l['b'], float); L = np.hypot(*(b - a)); n = max(2, int(L / step))
        t = np.linspace(0.05, 0.95, n); pts.append(a + np.outer(t, b - a))
    return np.vstack(pts)
P_IN = ben_points(('printed', 'drawn')); P_EDGE = ben_points(('sheet_edge',))
res = {}
for s in STEPS:
    per = []
    for g in range(6):
        md = EV + f'{s}/maps44/grid{g}/'
        pa = cv2.imread(md + '44_area.png', 0); pl = cv2.imread(md + '44_lines.png', 0)
        H, W = pl.shape
        if full_alpha is None:
            full_alpha = cv2.resize(np.load(SP + 'cufp/44/png_alpha_s4.npy').astype(np.float32), (W, H)) > 0.5
            half_alpha = cv2.resize(full_alpha.astype(np.uint8), (pa.shape[1], pa.shape[0]), interpolation=cv2.INTER_NEAREST) > 0
            # Ben's lines (printed + drawn) as a mask, for 'far from any of Ben's lines'
            benm = np.zeros((H, W), np.uint8)
            for l in T['lines']:
                cv2.line(benm, tuple(np.round(l['a']).astype(int)), tuple(np.round(l['b']).astype(int)), 1, 3)
            far = (cv2.dilate(benm, np.ones((25, 25), np.uint8)) == 0) & full_alpha
        a = pa[half_alpha]
        mx = cv2.dilate(pl, np.ones((7, 7), np.uint8))    # max within 3 px
        def samp(P):
            x = np.clip(P[:, 0].round().astype(int), 0, W - 1); y = np.clip(P[:, 1].round().astype(int), 0, H - 1); return mx[y, x]
        vi, ve = samp(P_IN), samp(P_EDGE)
        lp = cv2.GaussianBlur(pl, (5, 5), 0)          # as outlines.py's lp
        vlp = lp[np.clip(P_IN[:, 1].round().astype(int), 0, H - 1), np.clip(P_IN[:, 0].round().astype(int), 0, W - 1)]
        drawn = pl > 127
        r = dict(grid=g,
                 area_block_share_paper=round(float((a > 127).mean()), 4),
                 area_unsure_share_paper=round(float(((a >= 13) & (a <= 242)).mean()), 4),
                 area_mid_share_paper=round(float(((a >= 64) & (a <= 191)).mean()), 4),
                 lines_drawn_share_paper=round(float(drawn[full_alpha].mean()), 5),
                 lines_90_127_share_paper=round(float(((pl > 90) & (pl <= 127))[full_alpha].mean()), 5),
                 ben_printed_drawn_max3px_gt127=round(float((vi > 127).mean()), 4),
                 ben_printed_drawn_max3px_gt90=round(float((vi > 90).mean()), 4),
                 ben_printed_drawn_max3px_le20=round(float((vi <= 20).mean()), 4),
                 ben_printed_drawn_blur_on_line_mean=round(float(vlp.mean()), 1),
                 ben_sheet_edge_max3px_gt127=round(float((ve > 127).mean()), 4),
                 drawn_far_from_ben_share=round(float((drawn & far).sum() / max(1, drawn[full_alpha].sum())), 4))
        rd = (BASE_RUNS + f'base__grid{g}/') if s == 'baseline' else (EV + f'{s}/runs44/v2__grid{g}/')
        rep = json.load(open(rd + '44_outlines.json', encoding='utf8')); polys = json.load(open(rd + 'outlines.json', encoding='utf8'))
        st = {}
        for poly in polys:
            for sd in poly:
                k = sd['state'] + (' (paper edge)' if sd.get('paper_edge') else '')
                L = float(np.hypot(*(np.array(sd['b']) - np.array(sd['a']))))
                st.setdefault(k, [0, 0.0]); st[k][0] += 1; st[k][1] += L
        r.update(blocks=rep['blocks'], holes=rep.get('holes'), sides=rep['sides'], bridges=rep.get('bridges'), short_pieces=rep.get('short_pieces'), on_rail=rep.get('on_rail'),
                 share_on_detected_line_by_length=rep.get('share_on_detected_line_by_length'), share_on_printed_line_by_length=rep.get('share_on_printed_line_by_length'),
                 editor_len_px=rep['qa']['editor_len_px'], line_skel_len_px=rep['qa']['line_skel_len_px'], editor_per_line=rep['qa']['editor_per_line'],
                 states={k: [v[0], round(v[1])] for k, v in sorted(st.items())})
        b = json.load(open(rd + 'bench44.json', encoding='utf8'))['headline']['all']
        r.update(PQ=b['PQ'], recall_interior=b['recall_interior'], precision=b['precision'], fp=b['fp'], merges=b['merges'], matched=b['matched'])
        per.append(r); print(s, g, {k: r[k] for k in ('PQ', 'area_block_share_paper', 'area_unsure_share_paper', 'lines_drawn_share_paper', 'ben_printed_drawn_max3px_gt127', 'ben_printed_drawn_max3px_gt90', 'drawn_far_from_ben_share', 'blocks', 'bridges')}, flush=True)
    keys = [k for k in per[0] if isinstance(per[0][k], (int, float)) and k != 'grid']
    mean = {k: round(float(np.mean([p[k] for p in per if p[k] is not None])), 4) for k in keys}
    stm = {}
    for p in per:
        for k, v in p['states'].items(): stm.setdefault(k, []).append(v)
    mean['states_mean_count_len'] = {k: [round(float(np.mean([x[0] for x in v])), 1), round(float(np.mean([x[1] for x in v])))] for k, v in stm.items()}
    res[s] = dict(mean=mean, grids=per)
json.dump(res, open(OUT + 'map_calibration44.json', 'w'), indent=1)
for s in STEPS: print(s, json.dumps(res[s]['mean']))
