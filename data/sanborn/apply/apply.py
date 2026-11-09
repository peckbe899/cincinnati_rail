"""Apply the 1922 plate models (Ben, 7 November 2026): fwd_complete.pkl for every plate but 37L and 37R, fwd_local3.pkl
for those two; no refit.

    cd data/sanborn
    python apply/apply.py STAGE

The pipeline's own scripts (tools/sanborn) read each plate's old model directly (fwdlib, fwd38lib, common.px2ben /
ben2px, cuf/plates.py's inverse grids). This runner leaves them unchanged: it routes those calls to the new models
(tools/sanborn/joint/jointlib.py, TAGS below) at import time, then runs the scripts as they are (runpy). It lives in
data/sanborn because the ruling's scope for this step is data/sanborn, the tiles and the page's basin.json / plots.json.

Stages, in order:
  grids    each plate's world -> pixel grid from its new model (2 m, as cufp/fit.py writes model.npz): apply/inv/<pid>.npz
  stage    the page's files into deckpage/ (the scripts' page folder in the workspace layout) from hub/sites/deck, and
           Ben's live layout (hub/seed/deck/layout.json) into dbread/deck/layout.json, the copy the builders read
  x1904    cuf/x1904.py: the 1904 crossings matched to the 1922 crossings, now placed by the new models
  bend     cuf/tps1922.py on every frame bent onto the 1922 plates (cuf/tps1922_report.json), all solved together
  streets  the plate street sets taken out newest first and rebuilt in their order (rebuild_streets.sh's plate steps),
           ids carried over (carry_ids), checked against Ben's layout; basin.json back to hub/sites/deck
  tiles    hub/sites/deck/tiles_22 re-composited tile by tile, plates in cuf/plates.py order, deepest inside its plate wins
  seams    the seam report on the applied state (tools/sanborn/seams.py, the new models), against reports/2026-11-06_seams
Backups of everything replaced go to apply/backup/.
"""
import collections, datetime, glob, json, os, pickle, runpy, shutil, sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'sanborn'))
import _ws  # noqa: E402

SP, CODE = _ws.DATA, _ws.CODE
for _d in ('cuf', 'cufp', 'cuf38', 'sbg', 'lph', 'joint'):
    sys.path.insert(0, CODE + _d)
DECK = os.path.join(REPO, 'hub', 'sites', 'deck') + '/'
BK = HERE + '/backup/'
STAGED = ('basin.json', 'deck.json', 'tracks.json', 'context.json', 'plots.json')
LOCAL = ('22-37L', '22-37R')
STEP = 2.0
# the plate street sets in the order they were built (tools/sanborn/cuf/rebuild_streets.sh, plate steps only; the
# 1904-frame sets, Millvale and the w1 OSM set are not plate sets and stay as installed)
SETS = [('c22', 'cuf/build22.py', [], 'cuf/c22_removed.json'), ('c38', 'cuf38/build38.py', [], 'cuf38/c38_removed.json')] + \
       [(f'c{n}', 'cufp/build.py', [n], f'cufp/{n}/removed.json') for n in ('66', '68', '67', '69', '70', '82A', '83A', '75', '76', '29', '26A', '26B', '31', '33')]


def tag(pid):
    return 'local3' if pid in LOCAL else 'complete'


def backup(rel, base=SP):
    src = base + rel
    if os.path.exists(src):
        dst = BK + rel
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if not os.path.exists(dst):
            (shutil.copytree if os.path.isdir(src) else shutil.copy2)(src, dst)


# ------------------------------------------------------------------ routing
_INSTALLED = False


def install():
    """route the old-model calls to the new models (once per process)"""
    global _INSTALLED
    if _INSTALLED:
        return
    import fwdlib, fwd38lib, common as C, plates, jointlib as J
    orig = dict(fw=fwdlib.world_many, f38m=fwd38lib.world_many, p2b=C.px2ben, b2p=C.ben2px,
                inv={P['id']: P['inv'] for P in plates.PLATES})

    def base_many(pid, q):                      # the old models, as jointlib reads them (local3 is built on them)
        q = np.asarray(q, float).reshape(-1, 2)
        if pid == '22-35N':
            E, N = orig['p2b'](q[:, 0], q[:, 1]); return np.c_[E, N]
        if pid == '22-38':
            return orig['f38m'](q)
        return orig['fw'](pid[3:], q)
    J.base_many = base_many
    J.base_inv = lambda pid, E, N: orig['inv'][pid](E, N)

    def new(pid, q):
        if not J.has(pid, tag(pid)):            # a plate not applied yet (its own fit, as the page would draw it)
            return base_many(pid, q)
        return J.world_many(pid, np.asarray(q, float).reshape(-1, 2), tag(pid))
    fwdlib.world_many = lambda n, q: new('22-' + str(n), q)
    fwd38lib.world_many = lambda q: new('22-38', q)
    fwd38lib.world = lambda x, y: tuple(float(v) for v in new('22-38', [[x, y]])[0])

    def px2ben(x, y):
        x = np.asarray(x, float); y = np.asarray(y, float); W = new('22-35N', np.c_[x.ravel(), y.ravel()])
        return W[:, 0].reshape(x.shape), W[:, 1].reshape(x.shape)
    C.px2ben = px2ben
    C.ben2px = lambda E, N: grid_inv('22-35N')(E, N)
    for P in plates.PLATES:
        if os.path.exists(HERE + f"/inv/{P['id']}.npz"):
            P['inv'] = grid_inv(P['id'])
    import seams as S                           # seams.py imports common, fwdlib and fwd38lib by name: the same modules
    _INSTALLED = True


_G = {}


def grid_inv(pid):
    import cv2

    def inv(E, N):
        if pid not in _G:
            _G[pid] = dict(np.load(HERE + f'/inv/{pid}.npz'))
        g = _G[pid]; E = np.asarray(E, float); N = np.asarray(N, float)
        fx = ((E - g['E0']) / g['step']).astype(np.float32); fy = ((g['N1'] - N) / g['step']).astype(np.float32)
        px = cv2.remap(g['px'], fx, fy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=-1e6)
        py = cv2.remap(g['py'], fx, fy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=-1e6)
        return px, py
    return inv


def run_script(rel, argv):
    install()
    old = sys.argv; sys.argv = [CODE + rel] + list(argv)
    try:
        runpy.run_path(CODE + rel, run_name='__main__')
    finally:
        sys.argv = old


# ------------------------------------------------------------------ stages
def st_grids():
    from scipy.interpolate import griddata
    import jointlib as J
    import seams as S
    import importlib.util
    spec = importlib.util.spec_from_file_location('joint_solve', CODE + 'joint/solve.py'); SV = importlib.util.module_from_spec(spec); spec.loader.exec_module(SV)
    install()
    os.makedirs(HERE + '/inv', exist_ok=True)
    rep = {}
    for pid in S.plate_ids():
        w, h = SV.plate_size(pid)
        gx, gy = np.meshgrid(np.arange(0, w + 16, 16.0), np.arange(0, h + 16, 16.0)); Q = np.c_[gx.ravel(), gy.ravel()]
        Wd = J.world_many(pid, Q, tag(pid))
        E0, N0 = np.floor(Wd.min(0) / STEP) * STEP - 10; E1, N1 = np.ceil(Wd.max(0) / STEP) * STEP + 10
        ge, gn = np.meshgrid(np.arange(E0, E1, STEP), np.arange(N1, N0, -STEP))
        px = griddata(Wd, Q[:, 0], (ge, gn), method='linear'); py = griddata(Wd, Q[:, 1], (ge, gn), method='linear')
        px = np.where(np.isnan(px), -1e6, px).astype(np.float32); py = np.where(np.isnan(py), -1e6, py).astype(np.float32)
        np.savez_compressed(HERE + f'/inv/{pid}.npz', E0=E0, N1=N1, step=STEP, px=px, py=py)
        # round trip at the plate's controls, as a check of the grid
        d = pickle.load(open(SP + J.joint_path(pid, tag(pid)), 'rb'))
        X = np.asarray(d.get('controls_X') or [], float).reshape(-1, 2)
        if not len(X):
            X = Q[::97]
        Wx = J.world_many(pid, X, tag(pid)); _G.pop(pid, None)
        bx, by = grid_inv(pid)(Wx[:, 0], Wx[:, 1])
        err = np.hypot(np.asarray(bx).ravel() - X[:, 0], np.asarray(by).ravel() - X[:, 1])
        rep[pid] = dict(model=J.joint_path(pid, tag(pid)), grid=list(px.shape), roundtrip_px_median=round(float(np.median(err)), 2), roundtrip_px_max=round(float(err.max()), 2))
        print(pid, rep[pid], flush=True)
    json.dump(rep, open(HERE + '/inv/report.json', 'w'), indent=1)


def st_stage():
    os.makedirs(SP + 'deckpage', exist_ok=True)
    for f in STAGED:
        if os.path.exists(DECK + f):
            os.makedirs(BK + 'deck_site', exist_ok=True)
            if not os.path.exists(BK + 'deck_site/' + f):
                shutil.copy2(DECK + f, BK + 'deck_site/' + f)
            shutil.copy2(DECK + f, SP + 'deckpage/' + f)
    backup('dbread/deck/layout.json')
    shutil.copy2(os.path.join(REPO, 'hub', 'seed', 'deck', 'layout.json'), SP + 'dbread/deck/layout.json')
    print('staged', [f for f in STAGED if os.path.exists(SP + 'deckpage/' + f)], 'and Ben\'s layout from hub/seed')


def st_x1904():
    backup('cuf/x1904.json')
    frames = list(dict.fromkeys(r['fr'] for r in json.load(open(BK + 'cuf/x1904.json'))))      # the frames it was run on, in order
    print('1904 frames', len(frames))
    run_script('cuf/x1904.py', [','.join(frames)])


def st_bend():
    backup('lph/tps.pkl'); backup('cuf/tps1922_report.json')
    frames = list(json.load(open(BK + 'cuf/tps1922_report.json' if os.path.exists(BK + 'cuf/tps1922_report.json') else SP + 'cuf/tps1922_report.json')))
    print('bent frames', len(frames), frames)
    run_script('cuf/tps1922.py', [','.join(frames)])


def st_alpha():
    """the scans' alpha masks the plate builds read (cufp/<N>/png_alpha_s4.npy, cuf38/png_alpha_s4.npy), made as
    tools/sanborn/cufp/prep.py makes them (alpha > 0, every 4th pixel); derived files, not exported with the repo"""
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    cfg = json.load(open(SP + 'cufp/config.json'))
    todo = [('cuf38/png_alpha_s4.npy', '/mnt/user-data/uploads/38.png')]
    for s, script, args, rem in SETS:
        if args:
            n = args[0]; todo.append((f'cufp/{n}/png_alpha_s4.npy', cfg.get(n, {}).get('png') or f'/mnt/user-data/uploads/PNG/{n}.png'))
    for rel, png in todo:
        if os.path.exists(SP + rel):
            continue
        a = np.array(Image.open(_ws.ext(png)).convert('RGBA'))[:, :, 3]
        os.makedirs(os.path.dirname(SP + rel), exist_ok=True)
        np.save(SP + rel, (a[::4, ::4] > 0).astype(np.uint8)); print('made', rel, a.shape, flush=True)


def st_streets(start=None):
    """take the plate sets out newest first, then rebuild them in order; after each set's build its streets and blocks
    get back the ids they had (carry_set), so the next build sees Ben's edits on the right features. Starts from the
    page's basin.json as staged (apply/basin_before.json) and the removal files as they were (apply/backup)."""
    if not os.path.exists(HERE + '/basin_before.json'):
        shutil.copy2(SP + 'deckpage/basin.json', HERE + '/basin_before.json')
    shutil.copy2(HERE + '/basin_before.json', SP + 'deckpage/basin.json')
    for s, script, args, rem in SETS:                       # removal files as they were before any take-out
        if os.path.exists(BK + rem):
            shutil.copy2(BK + rem, SP + rem)
        if os.path.exists(SP + rem.replace('.json', '_prev.json')):
            os.remove(SP + rem.replace('.json', '_prev.json'))
    B0 = json.load(open(HERE + '/basin_before.json'))
    BJ = json.loads(json.dumps(B0))
    for s, script, args, rem in reversed(SETS):
        if not os.path.exists(SP + rem):
            print('no removal file', rem); continue
        R0 = json.load(open(SP + rem)); ids = {f['properties']['id'] for f in R0['features']}
        n0 = len(BJ['features'])
        BJ['features'] = [f for f in BJ['features'] if f['properties'].get('set') != s and f['properties'].get('id') not in ids] + R0['features']
        os.replace(SP + rem, SP + rem.replace('.json', '_prev.json'))
        print('took out', s, n0, '->', len(BJ['features']), flush=True)
    json.dump(BJ, open(SP + 'deckpage/basin.json', 'w'), separators=(',', ':'))
    report = {}
    for s, script, args, rem in SETS:
        print('build', s, flush=True)
        run_script(script, args + ['--install'])
        report[s] = carry_set(s, B0)
        print('  ids', report[s], flush=True)
    finish(B0, report)


def ben_ids():
    LAY = json.load(open(SP + 'dbread/deck/layout.json', encoding='utf8'))
    return LAY, set(LAY.get('streets', {})) | set(LAY.get('blocks', {}))


def carry_set(s, B0):
    """the set's rebuilt streets and blocks get the ids the set's features had before: streets by name, then nearest
    (mean distance of 21 points of the new line to the old line, under 40 m), blocks by overlap (IoU over 0.3); ids in
    Ben's layout claim first. The rest get fresh numbers above the prefix's highest."""
    from shapely.geometry import shape
    _, BEN = ben_ids()
    B1 = json.load(open(SP + 'deckpage/basin.json'))
    O = [f for f in B0['features'] if f['properties'].get('set') == s and f['properties'].get('id')]
    Nw = [f for f in B1['features'] if f['properties'].get('set') == s]
    rs = {}
    remap = {}
    for layer in ('street', 'block'):
        Ol = [f for f in O if f['properties']['layer'] == layer]; Nl = [f for f in Nw if f['properties']['layer'] == layer]
        go = [shape(o['geometry']) for o in Ol]
        pairs = []
        for i, f in enumerate(Nl):
            g = shape(f['geometry'])
            pts = [g.interpolate(t, normalized=True) for t in np.linspace(0, 1, 21)] if layer == 'street' else None
            for j, o in enumerate(Ol):
                if layer == 'street':
                    if o['properties'].get('name') != f['properties'].get('name'):
                        continue
                    d = float(np.mean([go[j].distance(p) for p in pts]))
                    if d < 40:
                        pairs.append((o['properties']['id'] not in BEN, d, i, j))
                elif g.intersects(go[j]):
                    ov = g.intersection(go[j]).area / max(g.union(go[j]).area, 1e-9)
                    if ov > 0.3:
                        pairs.append((o['properties']['id'] not in BEN, 1 - ov, i, j))
        tn, to = set(), set()
        for nb, d, i, j in sorted(pairs):
            if i in tn or j in to:
                continue
            tn.add(i); to.add(j); remap[id(Nl[i])] = Ol[j]['properties']['id']
        rs[layer] = dict(old=len(Ol), new=len(Nl), carried=len(tn), fresh=len(Nl) - len(tn), old_unmatched=len(Ol) - len(to),
                         ben_unmatched=sorted(Ol[j]['properties']['id'] for j in range(len(Ol)) if j not in to and Ol[j]['properties']['id'] in BEN))
    taken = {f['properties'].get('id') for f in B1['features'] if f['properties'].get('set') != s} | set(remap.values())
    known = taken | {f['properties'].get('id') for f in B0['features']}
    nxt = {}
    for f in Nw:
        fid = remap.get(id(f))
        if fid is None:
            pre = ''.join(ch for ch in f['properties']['id'] if not ch.isdigit())
            if pre not in nxt:
                nxt[pre] = max([int(x[len(pre):]) for x in known if x and x.startswith(pre) and x[len(pre):].isdigit()] + [0]) + 1
            fid = f'{pre}{nxt[pre]:04d}'; nxt[pre] += 1
        f['properties']['id'] = fid
    json.dump(B1, open(SP + 'deckpage/basin.json', 'w'), separators=(',', ':'))
    return rs


def finish(B0, report):
    """every id in Ben's layout that the page had must still be there: one the rebuild left without a counterpart is
    kept as it was (it carries Ben's own geometry or his deletion, which the page draws in its place); then the check"""
    B1 = json.load(open(SP + 'deckpage/basin.json'))
    LAY, BEN = ben_ids()
    have = {f['properties'].get('id') for f in B1['features']}
    kept_old = []
    for f in B0['features']:
        fid = f['properties'].get('id')
        if fid in BEN and fid not in have:
            g = json.loads(json.dumps(f)); g['properties']['kept_for_edit'] = "apply 2026-11-07: no rebuilt counterpart; kept for Ben's edit"
            B1['features'].append(g)
            kept_old.append(dict(id=fid, name=f['properties'].get('name'), set=f['properties'].get('set'),
                                 edit=sorted(LAY['streets'].get(fid) or LAY['blocks'].get(fid) or {})))
    ids = [f['properties'].get('id') for f in B1['features'] if f['properties'].get('id')]
    dup = [k for k, v in collections.Counter(ids).items() if v > 1]
    json.dump(B1, open(SP + 'deckpage/basin.json', 'w'), separators=(',', ':'))
    report['_kept_for_edit'] = kept_old
    check_ben(B0, B1, report, dup)


def carry_ids():
    finish(json.load(open(HERE + '/basin_before.json')), {})


def check_ben(B0, B1, report, dup):
    from shapely.geometry import shape
    LAY = json.load(open(SP + 'dbread/deck/layout.json', encoding='utf8'))
    by0 = {f['properties']['id']: f for f in B0['features'] if f['properties'].get('id')}; by1 = {f['properties']['id']: f for f in B1['features'] if f['properties'].get('id')}
    missing, renamed, moves = [], [], []
    for layer, key in (('streets', 'street'), ('blocks', 'block')):
        for fid, e in LAY.get(layer, {}).items():
            if fid not in by0:
                continue                                   # an edit on a feature the page does not have (his own additions)
            if fid not in by1:
                missing.append(dict(id=fid, layer=key, name=by0[fid]['properties'].get('name'), edit=e)); continue
            n0, n1 = by0[fid]['properties'].get('name'), by1[fid]['properties'].get('name')
            if key == 'street' and n0 != n1:
                renamed.append(dict(id=fid, before=n0, after=n1))
            g0, g1 = shape(by0[fid]['geometry']), shape(by1[fid]['geometry'])
            if key == 'street':
                pts = [g1.interpolate(t, normalized=True) for t in np.linspace(0, 1, 41)]
                dm = [g0.distance(p) for p in pts]
                d = dict(id=fid, layer=key, name=n1, set=by1[fid]['properties'].get('set'), mean_m=round(float(np.mean(dm)), 2),
                         max_m=round(float(max(g0.hausdorff_distance(g1), 0)), 2), ben_edit=sorted(e) if isinstance(e, dict) else str(e))
            else:
                d = dict(id=fid, layer=key, name=n1, set=by1[fid]['properties'].get('set'),
                         mean_m=round(float(g0.centroid.distance(g1.centroid)), 2), max_m=round(float(g0.hausdorff_distance(g1)), 2),
                         ben_edit=sorted(e) if isinstance(e, dict) else str(e))
            if d['max_m'] > 0.01:
                moves.append(d)
    moves.sort(key=lambda d: -d['max_m'])
    out = dict(made=datetime.datetime.now().isoformat(timespec='seconds'), sets=report, duplicate_ids=dup, ben_missing=missing,
               ben_renamed=renamed, ben_moved=moves, layout='hub/seed/deck/layout.json (staged as dbread/deck/layout.json)')
    json.dump(out, open(HERE + '/streets_report.json', 'w', encoding='utf8', newline='\n'), indent=1)
    print(json.dumps(dict(sets=report, duplicate_ids=dup, ben_missing=len(missing), ben_renamed=len(renamed), ben_moved=len(moves)), indent=1))


def st_install_basin():
    for f in ('basin.json', 'plots.json'):
        a, b = SP + 'deckpage/' + f, DECK + f
        if os.path.exists(a) and (not os.path.exists(b) or open(a, 'rb').read() != open(b, 'rb').read()):
            shutil.copy2(a, b); print('installed', f)


# ------------------------------------------------------------------ tiles
def st_tiles():
    """tools/sanborn/cuf/tiles22.py's composite (deepest inside its plate wins), done tile by tile from per-plate
    renders on disk (the full render holds every tile at once and runs out of memory), plates in cuf/plates.py order"""
    import cv2
    from PIL import Image
    from scipy import ndimage as ndi
    install()
    import plates as PL
    Image.MAX_IMAGE_PIXELS = None
    OUT = DECK + 'tiles_22/'; TMP = HERE + '/tiles_tmp/'; os.makedirs(TMP, exist_ok=True)
    if not os.path.exists(BK + 'tiles_22'):
        shutil.copytree(OUT, BK + 'tiles_22')
    T, RES = 512, 0.25; NP = int(T / RES)
    jj, ii = np.meshgrid(np.arange(NP), np.arange(NP))
    order = [P for P in PL.PLATES if P['ok']()]
    for k, P in enumerate(order):
        IM = P['img'](); h, w = IM.shape[:2]
        D8 = ndi.distance_transform_edt(IM[::8, ::8, 3] > 127).astype(np.float32) * 8
        gx, gy = np.meshgrid(np.arange(700000, 725000, 16.0), np.arange(4324000, 4342000, 16.0))
        px, py = P['inv'](gx, gy); px = np.asarray(px); py = np.asarray(py)
        okk = (px >= 0) & (py >= 0) & (px < w - 1) & (py < h - 1)
        a = np.zeros_like(okk); a[okk] = IM[py[okk].astype(int), px[okk].astype(int), 3] > 0
        tiles = sorted({(int(e // T * T), int(n // T * T)) for e, n in zip(gx[a], gy[a])})
        print(P['id'], 'tiles', len(tiles), flush=True)
        for tx, ty in tiles:
            E = tx + (jj + 0.5) * RES; N = ty + T - (ii + 0.5) * RES
            qx, qy = P['inv'](E, N)
            rgba = cv2.remap(IM, np.asarray(qx, np.float32), np.asarray(qy, np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
            rgba[..., 3] = np.where(rgba[..., 3] > 127, 255, 0).astype(np.uint8)
            if not rgba[..., 3].any():
                continue
            d = cv2.remap(D8, np.asarray(qx, np.float32) / 8, np.asarray(qy, np.float32) / 8, cv2.INTER_NEAREST, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
            np.savez(TMP + f'{tx}_{ty}__{k:02d}.npz', rgba=rgba, d=d.astype(np.float16))
        del IM
    for f in os.listdir(OUT):
        if f.endswith('.webp'):
            os.remove(OUT + f)
    by = collections.defaultdict(list)
    for f in sorted(os.listdir(TMP)):
        t, k = f[:-4].split('__'); by[t].append(f)
    keep = []
    for t in sorted(by):
        base = np.zeros((NP, NP, 4), np.uint8); bd = np.zeros((NP, NP), np.float16)
        for f in sorted(by[t]):                                  # fixed plate order
            z = np.load(TMP + f); rgba, d = z['rgba'], z['d']
            take = (rgba[..., 3] > 0) & (d > bd)
            base[take] = rgba[take]; bd[take] = d[take]
        if not (base[..., 3] > 0).any():
            continue
        tx, ty = map(int, t.split('_'))
        Image.fromarray(base, 'RGBA').save(OUT + f'{tx}_{ty}.webp', quality=72, method=4); keep.append([tx, ty])
    keep.sort(key=lambda t: (t[1], t[0])); json.dump(dict(size=T, res=RES, tiles=keep), open(OUT + 'index.json', 'w'))
    ex = [min(t[0] for t in keep), min(t[1] for t in keep), max(t[0] for t in keep) + T, max(t[1] for t in keep) + T]
    sc = int(2.0 / RES); W, H = int((ex[2] - ex[0]) / 2.0), int((ex[3] - ex[1]) / 2.0); ov = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    for tx, ty in keep:
        im = Image.open(OUT + f'{tx}_{ty}.webp').convert('RGBA').resize((NP // sc, NP // sc), Image.LANCZOS); ov.paste(im, (int((tx - ex[0]) / 2.0), int((ex[3] - ty - T) / 2.0)), im)
    ov.save(OUT + 'overview.webp', quality=70, method=4); json.dump(dict(E0=ex[0], N0=ex[1], E1=ex[2], N1=ex[3], res=2), open(OUT + 'overview.json', 'w'))
    shutil.rmtree(TMP)
    print('tiles_22', len(keep), 'overview', W, H, ex)


# ------------------------------------------------------------------ seams
def st_seams():
    install()
    import seams as S
    S.READ.clear()
    out = SP + f'reports/{datetime.date.today().isoformat()}_seams_applied'
    S.main([out])
    sys.path.insert(0, CODE + 'joint')
    import local as LC
    plates = S.plate_ids()
    a = json.load(open(out + '/seams.json', encoding='utf8')); b = json.load(open(SP + 'reports/2026-11-06_seams/seams.json', encoding='utf8'))
    cmp = {}
    for name, d in (('before', b), ('after', a)):
        st = LC.seam_stats(d['seams'], plates)
        cmp[name] = dict(plate_plate=st['all'], plate_1904=st['plate_1904_touching'])
    json.dump(cmp, open(out + '/compare_2026-11-06.json', 'w', encoding='utf8', newline='\n'), indent=1)
    print(json.dumps(cmp, indent=1))


if __name__ == '__main__':
    st = sys.argv[1]
    f = dict(grids=st_grids, stage=st_stage, x1904=st_x1904, bend=st_bend, alpha=st_alpha, streets=st_streets, ids=carry_ids,
             install_basin=st_install_basin, tiles=st_tiles, seams=st_seams)[st]
    f(*sys.argv[2:])
