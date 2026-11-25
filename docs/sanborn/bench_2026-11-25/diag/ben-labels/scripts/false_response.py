"""Q2b (ben-labels, 25 Nov 2026): what ink the line networks' FALSE responses lie on, and the area networks' errors near text.
    cd data/sanborn; python -B bench_2026-11-25/diag/ben-labels/scripts/false_response.py
Line maps: train_v2_runs/eval/STEP/maps44/gridG/44_lines.png (P(line) * 255; grids 0 and 3), maps1A/1A_lines.png, and the
batch's unet_data/5_lines_lines_ng1.png (baseline only; the new nets were never run on 5). Truth: Ben's final street
map lines, every kind (44 streetmap/22-44.json; 1A train_v2/1A/streetmap.json; 5 diag map_now). A FALSE pixel = P > 0.5,
on the paper, more than FAR (6) px from every one of his lines. Each false pixel takes the bin of the nearest ink pixel
(ink_bins' ink) if one lies within 4 px, else 'no ink'. Also how far the false pixels are from his lines.
Area maps (half size): errors (P > 0.5 against his map label 0/1, taught pixels only) within 3 half px of text ink vs the
same share for all taught pixels (enrichment).
Editor lines of the merged step (runs44/v2__gridG/44_edges.json): a line is FALSE when under 20% of its points lie within
8 px of one of his lines; its main bin = most of the ink in its 11 px strip.
"""
import sys, os, json
import numpy as np, cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *  # noqa
FAR = 6
NAMES = {0: 'no ink', 1: 'block line', 2: 'lot line', 3: 'building outline', 4: 'railroad', 5: 'streetcar', 6: 'water pipe', 7: 'sewer', 8: 'text and numbers', 9: 'not sorted'}
EV = SP + 'train_v2_runs/eval/'; STEPS = ['baseline', 'V1S1', 'V1S2', 'V2S1', 'V2S2']
def pts(a, b, step=2.0):
    a, b = np.asarray(a, float), np.asarray(b, float); L = np.hypot(*(b - a)); n = max(2, int(L / step) + 1)
    return a + np.linspace(0, 1, n)[:, None] * (b - a)
def plate_setup(N, smf, bf):
    full = scan(N); H, W = full.shape[:2]; del full; af = alpha_full(N, W, H)
    sm = json.load(open(smf, encoding='utf8')); fin = raster([(l['a'], l['b']) for l in sm['lines']], (H, W), 1.0, 1)
    dfin = cv2.distanceTransform((fin == 0).astype(np.uint8), cv2.DIST_L2, 5)
    bins = cv2.imread(bf, 0); ink = bins > 0
    d_, lbl = cv2.distanceTransformWithLabels((~ink).astype(np.uint8), cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
    ys, xs = np.nonzero(ink); lut = np.zeros(lbl.max() + 1, np.uint8)
    # label of each zero pixel: the labels are numbered in scan order of the zero (ink) pixels
    zl = lbl[ys, xs]; lut[zl] = bins[ys, xs]
    nearbin = np.where(d_ <= 4, lut[lbl], 0).astype(np.uint8)
    return dict(H=H, W=W, af=af, dfin=dfin, bins=bins, nearbin=nearbin, sm=sm)
def false_comp(P, p, region=None):
    m = (p > 127) & P['af'] & (P['dfin'] > FAR)
    if region is not None: m &= region
    tot = int(m.sum()); allr = (p > 127) & P['af'] & (region if region is not None else True)
    nb = P['nearbin'][m]; cnt = np.bincount(nb, minlength=10)
    dd = P['dfin'][m]
    return dict(false_px=tot, response_px=int(allr.sum()), false_share_of_response=round(tot / max(1, int(allr.sum())), 4),
                by_bin={NAMES[k]: round(float(cnt[k]) / max(1, tot), 4) for k in range(10)},
                dist_from_true={'6-20': round(float(((dd > 6) & (dd <= 20)).mean()), 4) if tot else 0, '20-40': round(float(((dd > 20) & (dd <= 40)).mean()), 4) if tot else 0, '>40': round(float((dd > 40).mean()), 4) if tot else 0})
def area_err(P, pa, lab, text_h, region=None):
    taught = lab != 255
    if region is not None: taught &= region
    err = taught & ((pa > 127) != (lab == 1)); nt = text_h & taught
    return dict(taught_px=int(taught.sum()), err_px=int(err.sum()), err_rate=round(float(err.sum() / max(1, taught.sum())), 4),
                err_near_text_share=round(float((err & text_h).sum() / max(1, err.sum())), 4), taught_near_text_share=round(float(nt.sum() / max(1, taught.sum())), 4),
                err_rate_near_text=round(float((err & text_h).sum() / max(1, nt.sum())), 4), err_rate_away=round(float((err & ~text_h).sum() / max(1, (taught & ~text_h).sum())), 4),
                false_block_in_street=int((taught & (pa > 127) & (lab == 0)).sum()), false_street_in_block=int((taught & (pa <= 127) & (lab == 1)).sum()))
def text_half(bins, h, w):
    t = (bins == 8).astype(np.uint8); th = cv2.resize(t, (w, h), interpolation=cv2.INTER_AREA) > 0
    return cv2.dilate(th.astype(np.uint8), np.ones((7, 7), np.uint8)) > 0
res = {}
# ---- 44
P = plate_setup('44', SP + 'streetmap/22-44.json', SP + 'unet_data/44_bins.png'); H, W = P['H'], P['W']; h, w = H // 2, W // 2
lab44 = cv2.imread(DIAG + '/map_now/44_label.png', 0); th44 = text_half(P['bins'], h, w)
ink_comp = np.bincount(P['bins'][P['af'] & (P['bins'] > 0)], minlength=10)
res['44'] = dict(ink_by_bin={NAMES[k]: round(float(ink_comp[k] / ink_comp[1:].sum()), 4) for k in range(1, 10)})
Lt = [(l['a'], l['b']) for l in P['sm']['lines']]
for s in STEPS:
    r = {}
    for g in ('grid0', 'grid3'):
        p = cv2.imread(EV + f'{s}/maps44/{g}/44_lines.png', 0); r['lines_' + g] = false_comp(P, p)
        pa = cv2.imread(EV + f'{s}/maps44/{g}/44_area.png', 0); r['area_' + g] = area_err(P, pa, lab44, th44)
    # editor lines of the merged step, grid0
    E = json.load(open(EV + f'{s}/runs44/v2__grid0/44_edges.json', encoding='utf8'))
    fl = []; nL = 0
    for e in E:
        q = pts(e['a'], e['b']); x = np.clip(q[:, 0].round().astype(int), 0, W - 1); y = np.clip(q[:, 1].round().astype(int), 0, H - 1)
        if (P['dfin'][y, x] <= 8).mean() < 0.2:
            m = (raster([(e['a'], e['b'])], (H, W), 1.0, WRONG_PX) > 0) & (P['bins'] > 0)
            mb = NAMES[int(np.bincount(P['bins'][m], minlength=10)[1:].argmax()) + 1] if m.any() else 'no ink'
            fl.append(dict(state=e['state'], main=mb, length=float(np.hypot(e['b'][0] - e['a'][0], e['b'][1] - e['a'][1]))))
    r['editor_lines_grid0'] = dict(lines=len(E), false_lines=len(fl), false_green=sum(f['state'] == 'green' for f in fl), false_length=round(sum(f['length'] for f in fl)),
                                   false_by_main_bin={k: sum(f['main'] == k for f in fl) for k in sorted({f['main'] for f in fl})},
                                   false_length_by_main_bin={k: round(sum(f['length'] for f in fl if f['main'] == k)) for k in sorted({f['main'] for f in fl})})
    res['44'][s] = r; print('44', s, json.dumps(r), flush=True)
del P
# ---- 1A (the whole plate, and the held-out region right of Elm St)
P = plate_setup('1A', SP + 'train_v2/1A/streetmap.json', DIAG + '/bins_1A_now.png'); H, W = P['H'], P['W']; h, w = H // 2, W // 2
vm = cv2.imread(SP + 'train_v2/1A/valmask.png', 0) > 0; vf = cv2.resize(vm.astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST) > 0
lab1 = cv2.imread(SP + 'train_v2/1A/label.png', 0); th1 = text_half(P['bins'], h, w); res['1A'] = {}
for s in STEPS:
    p = cv2.imread(EV + f'{s}/maps1A/1A_lines.png', 0); pa = cv2.imread(EV + f'{s}/maps1A/1A_area.png', 0)
    res['1A'][s] = dict(lines_whole=false_comp(P, p), lines_heldout=false_comp(P, p, vf), area_whole=area_err(P, pa, lab1, th1), area_heldout=area_err(P, pa, lab1, th1, vm))
    print('1A', s, json.dumps(res['1A'][s]), flush=True)
del P
# ---- 5 (baseline batch maps only)
P = plate_setup('5', DIAG + '/map_now/5_streetmap.json', DIAG + '/bins_5_now.png'); H, W = P['H'], P['W']; h, w = H // 2, W // 2
lab5 = cv2.imread(DIAG + '/map_now/5_label.png', 0); th5 = text_half(P['bins'], h, w)
p = cv2.imread(SP + 'unet_data/5_lines_lines_ng1.png', 0); pa = cv2.imread(SP + 'unet_data/5_pred_area_ng1.png', 0)
res['5'] = dict(baseline=dict(lines=false_comp(P, p), area=area_err(P, pa, lab5, th5))); print('5', json.dumps(res['5']), flush=True)
wj(os.path.join(DIAG, 'false_response.json'), res)
