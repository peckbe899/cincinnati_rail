"""merge/impl/r2: does the staged outlines.py's numpy thin() give the same pixels as cv2.ximgproc.thinning? (21 Nov 2026)

    venv python -B thin_check.py [N ...]      -> merge/impl/r2/thin_check.json

thin() is taken from the staged outlines.py by its source (ast), not by importing the script. The mask is the one
outlines.py thins for Q1: the line map at half size, P > 110/255, on the paper eroded by 15 px (here the paper, not an
uncut sheet's map ground: any mask tests the thinning).
"""
import ast, json, sys, time
import numpy as np
import cv2
import common as C
src = open(C.SU + 'outlines.py', encoding='utf8').read(); tree = ast.parse(src)
fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'thin'); ns = dict(np=np); exec(ast.get_source_segment(src, fn), ns); thin = ns['thin']
assert hasattr(cv2, 'ximgproc'), 'run under the venv (cv2.ximgproc)'
res = {}
for n in (sys.argv[1:] or ['44', '90', '5', '3', '47', '21', '1B', '60B', '93A']):
    pl = cv2.imread(C.U + f'{n}_lines_lines_ng1.png', 0); H, W = pl.shape
    al = cv2.resize(np.load(C.DATA + f'cufp/{n}/png_alpha_s4.npy').astype(np.uint8), (W // 2, H // 2), interpolation=cv2.INTER_NEAREST)
    ph = (cv2.resize(pl, (W // 2, H // 2), interpolation=cv2.INTER_AREA) > 110) & (cv2.erode(al, np.ones((15, 15), np.uint8)) > 0)
    t = time.time(); a = cv2.ximgproc.thinning(ph.astype(np.uint8) * 255) > 0; ta = time.time() - t
    t = time.time(); b = thin(ph); tb = time.time() - t
    res[n] = dict(mask_px=int(ph.sum()), skel_ximgproc=int(a.sum()), skel_numpy=int(b.sum()), px_differ=int((a != b).sum()), seconds_ximgproc=round(ta, 2), seconds_numpy=round(tb, 2))
    print(n, res[n], flush=True)
res['all_identical'] = all(v['px_differ'] == 0 for v in res.values())
res['opencv'] = cv2.__version__
json.dump(res, open(C.IMPL + 'thin_check.json', 'w'), indent=1); print('all identical:', res['all_identical'])
