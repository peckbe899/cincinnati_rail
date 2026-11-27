"""dbg_rail_window.py (handoff, 26 Nov 2026): the railroad rule of ink_bins_text.py on one window of a plate, with and
without the text mask, to see why a track is lost. Debug only; writes a picture into handoff/pics/.
    cd data/sanborn; python -B .../dbg_rail_window.py N X0 Y0 X1 Y1 OUT.png [--ground map]"""
import sys, os, json
import numpy as np, cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ink_bins_text as IB
N = sys.argv[1]; x0, y0, x1, y1 = map(int, sys.argv[2:6]); out = sys.argv[6]
im = cv2.imread(f'cufp/22-{N}.jpg'); H, W = im.shape[:2]; im = im[y0:y1, x0:x1]; h, w = im.shape[:2]
L = cv2.cvtColor(im, cv2.COLOR_BGR2LAB)[..., 0]; al = np.load(f'cufp/{N}/png_alpha_s4.npy'); paper = cv2.resize(al, (W, H), interpolation=cv2.INTER_NEAREST)[y0:y1, x0:x1] > 0
ink = (L < IB.INK_L) & paper
closed = np.zeros((h, w), np.uint8)
if os.path.exists(f'streetmap/22-{N}.json'):
    for bl in json.load(open(f'streetmap/22-{N}.json', encoding='utf8'))['blocks']: cv2.fillPoly(closed, [np.round(np.array(bl['ring']) - [x0, y0]).astype(np.int32)], 1)
tc = cv2.imread(f'bench_2026-11-25/text_v1/handoff/masks/{N}_text.png', 0)[y0:y1, x0:x1]; T = np.isin(tc, (2, 3)) & ink
pics = []
for name, ik in (('before', ink), ('after', ink & ~T)):
    IB.TEXT = T if name == 'after' else None; rr, info = IB.railroad(ik, closed, paper)
    c = (im * 0.45 + 140).astype(np.uint8); c[ik] = (90, 90, 90); c[rr] = (0, 0, 230); c[T] = (255, 0, 255) if name == 'after' else c[T]
    car = info['carrow']; c[car & ik] = (0, 150, 255)
    for p in info['T']: cv2.circle(c, tuple(np.round(p).astype(int).tolist()), 6, (200, 0, 0), 1)
    for i, j in info['E']: cv2.line(c, tuple(np.round(info['T'][i]).astype(int).tolist()), tuple(np.round(info['T'][j]).astype(int).tolist()), (0, 120, 0), 2)
    cv2.putText(c, f"{name}: clear {info['clear']} faint {info['faint']} chained {info['chained']} spurs {info['spurs']}", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    print(name, 'clear', info['clear'], 'faint', info['faint'], 'chained', info['chained'], 'spurs', info['spurs'], 'rr px', int(rr.sum()), 'carrow px', int((car & ik).sum()))
    pics.append(c)
cv2.imwrite(out, np.hstack(pics) if w < h else np.vstack(pics))
