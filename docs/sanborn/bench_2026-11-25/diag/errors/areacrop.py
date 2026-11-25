"""side-by-side half-size crops of P(block) (area net) for the baseline and the four pairs, grid 0, in a window
    python -B areacrop.py X0 Y0 X1 Y1 NAME  -> pics/area_NAME.jpg (white = block, black = street)"""
import sys, numpy as np, cv2
EV = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/train_v2_runs/eval/'
HERE = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-25/diag/errors/'
x0, y0, x1, y1 = [int(v) // 2 for v in sys.argv[1:5]]; name = sys.argv[5]
tiles = []
for s in ['baseline', 'V1S1', 'V2S1', 'V1S2', 'V2S2']:
    a = cv2.imread(EV + f'{s}/maps44/grid0/44_area.png', 0)[y0:y1, x0:x1]
    t = cv2.cvtColor(a, cv2.COLOR_GRAY2BGR); cv2.putText(t, s, (8, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)
    tiles.append(np.pad(t, ((4, 4), (4, 4), (0, 0)), constant_values=128))
cv2.imwrite(HERE + f'pics/area_{name}.jpg', np.hstack(tiles[:3]) if len(tiles) == 3 else np.vstack([np.hstack(tiles[:3]), np.hstack(tiles[3:] + [np.full_like(tiles[0], 128)])]), [cv2.IMWRITE_JPEG_QUALITY, 85])
