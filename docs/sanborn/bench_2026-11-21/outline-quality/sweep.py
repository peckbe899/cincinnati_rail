"""outline-quality: run many outline-step settings on plate 44 in-process and score them with the bench's own functions.

    python sweep.py NAME '{"markers": [true], "THR": [127, 160]}' [--base '{"gate": true}'] [--step4 default|green_only]
                    [--workers 3] [--area PNG] [--lines PNG]

Every combination of the grid (on top of --base) runs outlines_oq.outline() (the outline step, no files written), then
step 4, the editor's clean() + sheet(), and is scored as bench44.py scores (functions imported from bench44_copy.py, an
unchanged copy of the harness): PQ of the straightened outlines and of the watershed regions (all, fold A, fold B, and
on decided ground), line recall/precision of what the editor shows at 5 px / 20 deg, green and orange precision,
Ben blocks closed (faces of shown lines + sheet outline at snap 10 and 1.5 px, IoU >= 0.8), intact rings, and the
delete/draw workload. One json line per setting goes to sweeps/NAME.jsonl (settings already there are skipped).
A full bench run of a chosen setting: run_variant.py.
"""
import argparse, itertools, json, os, sys, time
import numpy as np, cv2
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/') + '/'
sys.path.insert(0, HERE)
import bench44_copy as B  # noqa: E402
import outlines_oq as O  # noqa: E402

G = {}


def step4_default(polys):
    return B.step4_default(polys)


def step4_green_only(polys):
    return [dict(src='read', name='', a=s['a'], b=s['b'], state='green') for p in polys for s in p if s['state'] == 'on print' and not s.get('paper_edge')]


def _drop(polys, test):
    return [dict(src='read', name='', a=s['a'], b=s['b'], state='green' if s['state'] == 'on print' else 'orange') for p in polys for s in p
            if s['state'] != 'short' and not s.get('paper_edge') and not test(s)]


def _len(s): return float(np.hypot(s['b'][0] - s['a'][0], s['b'][1] - s['a'][1]))


STEP4 = dict(default=step4_default, green_only=step4_green_only,
             drop_nol=lambda polys: _drop(polys, lambda s: s['state'] == 'not on a line'),                                  # 'not on a line' sides and bridges are not shown
             drop_nol_bridges=lambda polys: _drop(polys, lambda s: bool(s.get('bridge')) and s['state'] == 'not on a line'),
             drop_nol_bridges60=lambda polys: _drop(polys, lambda s: bool(s.get('bridge')) and s['state'] == 'not on a line' and _len(s) > 60),
             drop_nol_bridges120=lambda polys: _drop(polys, lambda s: bool(s.get('bridge')) and s['state'] == 'not on a line' and _len(s) > 120))


def init(area, lines):
    G['D'] = O.load('44', area, lines); G['T'] = B.load_truth(); G['ben'] = B.LineSet(G['T']['lines'], 20.0); G['SH'] = B.sheet()


def score(polys, inst, step4='default', tol=5.0, full=False):
    T, ben, SH = G['T'], G['ben'], G['SH']; out = {}
    rings = [np.array([s['a'] for s in p], float) for p in polys]; i2 = B.raster(rings)
    r, _ = B.pq(T, i2, len(rings)); rd, _ = B.pq(T, i2, len(rings), T['decided'])
    out['pq'] = {f: dict(PQ=r[f]['PQ'], SQ=r[f]['SQ'], RQ=r[f]['RQ'], matched=r[f]['matched'], fp=r[f]['fp'], merges=r[f]['merges'], lost_in_merges=r[f]['gt_lost_in_merges'], split=r[f]['gt_split'],
                     missed_other=r[f]['gt_missed_other'], pred=r[f]['pred'], PQ_decided=rd[f]['PQ'], fp_decided=rd[f]['fp']) for f in r}
    if inst is not None:
        h2, w2 = T['gt'].shape; i1 = cv2.resize(inst.astype(np.int32), (w2, h2), interpolation=cv2.INTER_NEAREST)
        u = np.unique(i1); u = u[u > 0]; lut = np.zeros(int(i1.max()) + 1, np.int32); lut[u] = np.arange(1, len(u) + 1); i1 = lut[i1]
        r1, _ = B.pq(T, i1, len(u)); out['pq_ws'] = {f: dict(PQ=r1[f]['PQ'], matched=r1[f]['matched'], fp=r1[f]['fp'], merges=r1[f]['merges']) for f in r1}
    edges = STEP4[step4](polys); shown = B.clean(edges)
    ls = B.LineSet([(e['a'], e['b'], e['state']) for e in shown], 20.0)
    sc, dp, db = B.line_scores(ls, ben, T, tol)
    out['lines'] = {f: {k: sc[f][k] for k in ('recall_interior', 'recall_printed', 'recall_drawn', 'precision', 'precision_green', 'precision_orange', 'shown_len', 'green_len', 'orange_len', 'recall_interior_decided', 'precision_decided')} for f in sc}
    for f in sc: out['lines'][f]['p8'] = sc[f]['tol_sensitivity']['8px']
    shs = [(s['a'], s['b']) for s in SH]
    out['closed'] = {}
    for snap in ((1.5, 10.0, 40.0) if full else (1.5, 10.0)):
        F = B.faces([(e['a'], e['b']) for e in shown] + shs, snap); fi = B.raster(F); rf, ious = B.pq(T, fi, len(F))
        out['closed'][f'snap{snap:g}'] = {f: int(((ious >= 0.8) & sel).sum()) for f, sel in (('all', np.ones(T['ng'], bool)), ('A', T['isA']), ('B', ~T['isA']))}
        out['closed'][f'snap{snap:g}_faces_PQ'] = rf['all']['PQ']
    kept = [all(s['state'] != 'short' and not s.get('paper_edge') for s in p) and all(np.hypot(*(np.array(p[k]['b']) - np.array(p[(k + 1) % len(p)]['a']))) <= 1.5 for k in range(len(p))) for p in polys]
    joined = [all(np.hypot(*(np.array(p[k]['b']) - np.array(p[(k + 1) % len(p)]['a']))) <= 1.5 for k in range(len(p))) for p in polys]
    out['rings'] = dict(outlines=len(polys), intact=int(sum(kept)), joined=int(sum(joined)))
    pl_sh = B.per_line(ls, dp, tol); pl_ben = B.per_line(ben, db, tol)
    mid = lambda items: np.array([(np.asarray(x[0]) + np.asarray(x[1])) / 2 for x in items]) if items else np.zeros((0, 2))
    msh, mben = mid(ls.items), mid(ben.items)
    Lsh = np.array([np.hypot(*(np.asarray(b) - np.asarray(a))) for a, b, _ in ls.items]); Lben = np.array([np.hypot(*(b - a)) for a, b, _ in ben.items])
    interior = np.array([k in ('printed', 'drawn') for _, _, k in ben.items])
    out['work'] = {}
    for f in ('all', 'A', 'B'):
        sel = lambda m: np.ones(len(m), bool) if f == 'all' else (B.is_a(m[:, 0], m[:, 1]) if f == 'A' else ~B.is_a(m[:, 0], m[:, 1]))
        ds = sel(msh) & (pl_sh < 0.5) if len(msh) else np.zeros(0, bool); dbn = sel(mben) & interior & (pl_ben < 0.5)
        out['work'][f] = dict(shown_lines=int(sel(msh).sum()) if len(msh) else 0, delete_n=int(ds.sum()), delete_len=round(float(Lsh[ds].sum())) if len(msh) else 0, draw_n=int(dbn.sum()), draw_len=round(float(Lben[dbn].sum())))
    return out, edges, shown


def job(P, step4):
    t0 = time.time(); polys, rep, _, block, inst = O.outline(G['D'], P, vis_out=False); t1 = time.time()
    if inst is None:
        n, cc = cv2.connectedComponents(block, connectivity=8); inst = cc
    s, _, _ = score(polys, inst, step4)
    return dict(P=P, step4=step4, rep=rep, mixed_pieces=G['D'].get('_mixed_pieces'), outline_s=round(t1 - t0, 1), score_s=round(time.time() - t1, 1), **s)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('name'); ap.add_argument('grid'); ap.add_argument('--base', default='{}'); ap.add_argument('--step4', default='default')
    ap.add_argument('--workers', type=int, default=3); ap.add_argument('--area', default=B.U + '44_pred_area_ng1.png'); ap.add_argument('--lines', default=B.U + '44_lines_lines_ng1.png')
    a = ap.parse_args(); grid = json.loads(a.grid); base = json.loads(a.base)
    keys = sorted(grid); combos = [dict(base, **dict(zip(keys, v))) for v in itertools.product(*[grid[k] for k in keys])]
    os.makedirs(HERE + 'sweeps', exist_ok=True); f = HERE + f'sweeps/{a.name}.jsonl'
    done = set()
    if os.path.exists(f):
        for l in open(f):
            r = json.loads(l); done.add((json.dumps(r['P'], sort_keys=True), r['step4']))
    todo = [P for P in combos if (json.dumps(P, sort_keys=True), a.step4) not in done]
    print(f'{len(combos)} settings, {len(todo)} to run', file=sys.stderr, flush=True)
    if a.workers <= 1:
        init(a.area, a.lines); it = (job(P, a.step4) for P in todo)
    else:
        import multiprocessing as mp
        pool = mp.Pool(a.workers, initializer=init, initargs=(a.area, a.lines)); it = pool.imap_unordered(_job, [(P, a.step4) for P in todo])
    for r in it:
        r['area_png'] = os.path.basename(a.area); r['lines_png'] = os.path.basename(a.lines)
        open(f, 'a').write(json.dumps(r) + '\n')
        print(json.dumps(dict(P=r['P'], PQ=[r['pq'][x]['PQ'] for x in ('all', 'A', 'B')], m=r['pq']['all']['matched'], fp=r['pq']['all']['fp'], R=r['lines']['all']['recall_interior'], Pr=r['lines']['all']['precision'],
                              cl10=r['closed']['snap10']['all'], cl1=r['closed']['snap1.5']['all'], s=r['outline_s'] + r['score_s'])), flush=True)


def _job(x): return job(*x)


if __name__ == '__main__':
    main()
