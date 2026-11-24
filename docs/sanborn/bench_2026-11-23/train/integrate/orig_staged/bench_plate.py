"""bench_plate: bench44's scores on any plate with a street map of Ben's, optionally inside a region (23 November 2026).

    cd data/sanborn
    python ../../tools/sanborn/unet/bench_plate.py --plate 1A --truth STREETMAP.json --area A.png --lines L.png
           [--region MASK.png] [--tag NAME] [--runs DIR] [--no-pic] [--reuse]
    python ../../tools/sanborn/unet/bench_plate.py --make-truth N OUT.json

A wrapper, not a copy: it imports bench44.py (beside it) and runs bench44.main() unchanged (the REAL outline step,
outlines.py --area-png --lines-png --out, the real step 4 and the editor's clean() and sheet(), every score and JSON key
as bench44's), with five of bench44's plate-44 settings replaced for the run:
  - N, W, H (and the half-size raster size) from --plate and its scan, cufp/22-N.jpg;
  - the truth: --truth, a street map in streetmap/22-N.json's format (its size must be the scan's);
  - the folds: A = inside --region (a mask PNG, nonzero = in; half size, or resized to it), B = outside; with no
    --region every block and line is in A. Blocks and predicted blocks go by centroid, line samples by their own
    position, whole lines (workload) by midpoint, as bench44's folds do. So with --region the region's scores are the
    'A' entries; bench_plate.json repeats them as region_headline.region (and B as region_headline.outside);
  - the decided ground, cached under the plate, the truth's sha256 and WMAX;
  - the sheet outline (edit_server.sheet of the plate) and the picture (the plate's scan; the region outlined).
Writes RUNS/TAG/ as bench44 does, plus bench_plate.json (bench44.json with the meta fixed and region_headline added);
prints one json line of the headline scores.

--make-truth N OUT.json: the street map of plate N from Ben's edits, made as street_map.py makes streetmap/22-N.json
(the same code: street_map.editor_lines, the same polygonize, the same json), but written to OUT.json and nothing into
streetmap/ or unet_data/. Checked on 44: it gives streetmap/22-44.json byte for byte (bench_2026-11-23/train/trainer).
"""
import argparse, contextlib, hashlib, io, json, os, sys, time
import numpy as np
import cv2
HERE = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/') + '/'; sys.path.insert(0, HERE); sys.path.insert(0, HERE + '..')
import _ws  # noqa: E402
SP = _ws.DATA


def sha(p, n=16): return hashlib.sha256(open(p, 'rb').read()).hexdigest()[:n] if os.path.exists(p) else None


def make_truth(N, out, tol=1.5, edge=60.0):
    """street_map.main's street map of plate N (its json), written to out (cwd must be data/sanborn)"""
    from shapely.geometry import LineString, Point
    from shapely.ops import unary_union, polygonize_full
    import street_map as SM
    N = N.upper(); TOL, EDGE = tol, edge
    bf = f'picks22_guided/22-{N}/edges_ben.json'; B = json.load(open(bf, encoding='utf8'))
    im = cv2.imread(f'cufp/22-{N}.jpg'); H, W = im.shape[:2]
    L, SH = SM.editor_lines(N, W, H, json.load(open(f'unet_data/{N}_edges.json', encoding='utf8')), B)
    def ext(l):
        a, b = np.array(l['a'], float), np.array(l['b'], float); d = (b - a) / np.hypot(*(b - a)); return LineString([a - d * TOL, b + d * TOL])
    ls = [LineString([l['a'], l['b']]) for l in L]; paper = unary_union([LineString([s['a'], s['b']]) for s in SH])
    P = sorted(polygonize_full(unary_union([ext(l) for l in L]))[0].geoms, key=lambda p: (round(p.centroid.y / 400), p.centroid.x))
    P = [p for p in P if p.area >= 400]
    blocks = []
    for i, p in enumerate(P):
        (cx, cy), (w, h), _ = cv2.minAreaRect(np.array(p.exterior.coords, np.float32))
        blocks.append(dict(id=i + 1, area_px=round(p.area), narrow_px=round(min(w, h)), ring=[[round(x, 1), round(y, 1)] for x, y in p.exterior.coords[:-1]]))
    ends = []
    for i, l in enumerate(L):
        for p in (l['a'], l['b']):
            g = min(o.distance(Point(p)) for j, o in enumerate(ls) if j != i)
            if g > TOL: d = paper.distance(Point(p)); ends.append(dict(at=[round(p[0], 1), round(p[1], 1)], gap_px=round(g, 1), where='sheet_edge' if d <= EDGE else 'inside', paper_edge_px=round(d)))
    kinds = {k: [sum(1 for l in L if l['kind'] == k), round(sum(ls[i].length for i, l in enumerate(L) if l['kind'] == k))] for k in ('printed', 'drawn', 'sheet_edge', 'no_printed_line')}
    res = dict(plate=N, size=[W, H], source=bf, source_saved_at=B.get('saved_at'), tolerance_px=TOL, sheet_edge_px=EDGE,
               note="Ben's ground truth street sides. Open ends are meant: a street that carries on to another sheet, or stops at the creek, canal or railway, is left open.",
               counts=dict(lines=len(L), length_px=round(sum(l.length for l in ls)), by_kind=kinds, blocks=len(blocks), open_ends=len(ends), open_at_sheet_edge=sum(e['where'] == 'sheet_edge' for e in ends), open_inside=sum(e['where'] == 'inside' for e in ends)),
               lines=[dict(a=[round(v, 1) for v in l['a']], b=[round(v, 1) for v in l['b']], kind=l['kind'], name=l['name']) for l in L], blocks=blocks, open_ends=ends)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    json.dump(res, open(out, 'w', encoding='utf8', newline='\n'), separators=(',', ':')); return res['counts']


def setup(B, plate, truth_file, region_file):
    """replace bench44's plate-44 settings (module B) for this plate"""
    ES = B.ES; S = B.S
    sm = json.load(open(truth_file, encoding='utf8')); scan = cv2.imread(SP + f'cufp/22-{plate}.jpg')
    H, W = scan.shape[:2]
    if sm['size'] != [W, H]: sys.exit(f'the truth is for a {sm["size"]} plate, the scan of {plate} is {[W, H]}')
    h2, w2 = int(H * S), int(W * S)
    B.N, B.W, B.H, B.h2, B.w2 = plate, W, H, h2, w2
    if region_file:
        M = cv2.imread(region_file, 0)
        if M is None: sys.exit(f'no region mask {region_file}')
        if M.shape != (h2, w2): M = cv2.resize(M, (w2, h2), interpolation=cv2.INTER_NEAREST)
        M = M > 0
    else: M = np.ones((h2, w2), bool)
    def is_a(x, y):
        x = np.nan_to_num(np.asarray(x, float)); y = np.nan_to_num(np.asarray(y, float))
        return M[np.clip((y * S).astype(int), 0, h2 - 1), np.clip((x * S).astype(int), 0, w2 - 1)]
    tsha = sha(truth_file)
    def decided_ground(gt, ng, alpha2):
        """bench44.decided_ground, cached under this plate and its truth"""
        f = B.RUNS + f"cache/decided_half_{plate}_{tsha}_{B.WMAX:g}.png"
        if os.path.exists(f): return cv2.imread(f, 0) > 0
        wm = B.WMAX * S; d1 = np.full((h2, w2), np.inf, np.float32); l1 = np.zeros((h2, w2), np.int32); d2 = np.full((h2, w2), np.inf, np.float32)
        off = cv2.distanceTransform(np.pad(alpha2.astype(np.uint8), 1), cv2.DIST_L2, 5)[1:-1, 1:-1]
        for i in [-1] + list(range(1, ng + 1)):
            if i == -1: y0, y1, x0, x1 = 0, h2, 0, w2; d = off
            else:
                ys, xs = np.nonzero(gt == i)
                if not len(ys): continue
                m = int(wm) + 2
                y0, y1, x0, x1 = max(0, ys.min() - m), min(h2, ys.max() + m + 1), max(0, xs.min() - m), min(w2, xs.max() + m + 1)
                d = cv2.distanceTransform((gt[y0:y1, x0:x1] != i).astype(np.uint8), cv2.DIST_L2, 5)
            D1, L1, D2 = d1[y0:y1, x0:x1], l1[y0:y1, x0:x1], d2[y0:y1, x0:x1]
            better = d < D1
            D2[:] = np.where(better, D1, np.minimum(D2, d)); L1[:] = np.where(better, i, L1); D1[:] = np.where(better, d, D1)
        dec = (gt > 0) | (alpha2 & (d1 + d2 <= wm)); dec &= alpha2 | (gt > 0)
        os.makedirs(B.RUNS + 'cache', exist_ok=True); tmp = f[:-4] + f'.{os.getpid()}.tmp.png'; cv2.imwrite(tmp, dec.astype(np.uint8) * 255); os.replace(tmp, f)
        return dec
    def load_truth():
        rings = [np.array(b['ring'], float) for b in sm['blocks']]
        lines = [(np.array(l['a'], float), np.array(l['b'], float), l['kind']) for l in sm['lines']]
        gt = B.raster(rings); cen = np.array([B.poly_centroid(r) for r in rings]) if rings else np.zeros((0, 2))
        alpha2 = cv2.resize(np.load(SP + f'cufp/{plate}/png_alpha_s4.npy').astype(np.float32), (w2, h2)) > 0.5
        return dict(rings=rings, lines=lines, gt=gt, ng=len(rings), cen=cen, isA=is_a(cen[:, 0], cen[:, 1]) if len(cen) else np.zeros(0, bool), alpha2=alpha2, decided=decided_ground(gt, len(rings), alpha2))
    def picture(run, shown_ls, dp, ben, db, sh_ls, tol):
        sc = 0.25; im = cv2.resize(scan, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA); im = (im * 0.55 + 110).astype(np.uint8)
        def draw(ls, d, col_ok, col_bad, th):
            ok = d <= tol; q = (ls.P * sc).astype(int); q[:, 0] = np.clip(q[:, 0], 0, im.shape[1] - 1); q[:, 1] = np.clip(q[:, 1], 0, im.shape[0] - 1)
            for sel, col in ((ok, col_ok), (~ok, col_bad)):
                if col is None: continue
                for x, y in q[sel]: cv2.circle(im, (int(x), int(y)), th, col, -1)
        draw(ben, db, None, (255, 80, 0), 1); draw(sh_ls, np.zeros(len(sh_ls.P)), (150, 150, 150), None, 1); draw(shown_ls, dp, (0, 160, 0), (0, 0, 230), 1)
        if region_file:
            r = cv2.resize(M.astype(np.uint8), (im.shape[1], im.shape[0]), interpolation=cv2.INTER_NEAREST)
            cv2.drawContours(im, cv2.findContours(r, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0], -1, (200, 0, 200), 2)
        cv2.imwrite(run + f'{plate}_bench.jpg', im, [cv2.IMWRITE_JPEG_QUALITY, 85])
    B.is_a = is_a; B.load_truth = load_truth; B.decided_ground = decided_ground; B.picture = picture
    B.sheet = lambda n=None: ES.sheet(plate, W, H)
    return sm, M


def main():
    ap = argparse.ArgumentParser(description='bench44 on another plate (see the docstring)', allow_abbrev=False)
    ap.add_argument('--make-truth', nargs=2, metavar=('N', 'OUT'))
    ap.add_argument('--plate'); ap.add_argument('--truth'); ap.add_argument('--area'); ap.add_argument('--lines'); ap.add_argument('--region')
    ap.add_argument('--tag'); ap.add_argument('--runs'); ap.add_argument('--no-pic', action='store_true'); ap.add_argument('--reuse', action='store_true')
    a = ap.parse_args()
    if a.make_truth:
        print(json.dumps(make_truth(a.make_truth[0], a.make_truth[1]))); return
    for k in ('plate', 'truth', 'area', 'lines'):
        if not getattr(a, k): sys.exit(f'--{k} is needed')
    plate = a.plate.upper(); truth = os.path.abspath(a.truth); region = os.path.abspath(a.region) if a.region else None
    import bench44 as B
    t0 = time.time(); sm, M = setup(B, plate, truth, region)
    tag = a.tag or f'{plate}_' + os.path.basename(a.area)[:-4]
    argv = [B.__file__, '--area', os.path.abspath(a.area), '--lines', os.path.abspath(a.lines), '--tag', tag]
    if a.runs: argv += ['--runs', os.path.abspath(a.runs)]
    if a.no_pic: argv.append('--no-pic')
    if a.reuse: argv.append('--reuse')
    sys.argv = argv
    with contextlib.redirect_stdout(io.StringIO()): B.main()
    run = B.RUNS + f'{tag}/'; res = json.load(open(run + 'bench44.json', encoding='utf8'))
    T = B.load_truth(); inA = T['isA']
    res['meta'].update(plate=plate, truth=f'{truth} (sha256 {sha(truth)}; {len(sm["blocks"])} blocks, {len(sm["lines"])} lines)', truth_source=sm.get('source'), truth_saved_at=sm.get('source_saved_at'),
                       folds=(f'A: inside the region {region} (sha256 {sha(region)}), B: outside' if region else 'no region: every block and line in A'),
                       region=dict(file=region, share_of_plate=round(float(M.mean()), 4), truth_blocks_in=int(inA.sum()), truth_blocks_out=int((~inA).sum())),
                       wrapper=dict(file=os.path.abspath(__file__), sha256=sha(os.path.abspath(__file__)), bench44=B.__file__, bench44_sha256=sha(B.__file__)), wrapper_seconds=round(time.time() - t0, 1))
    res['region_headline'] = dict(region=res['headline']['A'], outside=res['headline']['B'], all=res['headline']['all'])
    json.dump(res, open(run + 'bench_plate.json', 'w', encoding='utf8', newline='\n'), indent=1)
    print(json.dumps(dict(tag=tag, run=run, region_blocks=int(inA.sum()), headline=res['region_headline'])))


if __name__ == '__main__':
    main()
