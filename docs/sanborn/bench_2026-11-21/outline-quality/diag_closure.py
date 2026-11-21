"""outline-quality: which of Ben's blocks are found by an outline (IoU > 0.5) but do not close in the editor (no face
of the shown lines + sheet outline at snap 10 with IoU >= 0.8), and why.
    python diag_closure.py '{"markers": true, ...}' [step4]
Prints per Ben block: outline IoU, best face IoU, centroid; writes runs/diag_closure/<n>.jpg crops (half size) of the
first few unclosed blocks with the shown lines (green / orange) and Ben's ring (magenta)."""
import json, os, sys
import numpy as np, cv2
sys.dont_write_bytecode = True
import sweep as S  # noqa: E402
B, O = S.B, S.O
P = json.loads(sys.argv[1]); st4 = sys.argv[2] if len(sys.argv) > 2 else 'default'
S.init(B.U + '44_pred_area_ng1.png', B.U + '44_lines_lines_ng1.png'); T = S.G['T']
polys, rep, _, block, inst = O.outline(S.G['D'], P, vis_out=False)
rings = [np.array([s['a'] for s in p], float) for p in polys]; r, iou_o = B.pq(T, B.raster(rings), len(rings))
edges = S.STEP4[st4](polys); shown = B.clean(edges)
F = B.faces([(e['a'], e['b']) for e in shown] + [(s['a'], s['b']) for s in S.G['SH']], 10.0); rf, iou_f = B.pq(T, B.raster(F), len(F))
out = HERE = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/') + '/runs/diag_closure/'; os.makedirs(out, exist_ok=True)
full = cv2.imread(B.SP + 'cufp/22-44.jpg'); k = 0
print('ben  outlineIoU faceIoU  centroid')
for i in range(T['ng']):
    tag = 'closed' if iou_f[i] >= 0.8 else ('NOT CLOSED' if iou_o[i] > 0.5 else 'not found')
    print(f'{i + 1:3d}  {iou_o[i]:.2f}  {iou_f[i]:.2f}  {T["cen"][i].round().astype(int).tolist()}  {tag}')
    if tag == 'NOT CLOSED' and k < 12:
        rg = T['rings'][i]; x0, y0 = (rg.min(0) - 150).clip(0).astype(int); x1, y1 = (rg.max(0) + 150).astype(int); x1 = min(x1, B.W); y1 = min(y1, B.H)
        im = (full[y0:y1, x0:x1] * 0.55 + 110).astype(np.uint8); sc = 0.5; im = cv2.resize(im, None, fx=sc, fy=sc)
        Q = lambda p: tuple(((np.array(p) - [x0, y0]) * sc).round().astype(int))
        cv2.polylines(im, [((rg - [x0, y0]) * sc).round().astype(np.int32)], True, (200, 0, 200), 1, cv2.LINE_AA)
        for e in shown: cv2.line(im, Q(e['a']), Q(e['b']), (0, 150, 0) if e['state'] == 'green' else (0, 130, 255), 2, cv2.LINE_AA)
        for s in S.G['SH']: cv2.line(im, Q(s['a']), Q(s['b']), (120, 120, 120), 1, cv2.LINE_AA)
        for p in polys:
            for s in p:
                if s.get('paper_edge'): cv2.line(im, Q(s['a']), Q(s['b']), (150, 60, 0), 1, cv2.LINE_AA)
        cv2.imwrite(out + f'ben{i + 1}.jpg', im); k += 1
print('closed', int((iou_f >= 0.8).sum()), 'found', int((iou_o > 0.5).sum()))
