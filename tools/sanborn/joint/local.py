"""Local fit of plates 22-33, 22-34R, 22-37L, 22-37R and 22-38 (Ben, 6 November 2026: option (c) for these five).

    cd data/sanborn
    python ../../tools/sanborn/joint/local.py [--write]      (without --write: report only, no model files)

Model, per fitted plate p: new(px) = P + d_p(P), P = F_p(px), F_p the plate's own model as stored (cufp/33/fwd.pkl,
cuf_cw/<half>/fwd.pkl, cuf38/fwd38.pkl). d_p is a world-space correction: affine [1, u, v] (u, v in km about the plate's
control centre) plus, if chosen, a thin-plate spline (kernel r2 log r, r in units of 100 m) with centres at the plate's
controls, its tie crossings and (37L, 37R) every third gutter pair, and a bending penalty lambda (the smoothing of
scipy's RBFInterpolator: tps0.3 ... tps100). Per plate, affine or tps<lambda> is chosen by held-out error on the plate's
own controls (coordinate descent from all affine, two passes), as the single-plate fits chose their models.

Data, solved together:
- own controls: the OSM crossings each plate's fit kept (fwd.pkl X -> O), weight 1;
- ties: every crossing a fitted plate shares with another plate (tools/sanborn/seams.py matching on the plates' own
  models, old picks, within 45 m; the wrong name matches of reports/2026-11-06_seams_reread dropped). Between two fitted
  plates both move; with one of the other 16 plates, that plate is held fixed (its own model). Huber weights, k = 6 m;
- 37L and 37R as one sheet where they overlap at the gutter: their shared picks, and 206 paper-point pairs matched
  between the two scans across the overlap (data/sanborn/cuf_cw/overlap_37L_37R.json, made by overlap_pairs() below),
  must map to one point: weight 25 (an error of 1 m there counts as 5 m on a control), not Huber.
Held-out error: each own control left out in turn, the plate's own model refitted without it (fwdlib.make, the stored
model kind) and the correction downdated exactly (penalised least squares, the other rows held).

Writes data/sanborn/reports/<date>_local/ (README.md, plates.csv, ties.csv, solve.json), and with --write each fitted
plate's new model beside its old one (fwd_local.pkl, cuf38/fwd38_local.pkl) and the seam report on the new models
(reports/<date>_seams_local). Nothing else; nothing is applied.
"""
import csv, datetime, json, os, pickle, sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.dirname(HERE))
import _ws  # noqa: E402
import jointlib as J  # noqa: E402
import seams as S  # noqa: E402
import importlib.util  # noqa: E402
_spec = importlib.util.spec_from_file_location('joint_solve', os.path.join(HERE, 'solve.py'))   # not sbg/fit/solve.py, which seams puts first on the path
SV = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(SV)

SP = _ws.DATA
FIT = ['22-33', '22-34R', '22-37L', '22-37R', '22-38']
SCALE, U, HUBER, W_SHEET, PASSES = 1000.0, 100.0, 6.0, 25.0, 2
KINDS = ['affine', 'tps0.3', 'tps1', 'tps3', 'tps10', 'tps30', 'tps100']
OVERLAP = 'cuf_cw/overlap_37L_37R.json'


def overlap_pairs():
    """paper points seen on both 37R and 37L across the gutter: 150 px templates of 37R matched in 37L (score > 0.8),
    outliers more than 6 px from a quadratic 37R -> 37L map dropped. Cached in data/sanborn/cuf_cw/."""
    if os.path.exists(SP + OVERLAP):
        return json.load(open(SP + OVERLAP, encoding='utf8'))
    import cv2
    sys.path.insert(0, _ws.CODE + 'sbg')
    from sb import find
    L = cv2.imread(find('22-37L'), cv2.IMREAD_GRAYSCALE); R = cv2.imread(find('22-37R'), cv2.IMREAD_GRAYSCALE)
    M = []
    for y in range(150, 7650, 100):
        for x in range(150, 620, 80):
            t = R[y:y + 150, x:x + 150].astype(np.float32)
            if t.std() < 12:
                continue
            x0 = int(5622.6 + 0.9754 * x + 0.00463 * y - 120); y0 = max(0, y - 120)
            s = L[y0:y + 270, x0:min(L.shape[1], x0 + 390)].astype(np.float32)
            if s.shape[1] < 160 or s.shape[0] < 160:
                continue
            r = cv2.matchTemplate(s, t, cv2.TM_CCOEFF_NORMED); _, mx, _, loc = cv2.minMaxLoc(r)
            if mx > 0.8:
                M.append((x + 75, y + 75, loc[0] + x0 + 75, loc[1] + y0 + 75, mx))
    M = np.array(M)
    Q = lambda a: np.c_[np.ones(len(a)), a[:, 0] / 1000, a[:, 1] / 1000, (a[:, 0] / 1000) ** 2, a[:, 0] * a[:, 1] / 1e6, (a[:, 1] / 1000) ** 2]
    keep = np.ones(len(M), bool)
    for _ in range(4):
        cx, *_ = np.linalg.lstsq(Q(M[keep]), M[keep, 2], rcond=None); cy, *_ = np.linalg.lstsq(Q(M[keep]), M[keep, 3], rcond=None)
        keep = np.hypot(Q(M) @ cx - M[:, 2], Q(M) @ cy - M[:, 3]) < 6
    K = M[keep]
    d = dict(note='37R px (x, y) -> 37L px (x, y): 150 px templates of 37R matched in 37L (score > 0.8), outliers > 6 px from a quadratic dropped; tools/sanborn/joint/local.py overlap_pairs()',
             pairs=[[round(float(a), 1) for a in r[:4]] for r in K], score=[round(float(r[4]), 3) for r in K])
    json.dump(d, open(SP + OVERLAP, 'w', encoding='utf8', newline='\n'), indent=0)
    return d


def dropped_ties():
    """wrong name matches found by the re-read (latest verdict per tie)"""
    f = SP + 'reports/2026-11-06_seams_reread/verdicts.json'
    if not os.path.exists(f):
        return set()
    last = {}
    for v in json.load(open(f, encoding='utf8')):
        last[v['n']] = v
    out = set()
    for v in last.values():
        if v['verdict'] == 'b':
            a, b = v['tie'].split(' / '); st = v['crossing'].split(' & ')
            out.add((a, b, S.k2(*st))); out.add((b, a, S.k2(*st)))
    return out


class Local:
    def __init__(self, C, ties, sheet):
        self.C, self.ties, self.sheet = C, ties, sheet
        self.center = {p: C[p]['O'].mean(0) for p in FIT}
        cen = {p: [C[p]['P']] for p in FIT}
        for t in ties:
            for side in ('a', 'b'):
                if t[side] in FIT:
                    cen[t[side]].append(t['P' + side][None])
        for i, s in enumerate(sheet):
            if i % 3 == 0:
                cen['22-37L'].append(s['PL'][None]); cen['22-37R'].append(s['PR'][None])
        self.cent = {}
        for p in FIT:
            c = np.vstack(cen[p]); keep = []
            for q in c:
                if all(np.hypot(*(q - k)) > 1.0 for k in keep):
                    keep.append(q)
            c = np.array(keep); self.cent[p] = c
            Cm = np.c_[np.ones(len(c)), (c - self.center[p]) / SCALE]
            u, s_, vt = np.linalg.svd(Cm.T)          # null space of C^T: TPS side conditions
            self.__dict__.setdefault('Nsp', {})[p] = vt[3:].T
            self.__dict__.setdefault('Kcc', {})[p] = J.tps_kernel(c, c, U)

    def ncol(self, p, kind):
        return 3 + (self.Nsp[p].shape[1] if kind != 'affine' else 0)

    def B(self, p, P, kind):
        P = np.atleast_2d(P)
        b = J.basis(P, self.center[p], SCALE, 'affine')
        if kind == 'affine':
            return b
        return np.c_[b, J.tps_kernel(P, self.cent[p], U) @ self.Nsp[p]]

    def solve(self, kinds):
        off, m = {}, 0
        for p in FIT:
            off[p] = m; m += self.ncol(p, kinds[p])
        S_ = np.zeros((m, m))
        for p in FIT:
            if kinds[p] != 'affine':
                lam = float(kinds[p][3:]); o = off[p] + 3; n = self.Nsp[p]
                S_[o:o + n.shape[1], o:o + n.shape[1]] = lam * n.T @ self.Kcc[p] @ n
        tw = np.ones(len(self.ties))
        for _ in range(10):
            rows, Y, W, tag = [], [], [], []
            for p in FIT:
                c = self.C[p]; Bm = self.B(p, c['P'], kinds[p])
                for i in range(len(Bm)):
                    r = np.zeros(m); r[off[p]:off[p] + Bm.shape[1]] = Bm[i]
                    rows.append(r); Y.append(c['O'][i] - c['P'][i]); W.append(1.0); tag.append(('c', p, i))
            for k, t in enumerate(self.ties):
                r = np.zeros(m); y = t['Pb'] - t['Pa']
                if t['a'] in FIT:
                    ba = self.B(t['a'], t['Pa'], kinds[t['a']])[0]; r[off[t['a']]:off[t['a']] + len(ba)] = ba
                if t['b'] in FIT:
                    bb = self.B(t['b'], t['Pb'], kinds[t['b']])[0]; r[off[t['b']]:off[t['b']] + len(bb)] -= bb
                rows.append(r); Y.append(y); W.append(t['w'] if t['sheet'] else tw[k]); tag.append(('t', k, None))
            for k, s in enumerate(self.sheet):
                r = np.zeros(m)
                bl = self.B('22-37L', s['PL'], kinds['22-37L'])[0]; br = self.B('22-37R', s['PR'], kinds['22-37R'])[0]
                r[off['22-37L']:off['22-37L'] + len(bl)] = bl; r[off['22-37R']:off['22-37R'] + len(br)] -= br
                rows.append(r); Y.append(s['PR'] - s['PL']); W.append(W_SHEET); tag.append(('s', k, None))
            A, Y, W = np.array(rows), np.array(Y), np.array(W)
            Aw = A * W[:, None]; Ninv = np.linalg.inv(A.T @ Aw + S_ + 1e-9 * np.eye(m))
            th = Ninv @ (Aw.T @ Y); R = Y - A @ th
            it = [j for j, t in enumerate(tag) if t[0] == 't']
            rt = np.hypot(*R[it].T)
            new = np.where(rt <= HUBER, 1.0, HUBER / np.maximum(rt, 1e-9))
            if np.allclose(new, tw, atol=1e-4):
                break
            tw = new
        return dict(A=A, Y=Y, W=W, tag=tag, off=off, Ninv=Ninv, th=th, R=R, tw=tw, kinds=dict(kinds))

    def coef(self, sol, p):
        o = sol['off'][p]; return sol['th'][o:o + self.ncol(p, sol['kinds'][p])]

    def corr(self, sol, p, P):
        if p not in FIT:
            return np.zeros_like(np.atleast_2d(P))
        return self.B(p, P, sol['kinds'][p]) @ self.coef(sol, p)

    def heldout(self, sol, p):
        A, W, R, Ninv, th = sol['A'], sol['W'], sol['R'], sol['Ninv'], sol['th']
        c = self.C[p]; o = sol['off'][p]; k = self.ncol(p, sol['kinds'][p]); errs = []
        idx = [r for r, t in enumerate(sol['tag']) if t[0] == 'c' and t[1] == p]
        for i, r in enumerate(idx):
            a = A[r]; h = W[r] * a @ Ninv @ a
            th_i = th - np.outer(Ninv @ a, W[r] * R[r] / (1 - h))
            Pl = c['Pl'][i]
            pred = Pl + self.B(p, Pl, sol['kinds'][p])[0] @ th_i[o:o + k]
            errs.append(np.hypot(*(pred - c['O'][i])))
        return float(np.sqrt(np.mean(np.square(errs))))

    def model_dict(self, sol, p):
        th = self.coef(sol, p); kind = sol['kinds'][p]
        d = dict(model='local', kind=kind, plate=p, center=[float(v) for v in self.center[p]], scale=SCALE, U=U,
                 coefE=th[:3, 0].tolist(), coefN=th[:3, 1].tolist(), centers=None, wE=None, wN=None)
        if kind != 'affine':
            w = self.Nsp[p] @ th[3:]
            d.update(centers=self.cent[p].tolist(), wE=w[:, 0].tolist(), wN=w[:, 1].tolist())
        return d


def seam_stats(rows, five):
    def st(g):
        d = np.array([r['dist_m'] for r in g])
        return dict(n=len(g), median=round(float(np.median(d)), 2), p90=round(float(np.percentile(d, 90)), 2), max=round(float(d.max()), 2),
                    over_10m=int((d > 10).sum()), over_20m=int((d > 20).sum())) if len(g) else dict(n=0)
    pp = [r for r in rows if r['within_45m'] and r['seam'] == 'plate-plate']
    return dict(touching=st([r for r in pp if r['a_src'] in five or r['b_src'] in five]),
                within=st([r for r in pp if r['a_src'] in five and r['b_src'] in five]),
                all=st(pp),
                plate_1904_touching=st([r for r in rows if r['within_45m'] and r['seam'] == 'plate-1904' and r['a_src'] in five]))


def main():
    write = '--write' in sys.argv
    today = datetime.date.today().isoformat()
    out = SP + f'reports/{today}_local'; os.makedirs(out, exist_ok=True)
    C = {}
    for p in FIT:
        X, O, P, Pl, names, model = SV.controls(p)
        C[p] = dict(X=X, O=O, P=P, Pl=Pl, model=model)
    recs = []
    for p in S.plate_ids():
        recs += S.plate_crossings(p)[0]
    near, _ = S.pairs(recs)
    drop = dropped_ties()
    ties = []
    for i, j, d in near:
        a, b = recs[i], recs[j]
        if b['kind'] != 'plate' or not (a['src'] in FIT or b['src'] in FIT) or (a['src'], b['src'], a['k']) in drop:
            continue
        sheet = {a['src'], b['src']} == {'22-37L', '22-37R'}
        ties.append(dict(a=a['src'], b=b['src'], Pa=np.array([a['E'], a['N']]), Pb=np.array([b['E'], b['N']]),
                         street_1=a['a'], street_2=a['b'], before_m=round(d, 2), sheet=sheet, w=W_SHEET if sheet else 1.0))
    ov = overlap_pairs()
    pr = np.array([q[:2] for q in ov['pairs']]); pl = np.array([q[2:] for q in ov['pairs']])
    PR = J.base_many('22-37R', pr); PL = J.base_many('22-37L', pl)
    sheet = [dict(PL=PL[i], PR=PR[i]) for i in range(len(pr))]
    gap0 = np.hypot(*(PL - PR).T)
    print('ties', len(ties), '(sheet', sum(t['sheet'] for t in ties), ') gutter pairs', len(sheet), 'gap before median %.1f max %.1f m' % (np.median(gap0), gap0.max()), flush=True)
    L = Local(C, ties, sheet)
    kinds = {p: 'affine' for p in FIT}
    sol = L.solve(kinds); ho = {p: L.heldout(sol, p) for p in FIT}; trail = []
    for ps in range(PASSES):
        for p in FIT:
            best = (ho[p], kinds[p], sol)
            for k in KINDS:
                if k == kinds[p]:
                    continue
                alt = dict(kinds); alt[p] = k; s2 = L.solve(alt); h2 = L.heldout(s2, p)
                if h2 < best[0] - 1e-6:
                    best = (h2, k, s2)
            if best[1] != kinds[p]:
                trail.append(dict(pass_=ps + 1, plate=p, frm=kinds[p], to=best[1], heldout=round(best[0], 3)))
                kinds = dict(kinds); kinds[p] = best[1]; sol = best[2]; ho = {q: L.heldout(sol, q) for q in FIT}
        print('pass', ps + 1, kinds, {p: round(v, 2) for p, v in ho.items()}, flush=True)
    rows = []
    for p in FIT:
        c = C[p]; before = np.hypot(*(c['P'] - c['O']).T); dc = L.corr(sol, p, c['P']); after = np.hypot(*(c['P'] + dc - c['O']).T)
        w, h = SV.plate_size(p); corners = np.array([[0, 0], [w, 0], [w, h], [0, h]], float)
        mv = np.hypot(*L.corr(sol, p, J.base_many(p, corners)).T)
        ob = SV.old_heldout(p, c['model'])
        rows.append(dict(plate=p, base_model=c['model'], correction=kinds[p], controls=len(c['O']),
                         rms_before=round(float(np.sqrt((before ** 2).mean())), 2), rms_after=round(float(np.sqrt((after ** 2).mean())), 2),
                         heldout_before=round(ob, 2), heldout_after=round(ho[p], 2), max_corner_move_m=round(float(mv.max()), 2),
                         median_control_move_m=round(float(np.median(np.hypot(*dc.T))), 2),
                         ties=sum(1 for t in ties if p in (t['a'], t['b'])), image_px=f'{w}x{h}'))
        rows[-1]['rms_change'] = round(rows[-1]['rms_after'] - rows[-1]['rms_before'], 2)
    tinfo = []
    for k, t in enumerate(ties):
        na = t['Pa'] + L.corr(sol, t['a'], t['Pa'])[0]; nb = t['Pb'] + L.corr(sol, t['b'], t['Pb'])[0]
        tinfo.append(dict(a=t['a'], b=t['b'], street_1=t['street_1'], street_2=t['street_2'], before_m=t['before_m'],
                          after_m=round(float(np.hypot(*(nb - na))), 2), weight=round(float(t['w'] if t['sheet'] else sol['tw'][k]), 3), sheet=t['sheet']))
    gap1 = np.hypot(*(PL + L.corr(sol, '22-37L', PL) - PR - L.corr(sol, '22-37R', PR)).T)
    summary = dict(plates=FIT, kinds=kinds, ties=len(ties), gutter_pairs=len(sheet),
                   gutter_gap_before=dict(median=round(float(np.median(gap0)), 2), max=round(float(gap0.max()), 2)),
                   gutter_gap_after=dict(median=round(float(np.median(gap1)), 2), max=round(float(gap1.max()), 2)),
                   worse_by_more_than_0_3m=[r['plate'] for r in rows if r['rms_change'] > 0.3])
    import scipy
    meta = dict(made=datetime.datetime.now().isoformat(timespec='seconds'), by='tools/sanborn/joint/local.py', U_m=U, scale_m=SCALE, huber_m=HUBER,
                sheet_weight=W_SHEET, kinds_tried=KINDS, choice_trail=trail, versions=dict(numpy=np.__version__, scipy=scipy.__version__),
                bases={p: dict(path=J.base_path(p), sha256=SV.sha(J.base_path(p))) for p in FIT}, overlap=OVERLAP)
    if write:
        for p in FIT:
            jp = J.joint_path(p, 'local'); assert jp != J.base_path(p)
            d = L.model_dict(sol, p); d.update(base=J.base_path(p), base_sha256=SV.sha(J.base_path(p)), solve=os.path.relpath(out, SP).replace('\\', '/'), made=meta['made'])
            pickle.dump(d, open(SP + jp, 'wb'))
        S.READ.clear()
        seam_dir = SP + f'reports/{today}_seams_local'
        S.main(['--models', 'local', seam_dir])
        after = json.load(open(seam_dir + '/seams.json', encoding='utf8'))['seams']
        before = json.load(open(SP + 'reports/2026-11-06_seams/seams.json', encoding='utf8'))['seams']
        drop_rows = lambda R_: [r for r in R_ if (r['a_src'], r['b_src'], S.k2(r['street_1'], r['street_2'])) not in drop]
        sb, sa = seam_stats(drop_rows(before), FIT), seam_stats(drop_rows(after), FIT)
        worse = summary['worse_by_more_than_0_3m']
        verdict = dict(worse_plates=worse, median_falls=sa['touching']['median'] < sb['touching']['median'],
                       p90_falls=sa['touching']['p90'] < sb['touching']['p90'])
        verdict['apply'] = not worse and verdict['median_falls'] and verdict['p90_falls']
        summary.update(seams_before=sb, seams_after=sa, part3_check=verdict, seam_report=os.path.relpath(seam_dir, SP).replace('\\', '/'))
    json.dump(dict(meta=meta, summary=summary, plates=rows, ties=tinfo), open(out + '/solve.json', 'w', encoding='utf8', newline='\n'), indent=1)
    for name, data in (('plates.csv', rows), ('ties.csv', tinfo)):
        with open(out + '/' + name, 'w', newline='', encoding='utf8') as f:
            wr = csv.DictWriter(f, fieldnames=list(data[0]), lineterminator='\n'); wr.writeheader(); wr.writerows(data)
    if write:
        write_readme(out, meta, summary, rows, tinfo)
    print(json.dumps({k: v for k, v in summary.items()}, indent=1, default=str))
    for r in rows:
        print(r)


def write_readme(out, meta, summary, rows, tinfo):
    v = summary['part3_check']; sb, sa = summary['seams_before'], summary['seams_after']
    L = [f"# Local fit of plates 33, 34R, 37L, 37R and 38, {meta['made'][:10]}", '',
         "Ben's ruling (6 November): option (c) for these five plates. Their positions are refitted together, the other 16 plates held "
         'fixed as tie partners, 37L and 37R treated as one sheet at the gutter. Nothing is applied by this report: the new models sit '
         'beside the old ones (`fwd_local.pkl`, `cuf38/fwd38_local.pkl`). Method: `tools/sanborn/joint/local.py` (its docstring).', '',
         f"{summary['ties']} ties ({sum(t['sheet'] for t in tinfo)} of them 37L/37R paper points), {summary['gutter_pairs']} gutter pairs matched between the "
         f"37L and 37R scans. The gutter gap between the halves (the same paper point on both): median {summary['gutter_gap_before']['median']} m, "
         f"max {summary['gutter_gap_before']['max']} m before; median {summary['gutter_gap_after']['median']} m, max {summary['gutter_gap_after']['max']} m after.", '',
         '## Part 3 check', '',
         f"- Every plate's own control rms within 0.3 m of before: **{'yes' if not v['worse_plates'] else 'no'}**" + (f" (worse: {', '.join(v['worse_plates'])})" if v['worse_plates'] else ''),
         f"- Plate-plate seam median across the five falls: **{'yes' if v['median_falls'] else 'no'}** ({sb['touching']['median']} to {sa['touching']['median']} m)",
         f"- Plate-plate seam 90% across the five falls: **{'yes' if v['p90_falls'] else 'no'}** ({sb['touching']['p90']} to {sa['touching']['p90']} m)",
         f"- So Part 3 {'goes ahead' if v['apply'] else '**does not** go ahead (stop after Part 2)'}.", '',
         '"Across the five": every plate-plate seam a fitted plate takes part in (with another of the five or with a fixed plate). '
         "The wrong name matches of the re-read are left out of both before and after.", '',
         '## Per plate', '',
         'Controls: the plate\'s own OSM crossings. Rms: own controls, m. Held-out: leave-one-out rms (before: the plate\'s fit report). '
         'Corner move: largest move of the plate image\'s four corners.', '',
         '| Plate | Own model | Correction | Controls | Rms before | Rms after | Change | Held-out before | Held-out after | Max corner move m | Median control move m | Ties |',
         '|---|---|---|---|---|---|---|---|---|---|---|---|']
    for r in rows:
        L.append(f"| {r['plate']} | {r['base_model']} | {r['correction']} | {r['controls']} | {r['rms_before']} | {r['rms_after']} | "
                 f"{r['rms_change']:+.2f}{' **worse**' if r['rms_change'] > 0.3 else ''} | {r['heldout_before']} | {r['heldout_after']} | "
                 f"{r['max_corner_move_m']} | {r['median_control_move_m']} | {r['ties']} |")
    L += ['', '## Seams', '', f"Seam report on the new models (the five on `fwd_local`, the others on their own): `{summary['seam_report']}/`.", '',
          '| Plate-plate seams | | Shared | Median m | 90% m | Max m | > 10 m | > 20 m |', '|---|---|---|---|---|---|---|---|']
    for key, lab in (('touching', 'touching the five'), ('within', 'among the five'), ('all', 'all plates')):
        for when, d in (('before', sb[key]), ('after', sa[key])):
            L.append(f"| {lab} | {when} | {d['n']} | {d.get('median', '')} | {d.get('p90', '')} | {d.get('max', '')} | {d.get('over_10m', '')} | {d.get('over_20m', '')} |")
    for when, d in (('before', sb['plate_1904_touching']), ('after', sa['plate_1904_touching'])):
        L.append(f"| plate-1904, the five | {when} | {d['n']} | {d.get('median', '')} | {d.get('p90', '')} | {d.get('max', '')} | {d.get('over_10m', '')} | {d.get('over_20m', '')} |")
    L += ['', 'The 1904 frames have not moved (their bend is Part 3), so the plate-1904 seams of the five open where the plates move.', '',
          '## Ties, widest after the fit', '', '| Plates | Crossing | Before m | After m | Weight |', '|---|---|---|---|---|']
    for t in sorted(tinfo, key=lambda t: -t['after_m'])[:15]:
        L.append(f"| {t['a']} / {t['b']} | {t['street_1']} & {t['street_2']} | {t['before_m']} | {t['after_m']} | {t['weight']}{' (sheet)' if t['sheet'] else ''} |")
    L += ['', f"Choice trail: {meta['choice_trail'] or 'no change from affine'}. Computed with numpy {meta['versions']['numpy']}, scipy {meta['versions']['scipy']}.", '']
    open(out + '/README.md', 'w', encoding='utf8', newline='\n').write('\n'.join(L))


if __name__ == '__main__':
    main()
