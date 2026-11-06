"""The local fit again (Ben, 6 November 2026), after the round-3 re-read of the controls near the 37L/37R gutter.

    cd data/sanborn
    python ../../tools/sanborn/joint/local2.py [--write]

Same method as tools/sanborn/joint/local.py (its docstring), with three changes:
- the re-read picks stand in for the old ones: every crossing of the five plates re-read in data/sanborn/picks22_reread
  (rounds 1 and 3; the last read of a crossing counts) takes its new pick, for controls and ties alike; controls the
  round-3 re-read classed "wrong match" are dropped, and ties classed (b) are dropped;
- a plate whose controls moved or were dropped gets its own model rebuilt from the corrected controls (same model kind,
  fwdlib.make; no new model choice, no drop test); the rebuilt model is stored in the new model file (base_override);
- 37L and 37R corrections are affine only; 33, 34R and 38 are chosen by held-out error as before.
"Before" for the guard is each plate's old model on the same (corrected) controls; the rms on the old controls (the
first local fit's "before") is shown beside it. Writes reports/<date>_local2/ and, with --write, fwd_local2.pkl beside
each old model, the seam report on the old models with the re-read picks (reports/<date>_seams_reread3) and on the new
models (reports/<date>_seams_local2).
"""
import csv, datetime, glob, json, os, pickle, sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.dirname(HERE))
import _ws  # noqa: E402
import local as LC  # noqa: E402

J, S, SV = LC.J, LC.S, LC.SV
SP = _ws.DATA
FIT, TAG, AFFINE_ONLY = LC.FIT, 'local2', ('22-37L', '22-37R')
TOL_PX = 3.0


def reread_state():
    """latest re-read pick per (plate, old pick) for the five plates; control classes from round 3; (b) ties to drop"""
    recs = []
    for f in sorted(glob.glob(SP + 'picks22_reread/*/*.json')):
        r = json.load(open(f, encoding='utf8'))
        if r.get('plate') in FIT and r.get('new_pick'):
            recs.append((r.get('round', 1), r, os.path.relpath(f, SP).replace('\\', '/')))
    latest = {}
    for rnd, r, f in sorted(recs, key=lambda t: t[0]):
        k = (r['plate'], round(r['old_pick']['x']), round(r['old_pick']['y']))
        latest[k] = (r, f)
    ctl = {}
    for rnd, r, f in recs:
        if rnd == 3 and r.get('kind') == 'control':
            ctl.setdefault(r['plate'], {})[r['control_index']] = dict(cls=r['classification'], new=[r['new_pick']['x'], r['new_pick']['y']], record=f)
    for f in glob.glob(SP + 'picks22_reread/*/r3_*.json'):       # round-3 controls without a new pick (unresolved)
        r = json.load(open(f, encoding='utf8'))
        if r.get('kind') == 'control' and not r.get('new_pick') and r['plate'] in FIT:
            ctl.setdefault(r['plate'], {})[r['control_index']] = dict(cls=r['classification'], new=None, record=os.path.relpath(f, SP).replace('\\', '/'))
    return latest, ctl, LC.dropped_ties()


def new_px(latest, pid, x, y):
    for (p, ox, oy), (r, f) in latest.items():
        if p == pid and abs(r['old_pick']['x'] - x) <= TOL_PX and abs(r['old_pick']['y'] - y) <= TOL_PX:
            return (r['new_pick']['x'], r['new_pick']['y']), f
    return None, None


def setup(latest, ctl):
    import fwdlib
    C, basefn, info = {}, {}, {}
    for p in FIT:
        X, O, P, Pl, names, model = SV.controls(p)
        st = ctl.get(p, {}); keep, X2, changed = [], X.copy(), []
        for i in range(len(X)):
            s = st.get(i)
            if s and s['cls'] == 'wrong match':
                changed.append((i, 'dropped')); continue
            if s and s.get('new'):
                X2[i] = s['new']; changed.append((i, s['cls']))
            elif not s:
                np_, f = new_px(latest, p, *X[i])
                if np_ is not None:
                    X2[i] = np_; changed.append((i, 'tie re-read'))
            keep.append(i)
        Xn, On = X2[keep], O[keep]
        rebuild = any(c[1] in ('moved', 'dropped') for c in changed) and p != '22-35N'
        if rebuild:
            f = fwdlib.make(model, Xn, On); basefn[p] = f
        else:
            basefn[p] = (lambda pid: lambda q: J.base_many(pid, np.asarray(q, float)))(p)
        Pn = basefn[p](Xn)
        Pl = np.array([fwdlib.make(model, np.delete(Xn, i, 0), np.delete(On, i, 0))(Xn[i:i + 1])[0] for i in range(len(Xn))]) if p != '22-35N' else Pn
        C[p] = dict(X=Xn, O=On, P=Pn, Pl=Pl, model=model)
        old_on_new = J.base_many(p, Xn)
        info[p] = dict(changed=changed, rebuilt=rebuild, controls_old=len(X),
                       rms_old_controls=float(np.sqrt(np.mean(np.sum((P - O) ** 2, 1)))),
                       rms_before=float(np.sqrt(np.mean(np.sum((old_on_new - On) ** 2, 1)))),
                       base_override=dict(model=model, X=Xn.tolist(), O=On.tolist()) if rebuild else None)
    return C, basefn, info


def patched_crossings(latest):
    _pc = S.plate_crossings

    def pc(pid):
        recs, nf = _pc(pid)
        if pid in FIT:
            w = S.plate_world(pid)
            for r in recs:
                np_, f = new_px(latest, pid, r['x'], r['y'])
                if np_ is not None:
                    E, N = w(*np_); r.update(x=np_[0], y=np_[1], E=E, N=N, reread=f)
        return recs, nf
    return pc


def patched_pairs(drop):
    _pairs = S.pairs

    def pairs(recs):
        near, far = _pairs(recs)
        keep = lambda i, j: (recs[i]['src'], recs[j]['src'], recs[i]['k']) not in drop
        return [t for t in near if keep(t[0], t[1])], [t for t in far if keep(t[0], t[1])]
    return pairs


def main():
    write = '--write' in sys.argv
    today = datetime.date.today().isoformat()
    out = SP + f'reports/{today}_local2'; os.makedirs(out, exist_ok=True)
    latest, ctl, drop = reread_state()
    C, basefn, info = setup(latest, ctl)
    S.plate_crossings = patched_crossings(latest); S.pairs = patched_pairs(drop)
    recs = []
    for p in S.plate_ids():
        recs += S.plate_crossings(p)[0]
    near, _ = S.pairs(recs)
    ties = []
    for i, j, d in near:
        a, b = recs[i], recs[j]
        if b['kind'] != 'plate' or not (a['src'] in FIT or b['src'] in FIT):
            continue
        Pa = basefn[a['src']]([[a['x'], a['y']]])[0] if a['src'] in FIT else np.array([a['E'], a['N']])
        Pb = basefn[b['src']]([[b['x'], b['y']]])[0] if b['src'] in FIT else np.array([b['E'], b['N']])
        sheet = {a['src'], b['src']} == {'22-37L', '22-37R'}
        ties.append(dict(a=a['src'], b=b['src'], Pa=np.asarray(Pa, float), Pb=np.asarray(Pb, float), street_1=a['a'], street_2=a['b'],
                         before_m=round(float(np.hypot(*(np.asarray(Pa) - np.asarray(Pb)))), 2), sheet=sheet, w=LC.W_SHEET if sheet else 1.0,
                         reread=bool(a.get('reread') or b.get('reread'))))
    ov = LC.overlap_pairs()
    pr = np.array([q[:2] for q in ov['pairs']]); pl = np.array([q[2:] for q in ov['pairs']])
    PR, PL = basefn['22-37R'](pr), basefn['22-37L'](pl)
    sheet = [dict(PL=PL[k], PR=PR[k]) for k in range(len(pr))]
    gap0 = np.hypot(*(PL - PR).T)
    L = LC.Local(C, ties, sheet)
    kinds = {p: 'affine' for p in FIT}
    sol = L.solve(kinds); ho = {p: L.heldout(sol, p) for p in FIT}; trail = []
    for ps in range(LC.PASSES + 1):
        changed = False
        for p in FIT:
            if p in AFFINE_ONLY:
                continue
            best = (ho[p], kinds[p], sol)
            for k in LC.KINDS:
                if k == kinds[p]:
                    continue
                alt = dict(kinds); alt[p] = k; s2 = L.solve(alt); h2 = L.heldout(s2, p)
                if h2 < best[0] - 1e-6:
                    best = (h2, k, s2)
            if best[1] != kinds[p]:
                trail.append(dict(pass_=ps + 1, plate=p, frm=kinds[p], to=best[1], heldout=round(best[0], 3)))
                kinds = dict(kinds); kinds[p] = best[1]; sol = best[2]; ho = {q: L.heldout(sol, q) for q in FIT}; changed = True
        print('pass', ps + 1, kinds, {p: round(v, 2) for p, v in ho.items()}, flush=True)
        if not changed:
            break
    rows = []
    for p in FIT:
        c = C[p]; dc = L.corr(sol, p, c['P']); after = np.hypot(*(c['P'] + dc - c['O']).T)
        w, h = SV.plate_size(p); corners = np.array([[0, 0], [w, 0], [w, h], [0, h]], float)
        Pc = basefn[p](corners); mv = np.hypot(*(Pc + L.corr(sol, p, Pc) - J.base_many(p, corners)).T)
        ob = SV.old_heldout(p, c['model']); inf = info[p]
        rows.append(dict(plate=p, base_model=c['model'] + (' (rebuilt)' if inf['rebuilt'] else ''), correction=kinds[p],
                         controls=len(c['O']), controls_changed=';'.join(f'{i}:{s}' for i, s in inf['changed']) or '-',
                         rms_old_controls=round(inf['rms_old_controls'], 2), rms_before=round(inf['rms_before'], 2),
                         rms_after=round(float(np.sqrt((after ** 2).mean())), 2), heldout_before=round(ob, 2), heldout_after=round(ho[p], 2),
                         max_corner_move_m=round(float(mv.max()), 2), median_control_move_m=round(float(np.median(np.hypot(*dc.T))), 2),
                         ties=sum(1 for t in ties if p in (t['a'], t['b']))))
        rows[-1]['rms_change'] = round(rows[-1]['rms_after'] - rows[-1]['rms_before'], 2)
    tinfo = []
    for k, t in enumerate(ties):
        na = t['Pa'] + L.corr(sol, t['a'], t['Pa'])[0]; nb = t['Pb'] + L.corr(sol, t['b'], t['Pb'])[0]
        tinfo.append(dict(a=t['a'], b=t['b'], street_1=t['street_1'], street_2=t['street_2'], before_m=t['before_m'],
                          after_m=round(float(np.hypot(*(nb - na))), 2), weight=round(float(t['w'] if t['sheet'] else sol['tw'][k]), 3),
                          sheet=t['sheet'], reread=t['reread']))
    gap1 = np.hypot(*(PL + L.corr(sol, '22-37L', PL) - PR - L.corr(sol, '22-37R', PR)).T)
    summary = dict(plates=FIT, kinds=kinds, ties=len(ties), gutter_pairs=len(sheet),
                   gutter_gap_before=dict(median=round(float(np.median(gap0)), 2), max=round(float(gap0.max()), 2)),
                   gutter_gap_after=dict(median=round(float(np.median(gap1)), 2), max=round(float(gap1.max()), 2)),
                   worse_by_more_than_0_3m=[r['plate'] for r in rows if r['rms_change'] > 0.3],
                   controls_changed={p: info[p]['changed'] for p in FIT}, rebuilt=[p for p in FIT if info[p]['rebuilt']])
    import scipy
    meta = dict(made=datetime.datetime.now().isoformat(timespec='seconds'), by='tools/sanborn/joint/local2.py', affine_only=AFFINE_ONLY,
                choice_trail=trail, versions=dict(numpy=np.__version__, scipy=scipy.__version__),
                bases={p: dict(path=J.base_path(p), sha256=SV.sha(J.base_path(p))) for p in FIT}, overlap=LC.OVERLAP)
    if write:
        for p in FIT:
            jp = J.joint_path(p, TAG); assert jp != J.base_path(p)
            d = L.model_dict(sol, p)
            d.update(base=J.base_path(p), base_sha256=SV.sha(J.base_path(p)), base_override=info[p]['base_override'],
                     solve=os.path.relpath(out, SP).replace('\\', '/'), made=meta['made'])
            pickle.dump(d, open(SP + jp, 'wb'))
        J._J.clear()
        res = {}
        for name, models in (('reread3', None), (TAG, TAG)):
            S.READ.clear(); d_ = SP + f'reports/{today}_seams_{name}'
            S.main((['--models', models] if models else []) + [d_])
            S.MODELS = None
            res[name] = json.load(open(d_ + '/seams.json', encoding='utf8'))['seams']
        sb, sa = LC.seam_stats(res['reread3'], FIT), LC.seam_stats(res[TAG], FIT)
        worse = summary['worse_by_more_than_0_3m']
        verdict = dict(worse_plates=worse, median_falls=sa['touching']['median'] < sb['touching']['median'],
                       p90_falls=sa['touching']['p90'] < sb['touching']['p90'])
        verdict['apply'] = not worse and verdict['median_falls'] and verdict['p90_falls']
        summary.update(seams_before=sb, seams_after=sa, part3_check=verdict,
                       seam_reports=[f'reports/{today}_seams_reread3', f'reports/{today}_seams_{TAG}'])
    # every control of the five, before and after (which controls a failing plate leaves)
    ctl_rows = []
    for p in FIT:
        c = C[p]; dc = L.corr(sol, p, c['P'])
        mf = (os.path.dirname(J.base_path(p)) + '/matches.json') if p != '22-38' else 'cuf38/matches38.json'
        M = json.load(open(SP + mf, encoding='utf8'))
        M = [q for q in M if q.get('osm')] if isinstance(M, list) else []
        before = J.base_many(p, c['X'])
        for i in range(len(c['X'])):
            q = min(M, key=lambda q: np.hypot(q['x'] - c['X'][i][0], q['y'] - c['X'][i][1])) if M else None
            ctl_rows.append(dict(plate=p, x=round(float(c['X'][i][0]), 1), y=round(float(c['X'][i][1]), 1),
                                 crossing=f"{q['a']} & {q['b']}" if q else '', before_m=round(float(np.hypot(*(before[i] - c['O'][i]))), 2),
                                 after_m=round(float(np.hypot(*(c['P'][i] + dc[i] - c['O'][i]))), 2), moved_m=round(float(np.hypot(*dc[i])), 2)))
    json.dump(dict(meta=meta, summary=summary, plates=rows, ties=tinfo), open(out + '/solve.json', 'w', encoding='utf8', newline='\n'), indent=1, default=str)
    if write:
        write_readme(out, meta, summary, rows, tinfo, ctl_rows)
    for name, data in (('plates.csv', rows), ('ties.csv', tinfo), ('controls.csv', ctl_rows)):
        with open(out + '/' + name, 'w', newline='', encoding='utf8') as f:
            wr = csv.DictWriter(f, fieldnames=list(data[0]), lineterminator='\n'); wr.writeheader(); wr.writerows(data)
    print(json.dumps(summary, indent=1, default=str))
    for r in rows:
        print(r)


def write_readme(out, meta, summary, rows, tinfo, ctl_rows):
    v = summary['part3_check']; sb, sa = summary['seams_before'], summary['seams_after']
    L = [f"# Local fit again (after the round-3 re-read), {meta['made'][:10]}", '',
         "Ben's ruling (6 November): the five plates (33, 34R, 37L, 37R, 38) fitted together again, the other 16 fixed, 37L and 37R one "
         "sheet at the gutter, with the re-read picks in place of the old ones and the wrong matches dropped. The 37L and 37R corrections "
         "are affine only; 33, 34R and 38 are chosen by held-out error. Method: `tools/sanborn/joint/local2.py` (its docstring). Nothing "
         "is applied: the new models sit beside the old ones (`fwd_local2.pkl`, `cuf38/fwd38_local2.pkl`).", '',
         'Re-read picks used: all 11 of round 3 were confirmed (none moved more than 3.8 m, none a wrong match), so no control was dropped '
         'and no plate\'s own model was rebuilt; the re-read pixel positions stand in for the old ones. Round-1 re-reads of 37L/37R, 37R/38 '
         'and 35N/38 crossings stand in for their ties too.', '',
         f"{summary['ties']} ties, {summary['gutter_pairs']} gutter pairs. Gutter gap (the same paper point on both halves): median "
         f"{summary['gutter_gap_before']['median']} m, max {summary['gutter_gap_before']['max']} m before; median "
         f"{summary['gutter_gap_after']['median']} m, max {summary['gutter_gap_after']['max']} m after.", '',
         '## Part 3 check', '',
         f"- Every plate's own control rms within 0.3 m of before: **{'yes' if not v['worse_plates'] else 'no'}**" + (f" (worse: {', '.join(v['worse_plates'])})" if v['worse_plates'] else ''),
         f"- Plate-plate seam median across the five falls: **{'yes' if v['median_falls'] else 'no'}** ({sb['touching']['median']} to {sa['touching']['median']} m)",
         f"- Plate-plate seam 90% across the five falls: **{'yes' if v['p90_falls'] else 'no'}** ({sb['touching']['p90']} to {sa['touching']['p90']} m)",
         f"- So Part 3 {'goes ahead' if v['apply'] else '**does not** go ahead (stop after Part 2)'}.", '',
         '"Before" is each plate\'s own model on the same controls (the re-read pixel positions); "rms, old controls" is the first local '
         "fit's before. Seams before: the plates' own models with the re-read picks and the wrong matches dropped "
         f"(`{summary['seam_reports'][0]}`); after: the new models (`{summary['seam_reports'][1]}`). \"Across the five\": every plate-plate seam a fitted plate takes part in.", '',
         '## Per plate', '',
         '| Plate | Own model | Correction | Controls | Rms, old controls | Rms before | Rms after | Change | Held-out before | Held-out after | Max corner move m | Median control move m | Ties |',
         '|---|---|---|---|---|---|---|---|---|---|---|---|---|']
    for r in rows:
        L.append(f"| {r['plate']} | {r['base_model']} | {r['correction']} | {r['controls']} | {r['rms_old_controls']} | {r['rms_before']} | {r['rms_after']} | "
                 f"{r['rms_change']:+.2f}{' **worse**' if r['rms_change'] > 0.3 else ''} | {r['heldout_before']} | {r['heldout_after']} | "
                 f"{r['max_corner_move_m']} | {r['median_control_move_m']} | {r['ties']} |")
    worse = [r['plate'] for r in rows if r['rms_change'] > 0.3]
    if worse:
        L += ['', '## The controls of the plates that got worse', '', 'Each control\'s distance from its OSM crossing, before and after (all of them; `controls.csv` has all five plates).', '',
              '| Plate | Crossing | Pixel | Before m | After m | Moved m |', '|---|---|---|---|---|---|']
        for c in sorted([c for c in ctl_rows if c['plate'] in worse], key=lambda c: (c['plate'], -c['after_m'])):
            L.append(f"| {c['plate']} | {c['crossing']} | ({c['x']:.0f}, {c['y']:.0f}) | {c['before_m']} | {c['after_m']} | {c['moved_m']} |")
    L += ['', '## Seams', '', '| Plate-plate seams | | Shared | Median m | 90% m | Max m | > 10 m | > 20 m |', '|---|---|---|---|---|---|---|---|']
    for key, lab in (('touching', 'touching the five'), ('within', 'among the five'), ('all', 'all plates')):
        for when, d in (('before', sb[key]), ('after', sa[key])):
            L.append(f"| {lab} | {when} | {d['n']} | {d.get('median', '')} | {d.get('p90', '')} | {d.get('max', '')} | {d.get('over_10m', '')} | {d.get('over_20m', '')} |")
    for when, d in (('before', sb['plate_1904_touching']), ('after', sa['plate_1904_touching'])):
        L.append(f"| plate-1904, the five | {when} | {d['n']} | {d.get('median', '')} | {d.get('p90', '')} | {d.get('max', '')} | {d.get('over_10m', '')} | {d.get('over_20m', '')} |")
    L += ['', '## Ties, widest after the fit', '', '| Plates | Crossing | Before m | After m | Weight |', '|---|---|---|---|---|']
    for t in sorted(tinfo, key=lambda t: -t['after_m'])[:15]:
        L.append(f"| {t['a']} / {t['b']} | {t['street_1']} & {t['street_2']} | {t['before_m']} | {t['after_m']} | {t['weight']}{' (sheet)' if t['sheet'] else ''} |")
    L += ['', f"Choice trail (33, 34R, 38): {meta['choice_trail'] or 'affine kept'}. Computed with numpy {meta['versions']['numpy']}, scipy {meta['versions']['scipy']}.", '']
    open(out + '/README.md', 'w', encoding='utf8', newline='\n').write('\n'.join(L))


if __name__ == '__main__':
    main()
