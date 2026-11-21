"""outline-quality: crop of a checked plate, batch above and variant below, from plates/TAG/N_*_shown.json.
    python crop_plate.py TAG N x0 y0 x1 y1 [scale 0.4] [step4 policy for the variant: default|drop_nol]
Shown lines green / orange; bridging sides of the variant ringed cyan; grey = short or paper-edge pieces (not shown in
the editor). With a policy other than the one plates_check used, the variant's lines are rebuilt from its outlines.json
(sweep.STEP4 + the editor's clean()). Writes plates/TAG/N_crop_x0_y0[_policy].jpg."""
import json, os, sys
import numpy as np, cv2
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/') + '/'
sys.path.insert(0, HERE)
import sweep as S  # noqa: E402
SP = S.O.SP
tag, N = sys.argv[1], sys.argv[2]; x0, y0, x1, y1 = [int(v) for v in sys.argv[3:7]]; sc = float(sys.argv[7]) if len(sys.argv) > 7 else 0.4
pol = sys.argv[8] if len(sys.argv) > 8 else None
d = HERE + f'plates/{tag}/'; full = cv2.imread(SP + f'cufp/22-{N}.jpg')[y0:y1, x0:x1]
def panel(name):
    polys = json.load(open(d + f'{N}_{name}_outlines.json'))
    shown = json.load(open(d + f'{N}_{name}_shown.json')) if (name == 'batch' or pol is None) else S.B.clean(S.STEP4[pol](polys))
    im = (cv2.resize(full, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA) * 0.55 + 110).astype(np.uint8)
    P = lambda p: tuple(((np.array(p, float) - [x0, y0]) * sc).round().astype(int))
    for p in polys:
        for s in p:
            if s['state'] == 'short' or s.get('paper_edge'): cv2.line(im, P(s['a']), P(s['b']), (150, 150, 150), 1, cv2.LINE_AA)
    for e in shown: cv2.line(im, P(e['a']), P(e['b']), (0, 150, 0) if e['state'] == 'green' else (0, 130, 255), 2, cv2.LINE_AA)
    for p in polys:
        for s in p:
            if s.get('bridge') and not s.get('paper_edge'): cv2.circle(im, P((np.array(s['a']) + np.array(s['b'])) / 2), 5, (230, 200, 0), 2)
    cv2.putText(im, f'{N} {name}' + (f' ({pol})' if name != 'batch' and pol else ''), (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    return im
a, b = panel('batch'), panel('variant')
f = d + f'{N}_crop_{x0}_{y0}' + (f'_{pol}' if pol else '') + '.jpg'
cv2.imwrite(f, np.vstack([a, np.full((6, a.shape[1], 3), 255, np.uint8), b]), [cv2.IMWRITE_JPEG_QUALITY, 85]); print(f)
