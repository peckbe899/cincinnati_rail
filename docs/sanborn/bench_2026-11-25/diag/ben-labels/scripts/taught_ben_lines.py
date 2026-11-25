"""Q1 (ben-labels, 25 Nov 2026): how the current labels teach the lines Ben DELETED (verdict 'wrong': network lines he
judged false), the lines he ADDED (misses) and the lines he MOVED (old and new place).
    cd data/sanborn; python -B bench_2026-11-25/diag/ben-labels/scripts/taught_ben_lines.py
Line net (full size): a line's pixels = the line drawn LINE (3) px wide, on the paper. Shares of the target t (1 line,
0 not, 255 not scored) and the loss weight the trainer gives (edgenet.build: 1, NEG_INK 4 on ink where t == 0, POS 3
where t == 1, 0 where unscored). 'ink11' = the ink pixels (edgenet's ink) within the WRONG_PX (11) px strip along the
line: what the network actually responds to.
Area net (half size): 'under' = the line 1 px at half size; 'beside' = 2..8 half px either side. Label 0 street, 1
block, 255 not taught. The area net's third output's target (edge.png, dilated 3x3 = 1; 0 where taught; 255 untaught).
"""
import sys, os, json
import numpy as np, cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *  # noqa

SETS = {
    '1A': [('train_v2 map label (V1, V2)', SP + 'train_v2/1A/label.png', SP + 'train_v2/1A/lines.png', SP + 'train_v2/1A/edge.png')],
    '5': [('train_v2 pseudo label (V2; made 24 Nov, before Ben checked 5)', SP + 'train_v2/5/label.png', SP + 'train_v2/5/lines.png', SP + 'train_v2/5/edge.png'),
          ('map recipe on Ben\'s 25 Nov lines (not trained; diag map_now)', DIAG + '/map_now/5_label.png', DIAG + '/map_now/5_lines.png', DIAG + '/map_now/5_edge.png')],
    '44': [('map recipe on Ben\'s truth (hypothetical: 44 is never trained; diag map_now)', DIAG + '/map_now/44_label.png', DIAG + '/map_now/44_lines.png', DIAG + '/map_now/44_edge.png')],
    '43': [('train_v2 label = make_labels.py (all pairs, baseline too)', SP + 'train_v2/43/label.png', SP + 'train_v2/43/lines.png', SP + 'train_v2/43/edge.png')],
}
res = {}
for N, sets in SETS.items():
    full = scan(N); H, W = full.shape[:2]; ink = ink_edgenet(full); del full
    af = alpha_full(N, W, H); h, w = H // K, W // K; ah = alpha_half(N, w, h); G = groups(N); res[N] = {'counts': {k: len(v) for k, v in G.items()}}
    for name, lf, tf, ef in sets:
        lab = cv2.imread(lf, 0); t = cv2.imread(tf, 0); e = cv2.imread(ef, 0)
        assert t.shape == (H, W) and lab.shape == (h, w), (N, t.shape, lab.shape)
        etg = (cv2.dilate((e > 0).astype(np.uint8), np.ones((3, 3), np.uint8)) > 0).astype(np.uint8); etg[(lab == 255) & (etg == 0)] = 255
        wgt = np.zeros((H, W), np.float32); wgt[t == 0] = 1.0; wgt[(t == 0) & ink] = NEG_INK; wgt[t == 1] = POS
        out = {}
        for gname, L in G.items():
            if not L: out[gname] = dict(lines=0); continue
            m = (raster(L, (H, W), 1.0, LINE) > 0) & af
            strip = (raster(L, (H, W), 1.0, WRONG_PX) > 0) & af & ink
            under = (raster(L, (h, w), 1.0 / K, 1) > 0) & ah
            besid = (raster(L, (h, w), 1.0 / K, 17) > 0) & ~(raster(L, (h, w), 1.0 / K, 3) > 0) & ah
            per = []
            for a, b in L:
                mm = (raster([(a, b)], (H, W), 1.0, LINE) > 0) & af
                n = int(mm.sum())
                if n == 0: per.append('off paper'); continue
                s1, s0 = (t[mm] == 1).mean(), (t[mm] == 0).mean()
                per.append('positive' if s1 > 0.5 else 'negative' if s0 > 0.5 else 'unscored' if (t[mm] == 255).mean() > 0.5 else 'mixed')
            r = dict(lines=len(L), length_px=round(sum(float(np.hypot(b[0] - a[0], b[1] - a[1])) for a, b in L)),
                     line_px=share(m, t, (1, 0, 255)), line_px_on_ink=round(float((m & ink).sum() / max(1, m.sum())), 4),
                     mean_weight_per_px=round(float(wgt[m].mean()), 3), neg_weight_share_at_ink4=round(float(((t == 0) & ink & m).sum() / max(1, m.sum())), 4),
                     ink11=share(strip, t, (1, 0, 255)), lines_by_majority={k: per.count(k) for k in ('positive', 'negative', 'unscored', 'mixed', 'off paper')},
                     area_under=share(under, lab, (0, 1, 255)), area_beside=share(besid, lab, (0, 1, 255)), area_edge_target_under=share(under, etg, (1, 0, 255)))
            out[gname] = r
        # the reference: every scored pixel of the plate
        out['plate_reference'] = dict(t_pos_px=int((t == 1).sum()), t_neg_px=int((t == 0).sum()), t_neg_ink_px=int(((t == 0) & ink).sum()), t_unscored_on_paper_px=int(((t == 255) & af).sum()),
                                      paper_px=int(af.sum()), weight_pos=round(float(wgt[t == 1].sum())), weight_neg=round(float(wgt[t == 0].sum())))
        res[N][name] = out
        print(N, name); print(json.dumps(out, indent=None)[:3000], flush=True)
wj(os.path.join(DIAG, 'taught_ben_lines.json'), res)
