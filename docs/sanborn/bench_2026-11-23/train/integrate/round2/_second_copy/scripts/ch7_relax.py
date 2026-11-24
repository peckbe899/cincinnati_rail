"""Integrator, round 2 (24 Nov 2026): could the channel-7 shortcut (review-leak finding 1) be closed in the labels
instead of the trainer? Review-leak's second option: let pseudo 'not a line' pixels reach the area map's 0.5 crossing
wherever lines_ng1 was quiet. For each pseudo plate given: the pixels where area_in (resized as edgenet.pack does)
crosses 0.5, and the share of them that such a relaxed rule could make negative at all: at least ms px from every
outline side and orange line (dside) AND at least mr px from a line-net response above tl (dres), with the 'mu px
from untaught area ground' rule dropped. Reads only (the staged make_labels_v2.pseudo_inputs).
cd data/sanborn; ../../tools/sanborn/unet/.venv/Scripts/python.exe -B THIS PLATE ... > OUT.json"""
import json, os, sys
import numpy as np, cv2
sys.path.insert(0, 'bench_2026-11-23/train/staged/tools/sanborn/unet')
import make_labels_v2 as M
th = M.PSEUDO; res = {}
for N in sys.argv[1:]:
    I = M.pseudo_inputs(N); H, W = I['H'], I['W']
    a = cv2.resize(I['pa'], (W, H), interpolation=cv2.INTER_LINEAR)
    b = cv2.morphologyEx((a > 127).astype(np.uint8), cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)) > 0; del a
    b &= I['af']
    resp = I['pl'] > th['tl'] * 255; dres = cv2.distanceTransform((~resp).astype(np.uint8), cv2.DIST_L2, 5)
    far_side = I['dside'] >= th['ms']; quiet = dres >= th['mr']
    n = int(b.sum())
    res[N] = dict(crossing_px=n, far_from_sides=round(float(far_side[b].mean()), 4), quiet_line_net=round(float(quiet[b].mean()), 4),
                  both=round(float((far_side & quiet)[b].mean()), 4))
    print(N, json.dumps(res[N]), file=sys.stderr, flush=True)
print(json.dumps(res, indent=1))
