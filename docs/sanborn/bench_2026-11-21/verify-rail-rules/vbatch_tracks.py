"""verify-rail-rules (21 Nov 2026): batch-wide check of rail-rules' track claims, with my own copies of the code.
For every batch plate except 44 and 1A:
  orig     orig/rail_tracks.py (cp of the repo's) on unet_data/N_bins.png, as its run(): must equal unet_data/N_rail_rule.json
  patched  patched/rail_tracks.py tracks() on the proposed bins (rail-rules/batch/N_bins.png where the KEY was found,
           else unet_data/N_bins.png): compared with rail-rules/batch/tracks/N_rail_rule.json
Counts railroad / streetcar tracks and length for batch and patched. Read-only on the repo; writes vbatch/vbatch.json.
    cd data/sanborn
    python bench_2026-11-21/verify-rail-rules/vbatch_tracks.py [-j 3]"""
import os, sys, re, json, time, importlib.util
from multiprocessing import Pool
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); RR = os.path.join(os.path.dirname(HERE), 'rail-rules'); OUT = os.path.join(HERE, 'vbatch')


def load(which):
    spec = importlib.util.spec_from_file_location('rt_' + which, os.path.join(HERE, which, 'rail_tracks.py')); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


RO, RP = load('orig'), load('patched')
J = lambda P, k: [dict(kind=k, src='rule', pts=[[round(float(x), 1), round(float(y), 1)] for x, y in p]) for p in P]


def st(tr): return {k: dict(n=sum(t['kind'] == k for t in tr), px=round(sum(RO.plen(t['pts']) for t in tr if t['kind'] == k))) for k in ('railroad', 'streetcar')}


def one(N):
    t0 = time.time(); Bb = cv2.imread(f'unet_data/{N}_bins.png', 0)
    batch = json.load(open(f'unet_data/{N}_rail_rule.json', encoding='utf8'))['tracks']
    orig = J(RO.railroad_tracks((Bb == 4).astype(np.uint8)), 'railroad') + J(RO.streetcar_tracks((Bb == 5).astype(np.uint8)), 'streetcar')
    kp = os.path.join(RR, 'batch', f'{N}_bins.png'); Bp = cv2.imread(kp, 0) if os.path.exists(kp) else Bb
    pat = RP.tracks(Bp); theirs = json.load(open(os.path.join(RR, 'batch', 'tracks', f'{N}_rail_rule.json')))['tracks']
    r = dict(plate=N, key_bins=os.path.exists(kp), orig_eq_batch=orig == batch, patched_eq_theirs=pat == theirs, batch=st(batch), patched=st(pat), secs=round(time.time() - t0))
    if os.path.exists(kp): r['bins_px_differ_from_batch'] = int((Bp != Bb).sum())
    print(json.dumps(r), flush=True); return r


if __name__ == '__main__':
    a = sys.argv[1:]; j = int(a[a.index('-j') + 1]) if '-j' in a else 3; os.makedirs(OUT, exist_ok=True)
    order = lambda n: (int(re.match(r'\d+', n).group()), n)
    P = [n for n in sorted(json.load(open('unet_data/run_plates.json', encoding='utf8')), key=order) if n not in ('44', '1A') and os.path.exists(f'unet_data/{n}_bins.png')]
    with Pool(j) as pool: R = pool.map(one, P, chunksize=1)
    S = dict(plates=len(R), orig_eq_batch=sum(r['orig_eq_batch'] for r in R), patched_eq_theirs=sum(r['patched_eq_theirs'] for r in R), key_bins=sum(r['key_bins'] for r in R),
             batch={k: dict(n=sum(r['batch'][k]['n'] for r in R), px=sum(r['batch'][k]['px'] for r in R)) for k in ('railroad', 'streetcar')},
             patched={k: dict(n=sum(r['patched'][k]['n'] for r in R), px=sum(r['patched'][k]['px'] for r in R)) for k in ('railroad', 'streetcar')},
             no_railroad_batch=sorted(r['plate'] for r in R if r['batch']['railroad']['n'] == 0), no_railroad_patched=sorted(r['plate'] for r in R if r['patched']['railroad']['n'] == 0),
             no_rail_batch=sorted(r['plate'] for r in R if r['batch']['railroad']['n'] + r['batch']['streetcar']['n'] == 0), no_rail_patched=sorted(r['plate'] for r in R if r['patched']['railroad']['n'] + r['patched']['streetcar']['n'] == 0),
             mismatches=[r['plate'] for r in R if not (r['orig_eq_batch'] and r['patched_eq_theirs'])])
    json.dump(dict(summary=S, plates=R), open(os.path.join(OUT, 'vbatch.json'), 'w'), indent=1); print(json.dumps(S, indent=1))
