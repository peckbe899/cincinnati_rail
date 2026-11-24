"""eval_v2: a pair of blank-guide networks end to end, on plate 44 (the benchmark) and plate 1A's validation region
(23 November 2026; data/sanborn/bench_2026-11-23/train).

    cd data/sanborn
    ../../tools/sanborn/unet/.venv/Scripts/python.exe -B ../../tools/sanborn/unet/eval_v2.py --area-model A.pt --lines-model L.pt --out DIR
        [--grids 0,1,2,3,4,5] [--no-44] [--no-1a] [--truth-1a STREETMAP.json] [--region-1a MASK.png]
        [--baseline-maps data/sanborn/bench44_maps] [--baseline-runs DIR] [--jobs 3] [--python python] [--cpu]

Nothing is trained, and plate 44 only scores: no choice is made on it here (the checkpoint was chosen on 1A's
validation region by the trainer). Everything goes into DIR; nothing is written in the repo.

1. The two maps, as blocks_noguide.predict makes them (the scan at half size, INTER_AREA, blank guide -> P(block),
   truncated to uint8; the full scan, its ink image, blank guide and that P(block) resized INTER_LINEAR -> P(line)),
   with the tile grid moved as data/sanborn/bench_2026-11-21/inference/make_maps44.py moves it (OFFS: the image
   reflected by the offset on the top and left, the map cropped back): grid0 is the batch's grid, gridK is OFFS[K-1],
   the grids of data/sanborn/bench44_maps (the baseline: area_ng1 + lines_ng1). Each grid's DIR/maps44/gridK/info.json
   says how far its decisions are from the baseline grid's (0 for the baseline's own networks: the faithfulness check).
2. Plate 44 end to end: tools/sanborn/unet/bench44.py --grids DIR/maps44 (the REAL merged outline step, outlines.py
   --area-png --lines-png --out; the real step 4; the editor's clean() and sheet()) paired with the baseline grids,
   run by the same bench44 into --baseline-runs (default DIR/runs_baseline44; a baseline run already there for the
   same map, by sha256, is reused). -> DIR/runs44/v2_grids.json: mean, sd, min, max of every headline score over the
   grids and the paired gains (this pair minus the baseline, grid by grid).
3. Plate 1A: the two maps on the batch's grid, then bench_plate.py (bench44's scorer on 1A, the region = 1A's
   validation region (train_v2/1A/valmask.png: right of Elm Street) as fold A) for this pair and for the batch's own maps of 1A (unet_data/1A_pred_area_ng1.png,
   1A_lines_lines_ng1.png). The truth is --truth-1a, or else made from Ben's edits as street_map.py makes a street map
   (bench_plate.py --make-truth, into DIR/truth/). The region is --region-1a, or else data/sanborn/train_v2/1A/valmask.png,
   or else the right-hand quarter (half size, x >= int(0.75 w)).
   NOTE: Ben's 1A lines were made by editing the batch's (area_ng1 + lines_ng1) lines: a line he left alone is exactly
   the batch's line. So on 1A the baseline starts with an advantage in line position; read the 1A numbers with that in
   mind. Fold B of 1A (outside the region) was trained on by the v2 networks: it is in sample for them.
4. DIR/eval_v2.json: everything above in one file, with the models' sha256 and json (seed, best iteration).
bench44 and bench_plate run under --python (default: the system python, which has scipy and shapely); the outline
step under the networks' venv, as the batch runs it. PYTHONDONTWRITEBYTECODE is set for every step.
"""
import argparse, hashlib, json, os, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import cv2
HERE = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/') + '/'; sys.path.insert(0, HERE); sys.path.insert(0, HERE + '..')
import _ws  # noqa: E402
SP = _ws.DATA; U = SP + 'unet_data/'; TOOLS = _ws.CODE + 'unet/'          # the repo's tools/sanborn/unet (bench44.py, outlines.py)
OFFS = [((160, 400), (300, 700)), ((320, 160), (640, 200)), ((480, 560), (100, 450)), ((240, 0), (520, 0)), ((0, 240), (0, 520))]   # make_maps44.py: (area offset half px, line offset full px)
GRID_OFFS = {0: (None, None), **{k: OFFS[k - 1] for k in range(1, 6)}}
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'


def sha(p, n=None):
    if not os.path.exists(p): return None
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()[:n] if n else h.hexdigest()


def log(*a): print(*a, flush=True)


def tool(name):
    """a script beside this file if it is there (the staged copies), else the repo's tools/sanborn/unet"""
    return HERE + name if os.path.exists(HERE + name) else TOOLS + name


def env():
    e = dict(os.environ); e['PYTHONDONTWRITEBYTECODE'] = '1'
    e['PYTHONPATH'] = os.pathsep.join([_ws.CODE.rstrip('/'), TOOLS.rstrip('/')] + ([e['PYTHONPATH']] if e.get('PYTHONPATH') else []))
    return e


def load_nets(area_pt, lines_pt, cpu):
    import torch, unet as A
    dev = torch.device('cpu') if cpu else A.device()
    na = A.UNet(); na.load_state_dict(torch.load(area_pt, map_location='cpu')); na.to(dev); na.eval()
    nl = A.UNet(classes=2, in_ch=7); nl.load_state_dict(torch.load(lines_pt, map_location='cpu')); nl.to(dev); nl.eval()
    return dev, na, nl


def maps(nets, full, oa=None, ol=None):
    """blocks_noguide.predict's two maps of a scan, with the tile grids moved by oa (half px) and ol (full px)"""
    import unet as A, edgenet as E
    dev, na, nl = nets; H, W = full.shape[:2]; t = {}
    def moved(fn, net, x, off):
        if off and (off[0] or off[1]):
            oy, ox = off; return fn(net, dev, cv2.copyMakeBorder(x, oy, 0, ox, 0, cv2.BORDER_REFLECT))[oy:, ox:]
        return fn(net, dev, x)
    t0 = time.time(); img = cv2.resize(full, (W // 2, H // 2), interpolation=cv2.INTER_AREA); z = np.zeros(img.shape[:2], np.uint8)
    pa = (moved(A.predict_full, na, np.dstack([img[:, :, ::-1], z, z]), oa) * 255).astype(np.uint8); t['area_s'] = round(time.time() - t0, 2)
    t1 = time.time(); inkimg, _ = E.ink_image(full); Z = np.zeros((H, W), np.uint8)
    x = np.dstack([full[:, :, ::-1], inkimg, Z, Z, cv2.resize(pa, (W, H), interpolation=cv2.INTER_LINEAR)]); del inkimg
    pl = (moved(E.predict_full, nl, x, ol) * 255).astype(np.uint8); t['lines_s'] = round(time.time() - t1, 2)
    return pa, pl, t


def differs(a, b):
    if b is None or a.shape != b.shape: return None
    return round(float(((a > 127) != (b > 127)).mean()), 6)


def run(cmd, what):
    t0 = time.time(); r = subprocess.run(cmd, cwd=SP, capture_output=True, text=True, encoding='utf8', errors='replace', env=env())
    if r.returncode: raise RuntimeError(f'{what} failed (exit {r.returncode}):\n{(r.stdout + r.stderr)[-3000:]}')
    return r, round(time.time() - t0, 1)


def headline_all(b): return {k: b[k] for k in ('PQ', 'SQ', 'RQ', 'matched', 'merges', 'fp', 'PQ_decided', 'recall_interior', 'precision', 'precision_green', 'ben_blocks_closed', 'intact_rings', 'delete_len', 'draw_len') if k in b}


def main():
    ap = argparse.ArgumentParser(description='eval_v2 (see the docstring)', allow_abbrev=False)
    ap.add_argument('--area-model', required=True); ap.add_argument('--lines-model', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--grids', default='0,1,2,3,4,5'); ap.add_argument('--no-44', action='store_true'); ap.add_argument('--no-1a', action='store_true')
    ap.add_argument('--truth-1a'); ap.add_argument('--region-1a'); ap.add_argument('--baseline-maps', default=SP + 'bench44_maps'); ap.add_argument('--baseline-runs')
    ap.add_argument('--jobs', type=int, default=3); ap.add_argument('--python', default='python'); ap.add_argument('--cpu', action='store_true')
    a = ap.parse_args()
    OUT = os.path.abspath(a.out).replace('\\', '/') + '/'; os.makedirs(OUT, exist_ok=True)
    BR = (os.path.abspath(a.baseline_runs).replace('\\', '/') + '/') if a.baseline_runs else OUT + 'runs_baseline44/'
    grids = [int(g) for g in a.grids.split(',') if g.strip()]
    if any(g not in GRID_OFFS for g in grids): sys.exit(f'--grids: 0 to 5 only ({a.grids})')
    stale = sorted(set(os.listdir(OUT + 'maps44')) - {f'grid{g}' for g in grids}) if os.path.isdir(OUT + 'maps44') else []
    if stale and not a.no_44: sys.exit(f'{OUT}maps44 holds other grids ({stale}) from an earlier run; bench44 --grids would score them too: use a new --out')
    mj = lambda pt: (pt[:-3] + '.json') if os.path.exists(pt[:-3] + '.json') else (pt[:-8] + '.json' if pt.endswith('_last.pt') and os.path.exists(pt[:-8] + '.json') else None)
    def model_info(pt):
        j = mj(pt); d = json.load(open(j, encoding='utf8')) if j else {}
        return dict(file=os.path.abspath(pt), sha256=sha(pt), json=j, seed=d.get('seed'), best=d.get('best'), data=d.get('data'), manifest_sha256=d.get('manifest_sha256'), plates=[p.get('spec') if isinstance(p, dict) else p for p in d.get('plates', [])])
    res = dict(made=time.strftime('%Y-%m-%d %H:%M:%S'), out=OUT, models=dict(area=model_info(a.area_model), lines=model_info(a.lines_model)), eval_v2=dict(file=os.path.abspath(__file__), sha256=sha(os.path.abspath(__file__))),
               grids=grids, baseline_maps=a.baseline_maps, baseline_runs=BR, timings={})
    for m in res['models'].values():
        if any(str(p).split(':')[0].upper() in ('44', '90') for p in (m['plates'] or [])): log('WARNING: the model json lists 44 or 90 among its plates:', m['plates'])
    T0 = time.time(); nets = load_nets(a.area_model, a.lines_model, a.cpu); res['timings']['load_nets_s'] = round(time.time() - T0, 1)
    import unet as A_
    res['device'] = 'cpu' if a.cpu else getattr(A_.device, 'name', None)
    # ------------------------------------------------------------ plate 44
    if not a.no_44:
        full = cv2.imread(SP + 'cufp/22-44.jpg'); g44 = {}
        for g in grids:
            oa, ol = GRID_OFFS[g]; d = OUT + f'maps44/grid{g}/'; os.makedirs(d, exist_ok=True)
            pa, pl, t = maps(nets, full, oa, ol); cv2.imwrite(d + '44_area.png', pa); cv2.imwrite(d + '44_lines.png', pl)
            ba = cv2.imread(os.path.join(a.baseline_maps, f'grid{g}', '44_area.png'), 0); bl = cv2.imread(os.path.join(a.baseline_maps, f'grid{g}', '44_lines.png'), 0)
            info = dict(grid=f'grid{g}', area_offset=oa, lines_offset=ol, seconds=t, area_block_share=round(float((pa > 127).mean()), 4), line_share=round(float((pl > 127).mean()), 5),
                        area_decision_differs_from_baseline=differs(pa, ba), lines_decision_differs_from_baseline=differs(pl, bl),
                        area_identical_to_baseline=bool(ba is not None and np.array_equal(pa, ba)), lines_identical_to_baseline=bool(bl is not None and np.array_equal(pl, bl)))
            json.dump(info, open(d + 'info.json', 'w'), indent=1); g44[f'grid{g}'] = info; log('44', json.dumps(info))
            del pa, pl, ba, bl
        del full; res['maps44'] = g44
        # the baseline runs (reused when there for the same map)
        def base(g):
            r = BR + f'base__grid{g}/bench44.json'; am = os.path.join(a.baseline_maps, f'grid{g}', '44_area.png'); lm = os.path.join(a.baseline_maps, f'grid{g}', '44_lines.png')
            if os.path.exists(r):
                m = json.load(open(r, encoding='utf8'))['meta']
                if m.get('area_sha') == sha(am, 16) and m.get('lines_sha') == sha(lm, 16): return g, 'reused', 0
            _, s = run([a.python, '-B', TOOLS + 'bench44.py', '--area', am, '--lines', lm, '--tag', f'base__grid{g}', '--runs', BR, '--no-pic'], f'baseline bench44 grid{g}')
            return g, 'run', s
        t0 = time.time()
        with ThreadPoolExecutor(a.jobs) as ex: bres = list(ex.map(base, grids))
        res['timings']['baseline44_s'] = round(time.time() - t0, 1); res['baseline44_runs'] = {f'grid{g}': how for g, how, _ in bres}; log('baseline 44:', res['baseline44_runs'])
        t0 = time.time()
        run([a.python, '-B', TOOLS + 'bench44.py', '--grids', OUT + 'maps44', '--tag', 'v2', '--runs', OUT + 'runs44', '--jobs', str(a.jobs), '--paired', BR + 'base__{grid}/bench44.json'], 'bench44 --grids')
        res['timings']['bench44_grids_s'] = round(time.time() - t0, 1)
        G = json.load(open(OUT + 'runs44/v2_grids.json', encoding='utf8'))
        base_h = {g: json.load(open(BR + f'base__{g}/bench44.json', encoding='utf8'))['headline'] for g in G['meta']['grids']}
        st = lambda v: dict(mean=round(float(np.mean(v)), 4), sd=round(float(np.std(v, ddof=1)), 4) if len(v) > 1 else None)
        res['bench44'] = dict(grids=G['meta']['grids'], v2=G['headline'], paired=G.get('paired'),
                              baseline={f: {k: st([base_h[g][f][k] for g in base_h]) for k in base_h[next(iter(base_h))][f] if all(base_h[g][f][k] is not None for g in base_h)} for f in ('all', 'A', 'B')},
                              per_grid={g: dict(v2=headline_all(G['per_grid'][g]['all']), baseline=headline_all(base_h[g]['all'])) for g in G['meta']['grids']})
    # ------------------------------------------------------------ plate 1A
    if not a.no_1a:
        full = cv2.imread(SP + 'cufp/22-1A.jpg'); H, W = full.shape[:2]; d = OUT + 'maps1A/'; os.makedirs(d, exist_ok=True)
        pa, pl, t = maps(nets, full); cv2.imwrite(d + '1A_area.png', pa); cv2.imwrite(d + '1A_lines.png', pl); del full
        res['maps1A'] = dict(seconds=t, area_block_share=round(float((pa > 127).mean()), 4), line_share=round(float((pl > 127).mean()), 5),
                             area_decision_differs_from_batch=differs(pa, cv2.imread(U + '1A_pred_area_ng1.png', 0)), lines_decision_differs_from_batch=differs(pl, cv2.imread(U + '1A_lines_lines_ng1.png', 0)))
        del pa, pl
        if a.truth_1a: truth = os.path.abspath(a.truth_1a); how = 'given (--truth-1a)'
        else:
            truth = OUT + 'truth/22-1A.json'; r, _ = run([a.python, '-B', tool('bench_plate.py'), '--make-truth', '1A', truth], 'the 1A street map'); how = 'made from picks22_guided/22-1A/edges_ben.json as street_map.py makes one: ' + r.stdout.strip().splitlines()[-1]
        if a.region_1a: region = os.path.abspath(a.region_1a); rhow = 'given (--region-1a)'
        elif os.path.exists(SP + 'train_v2/1A/valmask.png'): region = SP + 'train_v2/1A/valmask.png'; rhow = 'train_v2/1A/valmask.png'
        else:
            h2, w2 = H // 2, W // 2; m = np.zeros((h2, w2), np.uint8); m[:, int(w2 * 0.75):] = 255; region = OUT + 'truth/1A_valmask.png'; os.makedirs(OUT + 'truth', exist_ok=True); cv2.imwrite(region, m)
            rhow = 'the right-hand quarter (x >= int(0.75 w) at half size), made here'
        res['truth1A'] = dict(file=truth, sha256=sha(truth), how=how, region=region, region_sha256=sha(region), region_how=rhow)
        def bp(tag, am, lm):
            r, s = run([a.python, '-B', tool('bench_plate.py'), '--plate', '1A', '--truth', truth, '--region', region, '--area', am, '--lines', lm, '--tag', tag, '--runs', OUT + 'runs1A'], f'bench_plate 1A {tag}')
            return json.loads(r.stdout.strip().splitlines()[-1]), s
        t0 = time.time()
        with ThreadPoolExecutor(2) as ex:
            fv = ex.submit(bp, 'v2_1A', d + '1A_area.png', d + '1A_lines.png'); fb = ex.submit(bp, 'batch_1A', U + '1A_pred_area_ng1.png', U + '1A_lines_lines_ng1.png')
            (v, _), (b, _) = fv.result(), fb.result()
        res['timings']['bench1A_s'] = round(time.time() - t0, 1)
        diff = {f: {k: (round(v['headline'][f][k] - b['headline'][f][k], 4) if isinstance(v['headline'][f].get(k), (int, float)) and isinstance(b['headline'][f].get(k), (int, float)) else None) for k in v['headline'][f]} for f in ('region', 'outside', 'all')}
        res['bench1A'] = dict(region_blocks=v['region_blocks'], v2=v['headline'], batch_ng1=b['headline'], v2_minus_batch=diff, runs=dict(v2=v['run'], batch=b['run']),
                              note='region = the validation region (out of sample for v2); outside = trained on by v2 (in sample); the truth is anchored to the batch lines')
    res['timings']['total_s'] = round(time.time() - T0, 1)
    json.dump(res, open(OUT + 'eval_v2.json', 'w', encoding='utf8', newline='\n'), indent=1)
    # a short table
    if 'bench44' in res:
        B = res['bench44']; log('\nplate 44 over grids', B['grids'])
        for k in ('PQ', 'PQ_decided', 'recall_interior', 'precision', 'ben_blocks_closed', 'merges', 'fp'):
            v, bs, p = B['v2']['all'].get(k), B['baseline']['all'].get(k), (B['paired'] or {}).get('all', {}).get(k)
            log(f'  {k:16s} v2 {v and v["mean"]} (sd {v and v["sd"]})  baseline {bs and bs["mean"]}  paired gain {p and p["mean"]} ({p and p["gains"]}/{p and p["of"]} grids up)')
    if 'bench1A' in res:
        B = res['bench1A']; log(f'\nplate 1A validation region ({B["region_blocks"]} of Ben\'s blocks by centroid)')
        for k in ('PQ', 'PQ_decided', 'recall_interior', 'precision', 'ben_blocks_closed'):
            log(f'  {k:16s} v2 {B["v2"]["region"].get(k)}  batch {B["batch_ng1"]["region"].get(k)}')
    log('wrote', OUT + 'eval_v2.json')


if __name__ == '__main__':
    main()
