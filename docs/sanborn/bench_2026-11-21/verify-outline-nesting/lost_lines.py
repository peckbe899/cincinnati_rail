"""verify-outline-nesting: on PDF sheets where the proposal exports FEWER lines than the batch, which batch lines are lost,
and where do they lie (off the map ground = a good drop; on the map ground = a possible regression)? (21 Nov 2026)

    python lost_lines.py N [N ...]   -> lost/N_lost.jpg, lost_lines.json

A batch line (unet_data/N_edges.json) is 'lost' when less than half of its length (1 px samples) has a final exported side
(outline-nesting/runs_plates/final/N) within 6 px and 20 degrees. Its midpoint is tested against map_area.py's map ground
(visual-pdf/maparea_check/N_mask8.png, the mask the final run used), eroded by 40 px: on map / near or off the map edge.
Picture: scan at 1/8, map ground edge white, lost lines red (on map) or blue (at or off the map edge), final lines green.
"""
import json, os, sys
import numpy as np
import cv2
from scipy.spatial import cKDTree
HERE = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/') + '/'
D = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
AG = D + 'bench_2026-11-21/outline-nesting/runs_plates/final/'; MASKS = D + 'bench_2026-11-21/visual-pdf/maparea_check/'
os.makedirs(HERE + 'lost', exist_ok=True)


def samples(segs):
    P, Dv, I = [], [], []
    for i, (a, b) in enumerate(segs):
        a, b = np.asarray(a, float), np.asarray(b, float); L = np.hypot(*(b - a))
        if L < 1: continue
        t = np.linspace(0, 1, max(2, int(L))); P.append(a + np.outer(t, b - a)); Dv.append(np.tile((b - a) / L, (len(t), 1))); I.append(np.full(len(t), i))
    if not P: return np.zeros((0, 2)), np.zeros((0, 2)), np.zeros(0, int)
    return np.vstack(P), np.vstack(Dv), np.concatenate(I)


res = {}
for N in sys.argv[1:]:
    E = json.load(open(D + f'unet_data/{N}_edges.json', encoding='utf8'))
    F = [(s['a'], s['b']) for p in json.load(open(AG + f'{N}/outlines.json', encoding='utf8')) for s in p if not (s['state'] == 'short' or s.get('paper_edge'))]
    bp, bd, bi = samples([(e['a'], e['b']) for e in E]); fp, fd, _ = samples(F); tr = cKDTree(fp)
    ok = np.zeros(len(bp), bool)
    for k, nb in enumerate(tr.query_ball_point(bp, 6.0)):
        if nb and np.max(np.abs(fd[nb] @ bd[k])) >= np.cos(np.radians(20)): ok[k] = True
    share = np.bincount(bi, ok, minlength=len(E)) / np.maximum(np.bincount(bi, minlength=len(E)), 1)
    full = cv2.imread(D + f'cufp/22-{N}.jpg', cv2.IMREAD_REDUCED_COLOR_8); h8, w8 = full.shape[:2]
    m8 = cv2.imread(MASKS + f'{N}_mask8.png', 0); m8 = cv2.resize(m8, (w8, h8), interpolation=cv2.INTER_NEAREST) > 127
    inner = cv2.erode(m8.astype(np.uint8), np.ones((11, 11), np.uint8)) > 0       # 5 px at 1/8 = 40 full px
    im = (full * 0.6 + 90).astype(np.uint8)
    cs, _ = cv2.findContours(m8.astype(np.uint8), cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE); cv2.drawContours(im, cs, -1, (255, 255, 255), 2)
    for a, b in F: cv2.line(im, (int(a[0] / 8), int(a[1] / 8)), (int(b[0] / 8), int(b[1] / 8)), (0, 150, 0), 1, cv2.LINE_AA)
    lost = {'on_map': [0, 0.0], 'edge_or_off': [0, 0.0]}
    for i, e in enumerate(E):
        if share[i] >= 0.5: continue
        a, b = np.array(e['a']), np.array(e['b']); m = ((a + b) / 2 / 8).astype(int); L = float(np.hypot(*(b - a)))
        yy, xx = min(h8 - 1, max(0, m[1])), min(w8 - 1, max(0, m[0]))
        on = bool(inner[yy, xx]); k = 'on_map' if on else 'edge_or_off'
        lost[k][0] += 1; lost[k][1] += L
        k2 = 'off_map' if not m8[yy, xx] else ('edge_band_inside' if not on else None)          # split of edge_or_off
        if k2: lost.setdefault(k2, [0, 0.0]); lost[k2][0] += 1; lost[k2][1] += L
        cv2.line(im, (int(a[0] / 8), int(a[1] / 8)), (int(b[0] / 8), int(b[1] / 8)), (0, 0, 255) if on else (255, 80, 0), 3, cv2.LINE_AA)
    cv2.imwrite(HERE + f'lost/{N}_lost.jpg', im, [cv2.IMWRITE_JPEG_QUALITY, 85])
    res[N] = dict(batch_lines=len(E), final_exported=len(F), lost_on_map=dict(n=lost['on_map'][0], len=round(lost['on_map'][1])), lost_edge_or_off=dict(n=lost['edge_or_off'][0], len=round(lost['edge_or_off'][1])),
                  of_which_off_map=dict(n=lost.get('off_map', [0, 0])[0], len=round(lost.get('off_map', [0, 0])[1])), of_which_edge_band_inside=dict(n=lost.get('edge_band_inside', [0, 0])[0], len=round(lost.get('edge_band_inside', [0, 0])[1])))
    print(N, res[N])
json.dump(res, open(HERE + 'lost_lines.json', 'w'), indent=1)
