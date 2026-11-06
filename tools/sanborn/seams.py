"""Seam report (read only): every street crossing that two 1922 plates, or a 1922 plate and a 1904 frame, both show, and
how far apart the two copies sit on the page.

    cd data/sanborn
    python ../../tools/sanborn/seams.py [OUT_DIR]      (default reports/<date>_seams)

Nothing is fitted or rebuilt; the models are used as stored. A crossing's position is where the page draws it:
- 1922 plates (the plates on the 1922 layer, cuf/plates.py PLATES): the agents' picks (sbg/picks22/s22-<plate>*.json, the
  readers' copies of one crossing within 60 px averaged, as cuf/x1904.py does) through the plate's forward model
  (cufp/<N>/fwd.pkl, cuf_cw/<half>/fwd.pkl, cuf38/fwd38.pkl; plate 35N through Ben's georeference, cuf/ben_georef.json,
  as drawn). The page draws the plates through inverse grids made from these models (model.npz, 2 m grid).
- 1904 deck and north frames (tiles_n): picks (sbg/picks/s<sheet>.json) split into frames by panel as cuf/x1904.py does
  (plus lph/mosn.py PANEL_KEEP/DROP and the split sheets of sbg/fit/load.py), placed by the frame transform
  (lph/tf_all.json, tf_ext*.json) and the 1922 bend (lph/tps.pkl), as lph/tiles_all.py draws them.
- 1904 basin frames (tiles_b): sbg/fit/load.py records placed by sbg/fit/tf.json (223 and 224 from lph/tf_all.json), for
  frames not already in the deck and north set and not on deck sheets, as sbg/fit/tiles.py draws them.
Crossings match by street names (sbg/names.py key and base, as cuf/x1904.py) within 45 m (plan rule 4's first radius);
each record pairs with the nearest copy in each other source. Same-name pairs 45-150 m apart are listed apart: they are
either a bad seam or two different crossings of the same two streets.
"""
import collections, csv, datetime, glob, hashlib, json, os, pickle, sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _ws  # noqa: E402

SP = _ws.DATA
for d in ('sbg', 'sbg/fit', 'lph', 'cuf', 'cufp', 'cuf38'):
    sys.path.insert(0, _ws.CODE + d)
from names import key, base  # noqa: E402
import tps  # noqa: E402
import fwdlib  # noqa: E402
import common as C  # noqa: E402
from load import load, frame_of, DECK, YSPLIT  # noqa: E402
from shapely.geometry import Point, Polygon  # noqa: E402

MATCH, FAR, DUP_PX = 45.0, 150.0, 60.0
JOINT = False   # --joint: plates placed by the joint refit's models (tools/sanborn/joint/jointlib.py) instead of their own
READ = []   # files read, for the report's checksums


def jload(rel):
    READ.append(rel); return json.load(open(SP + rel, encoding='utf8'))


def pload(rel):
    READ.append(rel); return pickle.load(open(SP + rel, 'rb'))


def k2(a, b):
    return tuple(sorted((base(key(a)), base(key(b)))))


def ap(p, x, y):   # lph/mosn.py ap
    if len(p) == 6:
        return p[0] * x + p[1] * y + p[4], p[2] * x + p[3] * y + p[5]
    a, c, tx, ty = p
    return a * x + c * y + tx, c * x - a * y + ty


# ---------------------------------------------------------------- 1922 plates
def plate_ids():
    sys.path.insert(0, _ws.CODE + 'cuf')
    import plates   # noqa: E402  (reads lph/tf22_cw.json; images are loaded only when drawn)
    READ.append('lph/tf22_cw.json')
    return [p['id'] for p in plates.PLATES if p['ok']()]


def plate_world(pid):
    n = pid[3:]
    if JOINT:
        sys.path.insert(0, _ws.CODE + 'joint')
        import jointlib
        READ.extend([jointlib.joint_path(pid), jointlib.base_path(pid)])
        return lambda x, y: jointlib.world(pid, x, y)
    if pid == '22-35N':
        READ.append('cuf/ben_georef.json')
        return lambda x, y: tuple(float(v) for v in C.px2ben(x, y))
    if pid == '22-38':
        import fwd38lib
        READ.append('cuf38/fwd38.pkl')
        return fwd38lib.world
    READ.append(f'cufp/{n}/fwd.pkl' if os.path.exists(SP + f'cufp/{n}/fwd.pkl') else f'cuf_cw/{n}/fwd.pkl')
    return lambda x, y: fwdlib.world(n, x, y)


def plate_crossings(pid):
    files = sorted(set(glob.glob(SP + f'sbg/picks22/s{pid}.json') + glob.glob(SP + f'sbg/picks22/s{pid}_*.json')))
    seen = []
    for f in files:
        rel = os.path.relpath(f, SP).replace('\\', '/'); READ.append(rel)
        for p in json.load(open(f, encoding='utf8')).get('intersections', []):
            if '?' in p['a'] + p['b']:
                continue
            k = k2(p['a'], p['b'])
            q = next((s for s in seen if s['k'] == k and np.hypot(s['x'] - p['x'], s['y'] - p['y']) < DUP_PX), None)
            if q:
                q['xs'].append(p['x']); q['ys'].append(p['y']); q['x'] = float(np.mean(q['xs'])); q['y'] = float(np.mean(q['ys']))
            else:
                seen.append(dict(k=k, a=p['a'], b=p['b'], x=float(p['x']), y=float(p['y']), xs=[p['x']], ys=[p['y']]))
    w = plate_world(pid)
    out = []
    for s in seen:
        E, N = w(s['x'], s['y'])
        out.append(dict(src=pid, kind='plate', k=s['k'], a=s['a'], b=s['b'], x=round(s['x'], 1), y=round(s['y'], 1),
                        E=E, N=N, readers=len(s['xs'])))
    return out, len(files)


# ---------------------------------------------------------------- 1904 frames
def deck_frames():
    TF = {}
    for f in ('lph/tf_all.json', 'lph/tf_ext.json', 'lph/tf_ext2.json', 'lph/tf_ext3.json'):
        TF.update(jload(f))
    MOD = pload('lph/tps.pkl')
    PX = {}
    for f in ('lph/panels_ext.json', 'lph/panels_ext2.json', 'lph/panels_ext3.json'):
        PX.update(jload(f))
    import mosn  # noqa: E402  (PANEL_KEEP / PANEL_DROP)
    poly = {k: Polygon(v) for k, v in PX.items()}
    inbox = lambda bs, x, y: any(b[0] <= x <= b[2] and b[1] <= y <= b[3] for b in bs)
    out = []
    by_sheet = collections.defaultdict(list)
    for fr in TF:
        by_sheet[mosn.sheet_of(fr)].append(fr)
    for sh, frs in sorted(by_sheet.items()):
        rel = f'sbg/picks/s{sh}.json'
        if not os.path.exists(SP + rel):
            continue
        J = jload(rel)
        for fr in frs:
            sibs = [s for s in PX if mosn.sheet_of(s) == sh and s != fr]
            pts = []
            for p in J.get('intersections', []):
                if '?' in p['a'] + p['b']:
                    continue
                x, y = float(p['x']), float(p['y'])
                if fr in PX and not poly[fr].contains(Point(x, y)):
                    continue
                if any(poly[s].contains(Point(x, y)) for s in sibs):
                    continue
                if fr in mosn.PANEL_KEEP and not inbox(mosn.PANEL_KEEP[fr], x, y):
                    continue
                if fr in mosn.PANEL_DROP and inbox(mosn.PANEL_DROP[fr], x, y):
                    continue
                if (sh in YSPLIT or sh == 17) and frame_of(sh, p.get('part'), y) != fr:
                    continue
                pts.append((p, x, y))
            if not pts:
                continue
            xs = np.array([q[1] for q in pts]); ys = np.array([q[2] for q in pts])
            E, N = ap(TF[fr], xs, ys)
            if fr in MOD:
                dE, dN = tps.disp(fr, E, N, MOD); E, N = E + dE, N + dN
            for (p, x, y), e, n in zip(pts, E, N):
                out.append(dict(src='1904 ' + fr, kind='frame', k=k2(p['a'], p['b']), a=p['a'], b=p['b'], x=x, y=y,
                                E=float(e), N=float(n), bent=fr in MOD))
    return out, set(TF)


def basin_frames(deck_tf):
    P = jload('sbg/fit/tf.json')
    for k, v in jload('lph/tf_all.json').items():
        if k in ('223', '224'):
            P[k] = v
    R, _ = load()
    READ.extend(sorted({f'sbg/picks/s{r["s"]}.json' for r in R}))
    out = []
    for r in R:
        fr = r['fr']
        if not fr or fr not in P or fr in deck_tf or r['s'] in DECK or '?' in r['a'] + r['b']:
            continue
        E, N = ap(P[fr], r['x'], r['y'])
        out.append(dict(src='1904 ' + fr, kind='frame', k=k2(r['a'], r['b']), a=r['a'], b=r['b'], x=r['x'], y=r['y'],
                        E=float(E), N=float(N), basin=True))
    return out


# ---------------------------------------------------------------- pairs
def pairs(recs):
    byk = collections.defaultdict(list)
    for i, r in enumerate(recs):
        byk[r['k']].append(i)
    near, far = {}, {}
    for k, idx in byk.items():
        for i in idx:
            a = recs[i]
            if a['kind'] != 'plate':
                continue
            best = {}
            for j in idx:
                b = recs[j]
                if b['src'] == a['src'] or (b['kind'] == 'plate' and b['src'] < a['src']):
                    continue   # plate-plate pairs once (a < b); plate-frame pairs from the plate side
                d = float(np.hypot(b['E'] - a['E'], b['N'] - a['N']))
                if d < FAR and (b['src'] not in best or d < best[b['src']][0]):
                    best[b['src']] = (d, j)
            for src, (d, j) in best.items():
                (near if d < MATCH else far)[(i, j)] = d
    # one to one within each pair of sources: nearest first
    def one2one(dd):
        used, keep = set(), []
        for (i, j), d in sorted(dd.items(), key=lambda kv: kv[1]):
            si, sj = (i, recs[j]['src']), (j, recs[i]['src'])
            if si in used or sj in used:
                continue
            used |= {si, sj}; keep.append((i, j, d))
        return keep
    n = one2one(near)
    taken = {(i, recs[j]['src']) for i, j, _ in n} | {(j, recs[i]['src']) for i, j, _ in n}
    f = [(i, j, d) for i, j, d in one2one(far) if (i, recs[j]['src']) not in taken and (j, recs[i]['src']) not in taken]
    return n, f


def stats(ds, vs):
    ds = np.asarray(ds); vs = np.asarray(vs)
    return dict(n=int(len(ds)), median=round(float(np.median(ds)), 2), rms=round(float(np.sqrt((ds ** 2).mean())), 2),
                p90=round(float(np.percentile(ds, 90)), 2), max=round(float(ds.max()), 2),
                mean_dE=round(float(vs[:, 0].mean()), 2), mean_dN=round(float(vs[:, 1].mean()), 2))


def main(argv=None):
    global JOINT
    argv = sys.argv[1:] if argv is None else argv
    JOINT = '--joint' in argv
    args = [a for a in argv if a != '--joint']
    out_dir = args[0] if args else SP + f"reports/{datetime.date.today().isoformat()}_seams{'_joint' if JOINT else ''}"
    os.makedirs(out_dir, exist_ok=True)
    recs, plate_info = [], {}
    for pid in plate_ids():
        r, nf = plate_crossings(pid); recs += r; plate_info[pid] = dict(pick_files=nf, crossings=len(r))
    dr, deck_tf = deck_frames(); br = basin_frames(deck_tf)
    recs += dr + br
    near, far = pairs(recs)

    rows = []
    for i, j, d in near + far:
        a, b = recs[i], recs[j]
        rows.append(dict(seam='plate-plate' if b['kind'] == 'plate' else 'plate-1904', within_45m=d < MATCH,
                         a_src=a['src'], b_src=b['src'], street_1=a['a'], street_2=a['b'], b_names=f"{b['a']} / {b['b']}",
                         a_E=round(a['E'], 2), a_N=round(a['N'], 2), b_E=round(b['E'], 2), b_N=round(b['N'], 2),
                         dE=round(b['E'] - a['E'], 2), dN=round(b['N'] - a['N'], 2), dist_m=round(d, 2),
                         a_px=f"{a['x']:.0f},{a['y']:.0f}", b_px=f"{b['x']:.0f},{b['y']:.0f}",
                         b_set=('basin' if b.get('basin') else 'deck/north' + (', bent' if b.get('bent') else '')) if b['kind'] == 'frame' else ''))
    rows.sort(key=lambda r: (not r['within_45m'], r['seam'], r['a_src'], r['b_src'], -r['dist_m']))

    groups = collections.defaultdict(list)
    for r in rows:
        if r['within_45m']:
            groups[(r['seam'], r['a_src'], r['b_src'])].append(r)
    per_pair = [dict(seam=s, a=a, b=b, **stats([r['dist_m'] for r in g], [(r['dE'], r['dN']) for r in g]))
                for (s, a, b), g in sorted(groups.items())]
    summary = {}
    for s in ('plate-plate', 'plate-1904'):
        g = [r for r in rows if r['within_45m'] and r['seam'] == s]
        summary[s] = dict(pairs_of_sources=sum(1 for p in per_pair if p['seam'] == s),
                          **(stats([r['dist_m'] for r in g], [(r['dE'], r['dN']) for r in g]) if g else dict(n=0)),
                          over_5m=sum(r['dist_m'] > 5 for r in g), over_10m=sum(r['dist_m'] > 10 for r in g),
                          over_20m=sum(r['dist_m'] > 20 for r in g),
                          same_names_45_150m=sum(1 for r in rows if not r['within_45m'] and r['seam'] == s))
    reads = sorted(set(READ))
    import scipy, pyproj, shapely
    meta = dict(made=datetime.datetime.now().isoformat(timespec='seconds'), by='tools/sanborn/seams.py (read only)' + (' --joint' if JOINT else ''),
                plate_models='joint refit (fwd_joint.pkl)' if JOINT else "each plate's own (fwd.pkl, Ben georeference for 35N)",
                match_m=MATCH, far_m=FAR, reader_merge_px=DUP_PX,
                plates=plate_info, frames=dict(deck_north=len({r['src'] for r in dr}), basin=len({r['src'] for r in br})),
                crossings=dict(plates=sum(r['kind'] == 'plate' for r in recs), frames_deck_north=len(dr), frames_basin=len(br)),
                versions=dict(python=sys.version.split()[0], numpy=np.__version__, scipy=scipy.__version__, pyproj=pyproj.__version__, shapely=shapely.__version__),
                inputs={f: hashlib.sha256(open(SP + f, 'rb').read()).hexdigest() for f in reads})
    json.dump(dict(meta=meta, summary=summary, per_pair=per_pair, seams=rows), open(os.path.join(out_dir, 'seams.json'), 'w', encoding='utf8', newline='\n'), indent=1)
    with open(os.path.join(out_dir, 'seams.csv'), 'w', newline='', encoding='utf8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator='\n'); w.writeheader(); w.writerows(rows)
    with open(os.path.join(out_dir, 'per_pair.csv'), 'w', newline='', encoding='utf8') as f:
        w = csv.DictWriter(f, fieldnames=list(per_pair[0]), lineterminator='\n'); w.writeheader(); w.writerows(per_pair)
    write_md(out_dir, meta, summary, per_pair, rows)
    print(json.dumps(dict(summary=summary, plates=len(plate_info), crossings=meta['crossings'], frames=meta['frames']), indent=1))
    return out_dir


def write_md(out_dir, meta, summary, per_pair, rows):
    near = [r for r in rows if r['within_45m']]
    pf = [r for r in near if r['seam'] == 'plate-1904']
    L = [f"# Seam report, {meta['made'][:10]}" + (' (plates on the joint refit)' if JOINT else ''), '',
         f"Plate models: {meta['plate_models']}.", '',
         'Read only: every street crossing that two 1922 plates, or a 1922 plate and a 1904 frame, both show, and how far apart the '
         'two copies sit on the page. Nothing was fitted, rebuilt or changed. Method: `tools/sanborn/seams.py` (its docstring); '
         f"matched by street names within {meta['match_m']:.0f} m. Files: `seams.csv` (every pair), `per_pair.csv` (by plate and "
         'frame), `seams.json` (all of it, with the sha256 of every file read).', '',
         f"Read: {len(meta['plates'])} plates on the 1922 layer ({meta['crossings']['plates']} crossings), "
         f"{meta['frames']['deck_north']} 1904 deck and north frames ({meta['crossings']['frames_deck_north']} crossings), "
         f"{meta['frames']['basin']} 1904 basin frames ({meta['crossings']['frames_basin']} crossings).", '',
         '## Summary', '',
         '| Seam | Source pairs | Shared crossings | Median m | RMS m | 90% m | Max m | > 5 m | > 10 m | > 20 m | Same names 45-150 m |',
         '|---|---|---|---|---|---|---|---|---|---|---|']
    for s, v in summary.items():
        L.append(f"| {s} | {v['pairs_of_sources']} | {v['n']} | {v.get('median', '')} | {v.get('rms', '')} | {v.get('p90', '')} | "
                 f"{v.get('max', '')} | {v['over_5m']} | {v['over_10m']} | {v['over_20m']} | {v['same_names_45_150m']} |")
    L += ['', 'Plate against 1904, by how the frame is drawn:', '', '| 1904 frames | Shared crossings | Frames | Median m | 90% m | Max m |', '|---|---|---|---|---|---|']
    for lab, g in (('deck/north, bent onto 1922 (lph/tps.pkl)', [r for r in pf if 'bent' in r['b_set']]),
                   ('deck/north, not bent', [r for r in pf if r['b_set'] == 'deck/north']),
                   ('basin (sbg/fit/tf.json)', [r for r in pf if r['b_set'] == 'basin'])):
        d = np.array([r['dist_m'] for r in g])
        L.append(f"| {lab} | {len(g)} | {len({r['b_src'] for r in g})} | " + (f"{np.median(d):.2f} | {np.percentile(d, 90):.2f} | {d.max():.2f} |" if len(d) else '- | - | - |'))
    L += ['', '## Plate against plate', '', '| Plate | Plate | Shared | Median m | Max m | Mean shift E, N m |', '|---|---|---|---|---|---|']
    for p in per_pair:
        if p['seam'] == 'plate-plate':
            L.append(f"| {p['a']} | {p['b']} | {p['n']} | {p['median']} | {p['max']} | {p['mean_dE']:+.1f}, {p['mean_dN']:+.1f} |")
    L += ['', '## Plate against 1904 frames, by plate', '', '| Plate | Frames | Shared | Median m | 90% m | Max m |', '|---|---|---|---|---|---|']
    byp = collections.defaultdict(list)
    for r in pf:
        byp[r['a_src']].append(r)
    for k, g in sorted(byp.items()):
        d = np.array([r['dist_m'] for r in g])
        L.append(f"| {k} | {len({r['b_src'] for r in g})} | {len(g)} | {np.median(d):.2f} | {np.percentile(d, 90):.2f} | {d.max():.2f} |")
    for s, lab in (('plate-plate', 'plate against plate'), ('plate-1904', 'plate against 1904')):
        L += ['', f'## Widest 20, {lab}', '', '| m | Plate | Other | Crossing | dE, dN m |', '|---|---|---|---|---|']
        for r in sorted([r for r in near if r['seam'] == s], key=lambda r: -r['dist_m'])[:20]:
            other = r['b_src'] + (f" ({r['b_set']})" if r['b_set'] else '')
            L.append(f"| {r['dist_m']:.1f} | {r['a_src']} | {other} | {r['street_1']} & {r['street_2']} | {r['dE']:+.1f}, {r['dN']:+.1f} |")
    far = [r for r in rows if not r['within_45m']]
    L += ['', f"## Same street names, {meta['match_m']:.0f}-{meta['far_m']:.0f} m apart", '',
          'Either a seam that wide or two different crossings of the same two streets; not counted above.', '']
    L += [f"- {r['a_src']} / {r['b_src']}: {r['street_1']} & {r['street_2']}, {r['dist_m']:.1f} m" for r in far] or ['- none']
    L += ['', '## Notes', '',
          '- Plate positions come from the stored forward models (`fwd.pkl`); the page draws the plates through the inverse grids made '
          'from them on a 2 m grid, so the drawn position can differ by a fraction of a metre. Plate 35N is Ben\'s georeference as drawn.',
          '- The 1904 frames bent onto the 1922 plates were bent at these same crossings, so their small distances are by construction.',
          '- Placement checked against the workspace\'s own `cuf/x1904.json` (same frames, its pre-bend model): identical to 0.0 m on '
          '830 frame crossings and 360 plate crossings.',
          f"- Computed with Python {meta['versions']['python']}, numpy {meta['versions']['numpy']}, scipy {meta['versions']['scipy']}, "
          f"pyproj {meta['versions']['pyproj']} (the workspace's versions are not recorded).", '']
    open(os.path.join(out_dir, 'README.md'), 'w', encoding='utf8', newline='\n').write('\n'.join(L))


if __name__ == '__main__':
    main()
