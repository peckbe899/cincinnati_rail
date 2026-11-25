"""Q2a (ben-labels, 25 Nov 2026): how the text-and-number ink near a true street line is taught today.
    cd data/sanborn; python -B bench_2026-11-25/diag/ben-labels/scripts/text_near_lines.py
Text = ink_bins bin 8 (44: unet_data/44_bins.png from Ben's street map; 1A, 5, 43: re-run today into this folder).
True lines = the line target's positives (t == 1: Ben's printed and drawn lines on 1A, 5 map, 44; the verified edges on
43; the green lines on 5 pseudo). d = distance (full px) from a text pixel to the nearest positive pixel. Buckets:
on (d <= 2), margin (2 < d <= 9: edgenet's GAP margin reaches 7 px past the 3 px line), near (9 < d <= 20), mid
(20 < d <= 40). Per bucket: share of the text pixels the target makes positive / negative / unscored, and the mean loss
weight (edgenet.build: POS 3, NEG_INK 4 on edgenet ink, 1 on other negatives, 0 unscored).
"""
import sys, os, json
import numpy as np, cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *  # noqa
SETS = {
    '44': (SP + 'unet_data/44_bins.png', [('map recipe (hypothetical)', DIAG + '/map_now/44_lines.png')]),
    '1A': (DIAG + '/bins_1A_now.png', [('train_v2 map (V1, V2)', SP + 'train_v2/1A/lines.png')]),
    '5': (DIAG + '/bins_5_now.png', [('train_v2 pseudo (V2)', SP + 'train_v2/5/lines.png'), ('map recipe now (not trained)', DIAG + '/map_now/5_lines.png')]),
    '43': (DIAG + '/bins_43_now.png', [('train_v2 label = make_labels.py (all pairs)', SP + 'train_v2/43/lines.png')]),
}
BK = [('on (<=2)', 0, 2), ('margin (2-9]', 2, 9), ('near (9-20]', 9, 20), ('mid (20-40]', 20, 40)]
res = {}
for N, (bf, sets) in SETS.items():
    full = scan(N); H, W = full.shape[:2]; ink = ink_edgenet(full); del full; af = alpha_full(N, W, H)
    bins = cv2.imread(bf, 0); text = (bins == 8) & af; res[N] = {'text_px_on_paper': int(text.sum()), 'ink_px_bins': int(((bins > 0) & af).sum())}
    for name, tf in sets:
        t = cv2.imread(tf, 0); d = cv2.distanceTransform((t != 1).astype(np.uint8), cv2.DIST_L2, 5)
        wgt = np.zeros((H, W), np.float32); wgt[t == 0] = 1.0; wgt[(t == 0) & ink] = NEG_INK; wgt[t == 1] = POS
        out = {}
        for bn, lo, hi in BK:
            m = text & (d > lo) & (d <= hi) if lo > 0 else text & (d <= hi)
            out[bn] = share(m, t, (1, 0, 255)) | {'mean_weight': round(float(wgt[m].mean()) if m.any() else 0, 3), 'share_of_all_text': round(float(m.sum() / max(1, text.sum())), 4)}
        m40 = text & (d <= 40); out['all within 40'] = share(m40, t, (1, 0, 255)) | {'mean_weight': round(float(wgt[m40].mean()), 3), 'share_of_all_text': round(float(m40.sum() / max(1, text.sum())), 4)}
        mfar = text & (d > 40); out['beyond 40'] = share(mfar, t, (1, 0, 255)) | {'mean_weight': round(float(wgt[mfar].mean()), 3)}
        # compare: all non-text ink within 9..40 px, and its weight
        oth = (bins > 0) & (bins != 8) & af & (d > 9) & (d <= 40); out['other ink 9-40'] = share(oth, t, (1, 0, 255)) | {'mean_weight': round(float(wgt[oth].mean()), 3)}
        # the loss mass: share of all negative weight that sits on text within 40 px
        out['neg_weight_share_on_text40'] = round(float(wgt[m40 & (t == 0)].sum() / max(1, wgt[t == 0].sum())), 4)
        out['neg_weight_share_on_text_all'] = round(float(wgt[text & (t == 0)].sum() / max(1, wgt[t == 0].sum())), 4)
        res[N][name] = out; print(N, name, json.dumps(out), flush=True)
wj(os.path.join(DIAG, 'text_near_lines.json'), res)
