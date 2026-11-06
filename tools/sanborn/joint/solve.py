"""Joint refit of the 1922 plates' positions (Ben, 6 November 2026): one solve for every plate on the 1922 layer.

    cd data/sanborn
    python ../../tools/sanborn/joint/solve.py [--write]      (without --write: report only, no model files)

Model, per plate p: new(px) = P + d_p(P), P = F_p(px). F_p is the plate's own model as stored (cufp/<N>/fwd.pkl,
cuf_cw/<half>/fwd.pkl, cuf38/fwd38.pkl; 22-35N Ben's georeference as drawn). d_p is a world-space correction in
u = (E - cE) / 1000, v = (N - cN) / 1000 about the plate's control centre: affine [1, u, v] or affine plus quadratic
[1, u, v, u2, uv, v2], each for E and N. So the joint solve moves each plate (its position, scale, turn and shear, plus a
gentle bend with the quadratic) and keeps its own fitted shape.

Data:
- own controls: the OSM crossings the plate's fit kept (fwd.pkl X -> O; 22-35N: the 30 checked crossings of
  cuf/corr.pkl, B -> O), weight 1;
- ties: the crossings two plates share (tools/sanborn/seams.py matching: street names, within 45 m, nearest one to
  one), new_a(px_a) = new_b(px_b), Huber weights (k = 6 m, iterated).
The 1904 frames and their bend are not used and not changed.

Choice per plate (affine or quadratic): the one with the lower held-out error on the plate's own controls, by
coordinate descent from all affine (two passes). Held-out error, as the single-plate fits' leave-one-out: each control
left out in turn, the plate's own model refitted without it (fwdlib.make with the stored model kind), and the joint
correction without it (exact downdate of the weighted least-squares solve; the other rows keep their positions).

Writes data/sanborn/reports/<date>_joint/ (README.md, plates.csv, ties.csv, solve.json) and, with --write, each plate's
new model beside its old one (tools/sanborn/joint/jointlib.py joint_path). Nothing else.
"""
import csv, datetime, hashlib, json, os, pickle, sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.dirname(HERE))
import _ws  # noqa: E402
import jointlib as J  # noqa: E402
import seams as S  # noqa: E402

SP = _ws.DATA
SCALE, HUBER, PASSES = 1000.0, 6.0, 2


def sha(rel):
    return hashlib.sha256(open(SP + rel, 'rb').read()).hexdigest()


# ------------------------------------------------------------------ data
def controls(pid):
    """own controls: pixel X, OSM O, the base model's position P = F(X), and P_loo = F without that control (at X)"""
    if pid == '22-35N':
        import common as C
        d = pickle.load(open(SP + 'cuf/corr.pkl', 'rb'))
        B, O = np.asarray(d['B'], float), np.asarray(d['O'], float)
        x, y = C.ben2px(B[:, 0], B[:, 1]); X = np.c_[x, y]
        P = J.base_many(pid, X)
        return X, O, P, P.copy(), [str(s) for s in d['names']], 'Ben georeference (nothing fitted)'
    d = pickle.load(open(SP + J.base_path(pid), 'rb'))
    X, O, model = np.asarray(d['X'], float), np.asarray(d['O'], float), d['model']
    P = J.base_many(pid, X)
    import fwdlib
    Pl = np.zeros_like(P)
    for i in range(len(X)):
        m = np.ones(len(X), bool); m[i] = False
        Pl[i] = fwdlib.make(model, X[m], O[m])(X[i:i + 1])[0]
    return X, O, P, Pl, [''] * len(X), model


def old_heldout(pid, model):
    if pid == '22-35N':
        return None   # nothing fitted: held-out = own rms
    if pid == '22-38':
        r = json.load(open(SP + 'cuf38/fit38_report.json'))
    else:
        r = json.load(open(SP + os.path.dirname(J.base_path(pid)) + '/report.json'))
    return float(r['loo'][model][0])


def plate_size(pid):
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    import plates
    n = pid[3:]
    if pid == '22-35N':
        g = json.load(open(SP + 'cuf/ben_georef.json')); return g['w'], g['h']
    if pid == '22-38':
        return Image.open(_ws.ext('/mnt/user-data/uploads/38.png')).size
    if n in ('34L', '34R', '37L', '37R', '16R'):
        from sb import find
        return Image.open(find(pid)).size
    return Image.open(plates.PNGPATH.get(n, _ws.ext(f'/mnt/user-data/uploads/PNG/{n}.png'))).size


# ------------------------------------------------------------------ solve
class System:
    def __init__(self, plates, C, ties):
        self.plates, self.C, self.ties = plates, C, ties
        self.center = {p: C[p]['O'].mean(0) for p in plates}

    def layout(self, kinds):
        off, o = {}, 0
        for p in self.plates:
            off[p] = o; o += 3 if kinds[p] == 'affine' else 6
        return off, o

    def B(self, p, P, kind):
        return J.basis(P, self.center[p], SCALE, kind)

    def build(self, kinds, tie_w):
        off, m = self.layout(kinds)
        rows, Y, W, tag = [], [], [], []
        for p in self.plates:
            c = self.C[p]; Bm = self.B(p, c['P'], kinds[p])
            for i in range(len(Bm)):
                r = np.zeros(m); r[off[p]:off[p] + Bm.shape[1]] = Bm[i]
                rows.append(r); Y.append(c['O'][i] - c['P'][i]); W.append(1.0); tag.append(('c', p, i))
        for t, (a, b, Pa, Pb) in enumerate(self.ties):
            Ba = self.B(a, Pa[None], kinds[a])[0]; Bb = self.B(b, Pb[None], kinds[b])[0]
            r = np.zeros(m); r[off[a]:off[a] + len(Ba)] = Ba; r[off[b]:off[b] + len(Bb)] -= Bb
            rows.append(r); Y.append(Pb - Pa); W.append(tie_w[t]); tag.append(('t', t, None))
        return np.array(rows), np.array(Y), np.array(W), tag, off

    def solve(self, kinds):
        tie_w = np.ones(len(self.ties))
        for _ in range(8):
            A, Y, W, tag, off = self.build(kinds, tie_w)
            Aw = A * W[:, None]
            Ninv = np.linalg.inv(A.T @ Aw)
            th = Ninv @ (Aw.T @ Y)
            R = Y - A @ th
            nt = len(self.plates) and sum(1 for t in tag if t[0] == 't')
            rt = np.hypot(*R[-nt:].T) if nt else np.zeros(0)
            new_w = np.where(rt <= HUBER, 1.0, HUBER / np.maximum(rt, 1e-9))
            if np.allclose(new_w, tie_w, atol=1e-4):
                break
            tie_w = new_w
        return dict(A=A, Y=Y, W=W, tag=tag, off=off, Ninv=Ninv, th=th, R=R, tie_w=tie_w, kinds=dict(kinds))

    def coef(self, sol, p):
        k = 3 if sol['kinds'][p] == 'affine' else 6; o = sol['off'][p]
        return sol['th'][o:o + k]          # (k, 2): columns E, N

    def corr(self, sol, p, P):
        return self.B(p, P, sol['kinds'][p]) @ self.coef(sol, p)

    def heldout(self, sol, p):
        """leave-one-out over the plate's own controls: base refitted without the control, correction downdated"""
        A, W, R, Ninv, th = sol['A'], sol['W'], sol['R'], sol['Ninv'], sol['th']
        c = self.C[p]; errs = []
        idx = [r for r, t in enumerate(sol['tag']) if t[0] == 'c' and t[1] == p]
        k = 3 if sol['kinds'][p] == 'affine' else 6; o = sol['off'][p]
        for i, r in enumerate(idx):
            a = A[r]; h = W[r] * a @ Ninv @ a
            th_i = th - np.outer(Ninv @ a, W[r] * R[r] / (1 - h))
            Pl = c['Pl'][i]
            pred = Pl + self.B(p, Pl[None], sol['kinds'][p])[0] @ th_i[o:o + k]
            errs.append(np.hypot(*(pred - c['O'][i])))
        return np.array(errs)


def main():
    write = '--write' in sys.argv
    out = SP + f'reports/{datetime.date.today().isoformat()}_joint'
    os.makedirs(out, exist_ok=True)
    plates = S.plate_ids()
    print('plates', len(plates), flush=True)
    C = {}
    for p in plates:
        X, O, P, Pl, names, model = controls(p)
        C[p] = dict(X=X, O=O, P=P, Pl=Pl, names=names, model=model)
    # ties: the seam report's plate-plate pairs, from the old models
    recs = []
    for p in plates:
        recs += S.plate_crossings(p)[0]
    near, _ = S.pairs(recs)
    ties, tinfo = [], []
    for i, j, d in near:
        a, b = recs[i], recs[j]
        if b['kind'] != 'plate':
            continue
        Pa = J.base_many(a['src'], [[a['x'], a['y']]])[0]; Pb = J.base_many(b['src'], [[b['x'], b['y']]])[0]
        ties.append((a['src'], b['src'], Pa, Pb)); tinfo.append(dict(a=a['src'], b=b['src'], street_1=a['a'], street_2=a['b'], before_m=round(d, 2)))
    print('ties', len(ties), flush=True)
    sysm = System(plates, C, ties)

    kinds = {p: 'affine' for p in plates}
    sol = sysm.solve(kinds)
    ho = {p: float(np.sqrt((sysm.heldout(sol, p) ** 2).mean())) for p in plates}
    trail = []
    for ps in range(PASSES):
        for p in plates:
            alt = dict(kinds); alt[p] = 'quadratic' if kinds[p] == 'affine' else 'affine'
            s2 = sysm.solve(alt)
            h2 = float(np.sqrt((sysm.heldout(s2, p) ** 2).mean()))
            if h2 < ho[p] - 1e-6:
                trail.append(dict(pass_=ps + 1, plate=p, to=alt[p], heldout_from=round(ho[p], 3), heldout_to=round(h2, 3)))
                kinds, sol = alt, s2
                ho = {q: float(np.sqrt((sysm.heldout(sol, q) ** 2).mean())) for q in plates}
    # per plate before / after
    rows = []
    for p in plates:
        c = C[p]
        before = np.hypot(*(c['P'] - c['O']).T)
        d_ctrl = sysm.corr(sol, p, c['P'])
        after = np.hypot(*(c['P'] + d_ctrl - c['O']).T)
        w, h = plate_size(p)
        corners = np.array([[0, 0], [w, 0], [w, h], [0, h]], float)
        Pc = J.base_many(p, corners); mv = np.hypot(*sysm.corr(sol, p, Pc).T)
        ob = old_heldout(p, c['model'])
        rows.append(dict(plate=p, base_model=c['model'], correction=sol['kinds'][p], controls=len(c['O']),
                         rms_before=round(float(np.sqrt((before ** 2).mean())), 2), rms_after=round(float(np.sqrt((after ** 2).mean())), 2),
                         heldout_before=round(ob if ob is not None else float(np.sqrt((before ** 2).mean())), 2),
                         heldout_after=round(ho[p], 2),
                         max_corner_move_m=round(float(mv.max()), 2), median_control_move_m=round(float(np.median(np.hypot(*d_ctrl.T))), 2),
                         ties=sum(1 for t in ties if p in t[:2]), image_px=f'{w}x{h}'))
        rows[-1]['rms_change'] = round(rows[-1]['rms_after'] - rows[-1]['rms_before'], 2)
    # ties before / after
    nt = len(ties)
    for t, (a, b, Pa, Pb) in enumerate(ties):
        na = Pa + sysm.corr(sol, a, Pa[None])[0]; nb = Pb + sysm.corr(sol, b, Pb[None])[0]
        tinfo[t].update(after_m=round(float(np.hypot(*(nb - na))), 2), huber_weight=round(float(sol['tie_w'][t]), 3))
    tb = np.array([t['before_m'] for t in tinfo]); ta = np.array([t['after_m'] for t in tinfo])
    summary = dict(plates=len(plates), controls=int(sum(len(C[p]['O']) for p in plates)), ties=nt,
                   ties_before=dict(median=round(float(np.median(tb)), 2), p90=round(float(np.percentile(tb, 90)), 2), max=round(float(tb.max()), 2)),
                   ties_after=dict(median=round(float(np.median(ta)), 2), p90=round(float(np.percentile(ta, 90)), 2), max=round(float(ta.max()), 2)),
                   quadratic=[p for p in plates if sol['kinds'][p] == 'quadratic'],
                   worse_by_more_than_0_3m=[r['plate'] for r in rows if r['rms_change'] > 0.3])
    import scipy
    meta = dict(made=datetime.datetime.now().isoformat(timespec='seconds'), by='tools/sanborn/joint/solve.py', scale_m=SCALE, huber_m=HUBER,
                choice_trail=trail, versions=dict(numpy=np.__version__, scipy=scipy.__version__),
                bases={p: dict(path=J.base_path(p), sha256=sha(J.base_path(p))) for p in plates})
    json.dump(dict(meta=meta, summary=summary, plates=rows, ties=tinfo), open(out + '/solve.json', 'w', encoding='utf8', newline='\n'), indent=1)
    for name, data in (('plates.csv', rows), ('ties.csv', tinfo)):
        with open(out + '/' + name, 'w', newline='', encoding='utf8') as f:
            wr = csv.DictWriter(f, fieldnames=list(data[0]), lineterminator='\n'); wr.writeheader(); wr.writerows(data)
    if write:
        for p in plates:
            jp = J.joint_path(p)
            assert jp != J.base_path(p)
            cf = sysm.coef(sol, p)
            pickle.dump(dict(model='joint', plate=p, base=J.base_path(p), base_sha256=sha(J.base_path(p)), basis=sol['kinds'][p],
                             center=[float(v) for v in sysm.center[p]], scale=SCALE, coefE=cf[:, 0].tolist(), coefN=cf[:, 1].tolist(),
                             solve=os.path.relpath(out, SP).replace('\\', '/'), made=meta['made']), open(SP + jp, 'wb'))
        # the seam report on the new models, and the check that decides whether the imagery is redrawn (Part 3)
        S.READ.clear()
        seam_dir = SP + f'reports/{datetime.date.today().isoformat()}_seams_joint'
        S.main(['--joint', seam_dir])
        after = json.load(open(seam_dir + '/seams.json', encoding='utf8'))['summary']
        before = json.load(open(SP + 'reports/2026-11-06_seams/seams.json', encoding='utf8'))['summary']
        worse = [r for r in rows if r['rms_change'] > 0.3]
        pp_b, pp_a = before['plate-plate'], after['plate-plate']
        verdict = dict(worse_plates=[r['plate'] for r in worse], seam_median_falls=pp_a['median'] < pp_b['median'],
                       seam_p90_falls=pp_a['p90'] < pp_b['p90'])
        verdict['redraw_imagery'] = not worse and verdict['seam_median_falls'] and verdict['seam_p90_falls']
        summary['part3_check'] = verdict
        json.dump(dict(meta=meta, summary=summary, plates=rows, ties=tinfo), open(out + '/solve.json', 'w', encoding='utf8', newline='\n'), indent=1)
        write_readme(out, meta, summary, rows, tinfo, before, after, verdict, os.path.relpath(seam_dir, SP).replace('\\', '/'))
    print(json.dumps(summary, indent=1))
    for r in rows:
        print(r)
    return out


def write_readme(out, meta, summary, rows, tinfo, before, after, verdict, seam_rel):
    L = [f"# Joint refit of the 1922 plates, {meta['made'][:10]}", '',
         "Ben's ruling (6 November): one joint refit of the 1922 plates' positions; imagery tiles and plate footprints may move, "
         'streets, blocks, plots and the 1904 bend do not. This is the solve and its numbers. Nothing is applied: the new models sit '
         'beside the old ones (`fwd_joint.pkl`, `cuf38/fwd38_joint.pkl`, `cuf/joint35N.pkl`); the page, its tiles and every other '
         'file are as they were. Method: `tools/sanborn/joint/solve.py` (its docstring).', '',
         f"{summary['plates']} plates, {summary['controls']} own controls, {summary['ties']} ties (crossings two plates share, "
         "from the seam report). Corrections chosen: "
         + (', '.join(f'{p} quadratic' for p in summary['quadratic']) + ', affine for the rest' if summary['quadratic']
            else "affine for every plate (the quadratic lowered no plate's held-out error)") + '.', '',
         '## Part 3 check', '',
         f"- Every plate's own control rms no worse by more than 0.3 m: **{'yes' if not verdict['worse_plates'] else 'no'}**"
         + (f" (worse: {', '.join(verdict['worse_plates'])})" if verdict['worse_plates'] else ''),
         f"- Plate-plate seam median falls: **{'yes' if verdict['seam_median_falls'] else 'no'}** "
         f"({before['plate-plate']['median']} to {after['plate-plate']['median']} m)",
         f"- Plate-plate seam 90% falls: **{'yes' if verdict['seam_p90_falls'] else 'no'}** "
         f"({before['plate-plate']['p90']} to {after['plate-plate']['p90']} m)",
         f"- So the 1922 imagery is {'redrawn from the new models' if verdict['redraw_imagery'] else '**not** redrawn (stop after Part 2)'}.", '',
         '## Per plate', '',
         'Controls: the plate\'s own OSM crossings (unchanged in number). Rms: own controls, metres. Held-out: leave-one-out rms '
         '(before: the plate\'s own fit report; 35N, nothing fitted, its rms). Corner move: largest move of the plate image\'s four corners.', '',
         '| Plate | Own model | Correction | Controls | Rms before | Rms after | Change | Held-out before | Held-out after | Max corner move m | Median control move m | Ties |',
         '|---|---|---|---|---|---|---|---|---|---|---|---|']
    for r in rows:
        flag = ' **worse**' if r['rms_change'] > 0.3 else ''
        L.append(f"| {r['plate']} | {r['base_model']} | {r['correction']} | {r['controls']} | {r['rms_before']} | {r['rms_after']} | "
                 f"{r['rms_change']:+.2f}{flag} | {r['heldout_before']} | {r['heldout_after']} | {r['max_corner_move_m']} | "
                 f"{r['median_control_move_m']} | {r['ties']} |")
    L += ['', '## Seams', '', f"Seam report rerun on the new models: `{seam_rel}/` (same matching as `reports/2026-11-06_seams/`).", '',
          '| Seam | | Shared | Median m | 90% m | Max m | > 10 m | > 20 m |', '|---|---|---|---|---|---|---|---|']
    for s in ('plate-plate', 'plate-1904'):
        for lab, v in (('before', before[s]), ('after', after[s])):
            L.append(f"| {s} | {lab} | {v['n']} | {v['median']} | {v['p90']} | {v['max']} | {v['over_10m']} | {v['over_20m']} |")
    L += ['', 'The 1904 frames did not move, so plate-1904 seams change only by the plates\' moves; the bent frames were bent onto '
          'the old plate positions.', '', '## Ties, widest after the solve', '', '| Plates | Crossing | Before m | After m | Huber weight |', '|---|---|---|---|---|']
    for t in sorted(tinfo, key=lambda t: -t['after_m'])[:15]:
        L.append(f"| {t['a']} / {t['b']} | {t['street_1']} & {t['street_2']} | {t['before_m']} | {t['after_m']} | {t['huber_weight']} |")
    L += ['', f"Choice trail (affine to quadratic tried per plate, kept if held-out fell): {meta['choice_trail'] or 'no change'}.",
          f"Computed with numpy {meta['versions']['numpy']}, scipy {meta['versions']['scipy']}.", '']
    open(out + '/README.md', 'w', encoding='utf8', newline='\n').write('\n'.join(L))


if __name__ == '__main__':
    main()
