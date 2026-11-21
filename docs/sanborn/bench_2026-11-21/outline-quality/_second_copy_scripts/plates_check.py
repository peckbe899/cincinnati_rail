"""outline-quality: the chosen outline-step variant on cut batch plates, beside the batch (no truth there: indicators and
pictures only).

    python plates_check.py TAG '{"markers": true, ...}' [--step4 NAME] N [N ...]

For each plate: the outline step as the batch ran it (outlines_oq with no switches; checked against the batch's stored
picks22_guided/22-N/outlines.json) and the variant, both on the batch's own maps (unet_data/N_pred_area_ng1.png and
N_lines_lines_ng1.png). Each goes through step 4 (sweep.STEP4), the editor's clean() and the plate's sheet outline.
Indicators per plate: blocks, sides, bridges, editor lines and length, green share, closed faces (editor lines + sheet
outline polygonized at snap 1.5 and 10 px, faces >= 400 px2, and those of block size >= 20,000 px2), open line ends
(an end with no other line within 10 px), lines more than half on the rail bins (N_bins.png values 4, 5, within 6 px),
largest outline as a share of the paper, outlines under a quarter of the median, seconds.
Writes plates/TAG/N_*.jpg (batch left, variant right, 1/6 size; and a 1/2-size crop) and plates/TAG/summary.json.
"""
import argparse, json, os, sys, time
import numpy as np, cv2
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/') + '/'
sys.path.insert(0, HERE)
import outlines_oq as O  # noqa: E402
import sweep as S  # noqa: E402
B = S.B; SP = O.SP; U = O.U


def sheet(n, W, H):
    """edit_server.sheet (copied in bench44.py), with the plate's own size"""
    a = np.load(SP + f'cufp/{n}/png_alpha_s4.npy').astype(np.float32); m = (a > 0.5).astype(np.uint8)
    sx, sy = W / m.shape[1], H / m.shape[0]; out = []
    for c in cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)[0]:
        if cv2.contourArea(c) < 500: continue
        p = cv2.approxPolyDP(c, 2.0, True)[:, 0, :].astype(float) * [sx, sy]
        for k in range(len(p)):
            q0, q1 = p[k], p[(k + 1) % len(p)]
            if np.hypot(*(q1 - q0)) >= 40: out.append(dict(src='sheet', state='sheet', a=q0.round(1).tolist(), b=q1.round(1).tolist()))
    return out


def area2(r): r = np.asarray(r, float); return abs((r[:, 0] * np.roll(r[:, 1], -1) - np.roll(r[:, 0], -1) * r[:, 1]).sum()) / 2


def indicators(polys, shown, SH, D, rail):
    from shapely.geometry import LineString
    from shapely.strtree import STRtree
    segs = [(e['a'], e['b']) for e in shown]; L = np.array([np.hypot(*(np.subtract(b, a))) for a, b in segs]) if segs else np.zeros(0)
    res = dict(blocks=len(polys), sides=sum(1 for p in polys for s in p if s['state'] != 'short'), short=sum(1 for p in polys for s in p if s['state'] == 'short'),
               bridges=sum(1 for p in polys for s in p if s.get('bridge')), editor_lines=len(shown), editor_len=int(L.sum()),
               green_share=round(float(L[[e['state'] == 'green' for e in shown]].sum() / max(1, L.sum())), 3))
    for snap in (1.5, 10.0):
        F = B.faces(segs + [(s['a'], s['b']) for s in SH], snap); ar = np.array([area2(f) for f in F]) if F else np.zeros(0)
        res[f'faces_snap{snap:g}'] = len(F); res[f'block_faces_snap{snap:g}'] = int((ar >= 20000).sum())
    # open ends: an end with no other editor line or sheet line within 10 px
    geoms = [LineString(s) for s in segs] + [LineString([s['a'], s['b']]) for s in SH]; tree = STRtree(geoms); op = 0
    from shapely.geometry import Point
    for i, (a, b) in enumerate(segs):
        for p in (a, b):
            pt = Point(p); near = [j for j in tree.query(pt.buffer(10.0)) if j != i and geoms[j].distance(pt) <= 10.0]
            op += not near
    res['open_ends'] = op; res['open_ends_per_line'] = round(op / max(1, len(segs)), 2)
    if rail is not None and segs:
        H, W = rail.shape; on = []
        for a, b in segs:
            a, b = np.array(a, float), np.array(b, float); t = np.linspace(0, 1, max(5, int(np.hypot(*(b - a)) / 3))); q = a + np.outer(t, b - a)
            on.append(rail[np.clip(q[:, 1].round().astype(int), 0, H - 1), np.clip(q[:, 0].round().astype(int), 0, W - 1)].mean())
        on = np.array(on); res['rail_lines'] = int((on > 0.5).sum()); res['rail_len'] = int(L[on > 0.5].sum())
    ar = np.array([area2([s['a'] for s in p]) for p in polys]) if polys else np.zeros(0); paper = float(D['alpha'].sum())
    res['largest_share'] = round(float(ar.max() / paper), 3) if len(ar) else 0.0
    res['small_outlines'] = int((ar < 0.25 * np.median(ar)).sum()) if len(ar) else 0
    return res


def draw(D, polys, shown, sc):
    im = cv2.resize(D['full'], None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA); im = (im * 0.55 + 110).astype(np.uint8)
    P = lambda p: tuple((np.array(p, float) * sc).round().astype(int))
    for p in polys:
        for s in p:
            if s['state'] == 'short' or s.get('paper_edge'): cv2.line(im, P(s['a']), P(s['b']), (150, 150, 150), 1, cv2.LINE_AA)
    for e in shown:
        cv2.line(im, P(e['a']), P(e['b']), (0, 150, 0) if e['state'] == 'green' else (0, 130, 255), 2 if sc >= 0.3 else 1, cv2.LINE_AA)
    for p in polys:
        for s in p:
            if s.get('bridge') and not s.get('paper_edge'): cv2.circle(im, P((np.array(s['a']) + np.array(s['b'])) / 2), 3 if sc >= 0.3 else 2, (230, 200, 0), -1)
    return im


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('tag'); ap.add_argument('params'); ap.add_argument('plates', nargs='+'); ap.add_argument('--step4', default='default')
    ap.add_argument('--crop', default=None, help='N:x0,y0,x1,y1;...')
    a = ap.parse_args(); P = json.loads(a.params); out = HERE + f'plates/{a.tag}/'; os.makedirs(out, exist_ok=True)
    crops = {k: [int(v) for v in c.split(',')] for k, c in (x.split(':') for x in a.crop.split(';'))} if a.crop else {}
    summ = json.load(open(out + 'summary.json')) if os.path.exists(out + 'summary.json') else {}
    for N in a.plates:
        t0 = time.time(); D = O.load(N, U + f'{N}_pred_area_ng1.png', U + f'{N}_lines_lines_ng1.png'); H, W = D['H'], D['W']
        bins = cv2.imread(U + f'{N}_bins.png', cv2.IMREAD_UNCHANGED)
        rail = (cv2.dilate(np.isin(bins, (4, 5)).astype(np.uint8), np.ones((13, 13), np.uint8)) > 0) if bins is not None else None
        SH = sheet(N, W, H); row = dict(params=P, step4=a.step4)
        res = {}
        for name, PP, st4 in (('batch', {}, 'default'), ('variant', P, a.step4)):
            t1 = time.time(); polys, rep, _, block, inst = O.outline(D, PP, vis_out=False); dt = round(time.time() - t1, 1)
            if name == 'batch':
                ref = SP + f'picks22_guided/22-{N}/outlines.json'
                row['batch_reproduced'] = os.path.exists(ref) and json.dumps(polys) == json.dumps(json.load(open(ref, encoding='utf8')))
            edges = S.STEP4[st4](polys); shown = B.clean(edges)
            row[name] = dict(indicators(polys, shown, SH, D, rail), outline_seconds=dt, share_on_printed_line_by_length=rep['share_on_printed_line_by_length'])
            res[name] = (polys, shown)
            json.dump(polys, open(out + f'{N}_{name}_outlines.json', 'w')); json.dump(shown, open(out + f'{N}_{name}_shown.json', 'w'))
        sc = 1 / 6
        l_, r_ = draw(D, *res['batch'], sc), draw(D, *res['variant'], sc)
        im = np.hstack([l_, np.full((l_.shape[0], 6, 3), 255, np.uint8), r_])
        cv2.imwrite(out + f'{N}_side_by_side.jpg', im, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if N in crops:
            x0, y0, x1, y1 = crops[N]; Dc = dict(full=D['full'][y0:y1, x0:x1])
            sh = lambda pl, sv: ([[dict(s, a=[s['a'][0] - x0, s['a'][1] - y0], b=[s['b'][0] - x0, s['b'][1] - y0]) for s in p] for p in pl], [dict(e, a=[e['a'][0] - x0, e['a'][1] - y0], b=[e['b'][0] - x0, e['b'][1] - y0]) for e in sv])
            l_, r_ = draw(Dc, *sh(*res['batch']), 0.4), draw(Dc, *sh(*res['variant']), 0.4)
            cv2.imwrite(out + f'{N}_crop.jpg', np.vstack([l_, np.full((6, l_.shape[1], 3), 255, np.uint8), r_]), [cv2.IMWRITE_JPEG_QUALITY, 85])
        row['seconds'] = round(time.time() - t0, 1); summ[N] = row
        print(N, json.dumps(row), flush=True)
        json.dump(summ, open(out + 'summary.json', 'w'), indent=1)
        del D


if __name__ == '__main__':
    main()
