"""Train the second blank-guide pair on data/sanborn/train_v2/ and test every pair end to end (24 November 2026).

    From the repo folder (3D), in PowerShell:
        python tools\\sanborn\\unet\\train_v2.py                 the whole run (about 6.5 hours on this machine: 8 trainings of about 47 min, 5 evals of 2-4 min)
        python tools\\sanborn\\unet\\train_v2.py --dry-run       print the steps and their commands, run nothing
        python tools\\sanborn\\unet\\train_v2.py --only V1S1     one step (baseline, V1S1, V2S1, V1S2, V2S2; comma-separated)
        python tools\\sanborn\\unet\\train_v2.py --summary       rewrite the summary from what is there
        options: --iters 4000, --out DIR, --data DIR, --baseline-runs DIR (see main())
    It starts the networks' own Python (tools/sanborn/unet/.venv) by itself, as train_noguide.py does.

Ben, 23 November 2026: "1A is done. let's try training on a number of them. you should choose them by complexity and
size, with what you think are enough plates to teach the U-net sufficiently". The data folder data/sanborn/train_v2/
(make_labels_v2.py; its manifest.json lists the plates) holds:
  - the four labelled plates 43, 45, 80, 82A, with today's labels (source 'label');
  - plate 1A from Ben's check of its lines (source 'map'), its ground right of Elm Street held out (valmask.png): the
    checkpoints are chosen there and nowhere else;
  - eleven pseudo-labelled plates (source 'pseudo'): 5, 54A, 53, 7, 51, 58 at 100 ft; 66, 68, 76 and the PDF sheets
    79, 89 at 200 ft. Their labels are the batch's own outputs (area_ng1, lines_ng1, the merged outline step) kept only
    where confident: the networks' guesses, filtered, not truth. (58, a low-tint 100-ft residential plate, was added
    on 24 Nov: 15 of the batch's other 34 plates at 100 ft have a tint under 0.30 and none was in the first ten.)
Plate 44 (the benchmark) and plate 90 (the next truth plate) are not in the data folder, and the trainers refuse them.

The steps, in order (a step already finished is skipped, so after an interruption the same command carries on):
  baseline  eval_v2.py on area_ng1 + lines_ng1 (the batch's pair): the reference row, and the baseline bench44 runs
            (6 tile grids) every later eval is paired with.
  V1S1      area_v2a_s1, lines_v2a_s1: the four labelled plates and 1A (outside its validation ground), seed 1; then
            eval_v2.
  V2S1      area_v2b_s1, lines_v2b_s1: V1 plus the eleven pseudo plates at weight 5/11 each, so half the crops come
            from labelled ground and half from pseudo ground (5 x 1 against 11 x 5/11), seed 1; then eval_v2. The line
            network gets 128 ('no area map') as its 7th input on the pseudo plates (edgenet.py --area-blank pseudo):
            their line targets were made from the very map that is their area_in.png, so the target could be read
            off that input (review-leak finding 1).
  V1S2, V2S2  the same with seed 2: the spread between two seeds is the bar a difference between V1 and V2 must clear.
Each network trains ITERS iterations (default 4000, as area_ng1 and lines_ng1), checks the 1A validation ground every
250 and keeps the best checkpoint (NAME.pt) and the last (NAME_last.pt). The line network's 7th input is each plate's
area_in.png (the batch's area_ng1 map; in sample on 43, 45, 80, 82A; 128 on the pseudo plates in V2), NOT the new
area network's answer. eval_v2.py feeds it the new area network's map, as the batch would.

A step that fails does not stop the run (review-code 2): a failed training skips that step's eval, a failed eval is
logged, the run goes on to the next step, and at the end the failed steps are named and the exit code is 1. Running
the same command again redoes only what is not finished.

THE RULE FOR WHAT SHIPS (written down before the run; review-leak finding 3). Plate 44 only scores; it decides two
things and nothing else, and every number below is the 6-grid mean PQ of bench44 with the merged outline step:
  - noise = the larger of |V1S1 - V1S2| and |V2S1 - V2S2| (the seed-to-seed spread);
  - V2 is preferred to V1 only if V2 beats V1 for EACH seed and the mean of the two differences is larger than noise;
    otherwise V1 (the simpler one);
  - the preferred variant replaces area_ng1 + lines_ng1 only if its paired gain over them is above 0 for EACH seed and
    its mean is larger than noise; otherwise the batch pair stays;
  - the seed of the pair that ships is chosen on the 1A validation region (its PQ there; a tie goes to seed 1), never
    on 44.
  summary.json and summary.md apply the rule once all four pairs are evaluated. The shipped pair's 44 numbers are then
  a little optimistic (44 chose between V1, V2 and keeping the batch pair). Plate 90, once Ben has checked its lines,
  is the untouched check of the pair that ships. The 1A region numbers are NOT a test: the checkpoints were chosen on
  that ground, the pseudo-label thresholds were tuned on the whole of 1A, and it holds 9 of Ben's blocks (one block
  moves its PQ by about 0.1).

Files (OUT, default data/sanborn/train_v2_runs/):
  models/NAME.pt, NAME_last.pt, NAME.json     the trainers' output (seed, data manifest sha256, git commit, history)
  eval/STEP/eval_v2.json                      eval_v2.py's output (44 on 6 grids with the merged outline step, 1A region)
  eval/runs_baseline44/                       the baseline's bench44 runs, shared by every eval
  logs/STEP_*.log                             each command's own output
  train_v2.log                                what ran, when, how long
  summary.json, summary.md                    the table and the rule's decision (rewritten after every step)
A model counts as finished when NAME_last.pt is there and NAME.json's history reaches ITERS with the data folder's
current manifest, the step's seed, plates, weights and --area-blank; an eval when eval/STEP/eval_v2.json names the
current model files (sha256). A training cut off part way starts again from the beginning (the trainers do not resume
inside a run). Every eval scores 1A against train_v2/1A/streetmap.json and train_v2/1A/valmask.png (the files the
checkpoints were chosen on), not against Ben's live edges_ben.json.
"""
import argparse, hashlib, json, os, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))


def _repo():
    """the repo above this file (also when it runs from a staging folder)"""
    d = HERE
    while True:
        if os.path.exists(os.path.join(d, 'tools', 'sanborn', '_ws.py')) and os.path.exists(os.path.join(d, 'configs', 'sanborn_paths.json')): return d
        p = os.path.dirname(d)
        if p == d: sys.exit('train_v2: no repo (tools/sanborn/_ws.py) above this file')
        d = p


REPO = _repo(); SP = os.path.join(REPO, 'data', 'sanborn'); TOOLS = os.path.join(REPO, 'tools', 'sanborn')
PY = os.path.join(TOOLS, 'unet', '.venv', 'Scripts', 'python.exe')
LABELLED = ['43', '45', '80', '82A', '1A']
PSEUDO = ['5', '54A', '53', '7', '51', '58', '66', '68', '76', '79', '89']
PSEUDO_W = round(len(LABELLED) / len(PSEUDO), 6)   # 11 x 5/11 = 5 x 1: labelled and pseudo crops 1:1
AREA_BLANK = 'pseudo'                              # V2's line network: 128 as the 7th input on the pseudo plates (review-leak finding 1)
FORBIDDEN = ('44', '90')
GRIDS = '0,1,2,3,4,5'
STEPS = [('baseline', None, None), ('V1S1', 'a', 1), ('V2S1', 'b', 1), ('V1S2', 'a', 2), ('V2S2', 'b', 2)]


def sha(p):
    if not os.path.exists(p): return None
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()


def jload(p):
    """a json file, or None if it is missing or cut off (a run killed while writing it)"""
    try:
        with open(p, encoding='utf8') as f: return json.load(f)
    except (OSError, ValueError): return None


def jsave(p, obj, text=None):
    tmp = p + f'.{os.getpid()}.tmp'
    with open(tmp, 'w', encoding='utf8', newline='\n') as f:
        if text is None: json.dump(obj, f, indent=1)
        else: f.write(text)
    for k in range(50):
        try: os.replace(tmp, p); return
        except PermissionError:
            if k == 49: raise
            time.sleep(0.2)


class Log:
    def __init__(self, path): self.path = path; os.makedirs(os.path.dirname(path), exist_ok=True)
    def __call__(self, *a):
        s = time.strftime('%Y-%m-%d %H:%M:%S') + ' ' + ' '.join(str(x) for x in a)
        print(s, flush=True)
        with open(self.path, 'a', encoding='utf8', newline='\n') as f: f.write(s + '\n')


def run(cmd, logfile, log, dry):
    """run a step's command; (ok, minutes). A failure is logged, not raised (review-code 2)"""
    log('RUN', ' '.join(f'"{c}"' if ' ' in c else c for c in cmd))
    if dry: return True, 0.0
    t0 = time.time(); env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    env['PYTHONPATH'] = os.pathsep.join([TOOLS, os.path.join(TOOLS, 'unet')] + ([env['PYTHONPATH']] if env.get('PYTHONPATH') else []))   # _ws and the pipeline's modules (the scripts beside this file come first)
    try:
        with open(logfile, 'a', encoding='utf8', newline='\n') as f:
            f.write(f'===== {time.strftime("%Y-%m-%d %H:%M:%S")} {" ".join(cmd)}\n'); f.flush()
            p = subprocess.Popen(cmd, cwd=SP, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf8', errors='replace', env=env)
            for line in p.stdout: f.write(line); f.flush(); print('   ' + line.rstrip()[:200], flush=True)
            rc = p.wait()
    except OSError as e:
        log(f'FAILED to run ({e}); see {logfile}'); return False, round((time.time() - t0) / 60, 1)
    if rc: log(f'FAILED (exit {rc}); see {logfile}')
    return rc == 0, round((time.time() - t0) / 60, 1)


def plates_of(variant):
    """the plate specs, --weights and --area-blank (line network) of a variant"""
    if variant == 'a': return list(LABELLED), None, None
    return LABELLED + PSEUDO, ','.join(f'{p}={PSEUDO_W}' for p in PSEUDO), AREA_BLANK


def model_done(models, name, iters, man_sha, seed, plates, weights, blank):
    """finished with this data folder, seed, plates, weights and --area-blank (review-code 4); a cut-off json counts as
    not finished (review-code 3); a finished model made otherwise stops the run (move it aside)"""
    j = os.path.join(models, name + '.json')
    if not (os.path.exists(j) and os.path.exists(os.path.join(models, name + '_last.pt')) and os.path.exists(os.path.join(models, name + '.pt'))): return False
    d = jload(j)
    if not isinstance(d, dict): return False
    h = d.get('history') or []
    if not h or h[-1].get('iter') != iters: return False
    why = []
    if d.get('manifest_sha256') != man_sha: why.append(f'data manifest {str(d.get("manifest_sha256"))[:12]}, now {man_sha[:12]}')
    if d.get('seed') != seed: why.append(f'seed {d.get("seed")}, now {seed}')
    have = [p.get('spec') for p in d.get('plates', []) if isinstance(p, dict)]
    if have != list(plates): why.append(f'plates {have}, now {list(plates)}')
    want_w = {p: float(v) for p, v in (kv.split('=') for kv in weights.split(','))} if weights else {}
    have_w = {p.get('plate'): p.get('weight') for p in d.get('plates', []) if isinstance(p, dict)}
    if any(abs(float(have_w.get(p, -1)) - want_w.get(p, 1.0)) > 1e-9 for p in have_w): why.append('other plate weights')
    if name.startswith('lines') and sorted(d.get('area_blank') or []) != sorted(s.upper() for s in ([blank] if blank else [])): why.append(f'--area-blank {d.get("area_blank")}, now {blank}')
    if why: sys.exit(f'{name} is finished but was trained otherwise ({"; ".join(why)}): move models/{name}.* aside to train it again')
    return True


def eval_done(edir, area_pt, lines_pt):
    m = (jload(os.path.join(edir, 'eval_v2.json')) or {}).get('models', {})
    return bool(m) and (m.get('area') or {}).get('sha256') == sha(area_pt) and (m.get('lines') or {}).get('sha256') == sha(lines_pt)


def g(d, *ks):
    for k in ks:
        if not isinstance(d, dict) or k not in d: return None
        d = d[k]
    return d


def mean(v):
    v = [x for x in v if isinstance(x, (int, float))]
    return round(sum(v) / len(v), 4) if v else None


def decide(rows):
    """THE RULE FOR WHAT SHIPS (see the docstring): None until all four pairs are evaluated"""
    R = {r['step']: r for r in rows}
    pq = {s: g(R.get(s), '44', 'PQ') for s in ('V1S1', 'V1S2', 'V2S1', 'V2S2')}
    gain = {s: g(R.get(s), '44_paired_gain', 'PQ', 'mean') for s in pq}
    vq = {s: g(R.get(s), '1A_region', 'PQ') for s in pq}
    if any(v is None for v in list(pq.values()) + list(gain.values())): return dict(done=False, note='the rule is applied once V1S1, V2S1, V1S2 and V2S2 are all evaluated')
    noise = max(abs(pq['V1S1'] - pq['V1S2']), abs(pq['V2S1'] - pq['V2S2']))
    d21 = [pq['V2S1'] - pq['V1S1'], pq['V2S2'] - pq['V1S2']]
    v2 = all(x > 0 for x in d21) and sum(d21) / 2 > noise; var = 'V2' if v2 else 'V1'
    gs = [gain[f'{var}S1'], gain[f'{var}S2']]
    ship = all(x > 0 for x in gs) and sum(gs) / 2 > noise
    s1, s2 = vq[f'{var}S1'], vq[f'{var}S2']
    seed = 2 if (s1 is not None and s2 is not None and s2 > s1) else 1
    return dict(done=True, noise_pq=round(noise, 4), v2_minus_v1_by_seed=[round(x, 4) for x in d21], variant=var,
                variant_why=('V2 beats V1 for both seeds by more than the noise on average' if v2 else 'V2 does not beat V1 for both seeds by more than the noise on average: V1, the simpler'),
                paired_gain_by_seed=[round(x, 4) for x in gs], ships=ship,
                ship_why=(f'{var} beats area_ng1 + lines_ng1 on 44 for both seeds by more than the noise on average' if ship else f'{var} does not beat area_ng1 + lines_ng1 on 44 for both seeds by more than the noise on average: the batch pair stays'),
                seed=seed if ship else None, seed_why=(f'1A validation region PQ: seed 1 {s1}, seed 2 {s2} (not 44)' if ship else None),
                pair=(f'area_v2{"b" if v2 else "a"}_s{seed}.pt + lines_v2{"b" if v2 else "a"}_s{seed}.pt' if ship else 'area_ng1 + lines_ng1 (unchanged)'),
                caution='44 chose between V1, V2 and keeping the batch pair, so the shipped pair\'s 44 numbers are a little optimistic; plate 90, once Ben has checked its lines, is the untouched check')


def summary(OUT, iters):
    """summary.json and summary.md from what is there"""
    rows = []
    for step, var, seed in STEPS:
        e = os.path.join(OUT, 'eval', step, 'eval_v2.json'); E = jload(e)
        r = dict(step=step, variant={'a': 'V1', 'b': 'V2'}.get(var, 'baseline (area_ng1 + lines_ng1)'), seed=seed, eval=os.path.relpath(e, SP) if E else None)
        if var:
            for kind in ('area', 'lines'):
                d = jload(os.path.join(OUT, 'models', f'{kind}_v2{var}_s{seed}.json'))
                if isinstance(d, dict):
                    b = d.get('best') or {}; hl = (d.get('history') or [{}])[-1]
                    r[kind] = dict(best_iter=b.get('iter'), val=b.get('iou_street', b.get('f1')), last_val=g(hl, 'val_pooled', 'iou_street' if kind == 'area' else 'f1'),
                                   minutes=d.get('minutes'), iters=hl.get('iter'), seed=d.get('seed'), manifest=str(d.get('manifest_sha256'))[:12], area_blank=d.get('area_blank'))
        if isinstance(E, dict):
            A = g(E, 'bench44', 'v2', 'all') or {}; P = g(E, 'bench44', 'paired', 'all') or {}
            r['44'] = {k: (A.get(k) or {}).get('mean') for k in ('PQ', 'PQ_decided', 'recall_interior', 'precision', 'merges', 'fp', 'ben_blocks_closed')}
            r['44']['PQ_sd_over_grids'] = (A.get('PQ') or {}).get('sd'); r['44']['grids'] = g(E, 'bench44', 'grids')
            r['44_paired_gain'] = {k: dict(mean=(P.get(k) or {}).get('mean'), grids_up=(P.get(k) or {}).get('gains'), of=(P.get(k) or {}).get('of')) for k in ('PQ', 'recall_interior', 'precision')}
            R = g(E, 'bench1A', 'v2', 'region') or {}
            r['1A_region'] = {k: R.get(k) for k in ('PQ', 'PQ_decided', 'recall_interior', 'precision', 'merges', 'fp', 'ben_blocks_closed')}
            r['1A_region_blocks'] = g(E, 'bench1A', 'region_blocks')
        rows.append(r)
    means = {}
    for var in ('a', 'b'):
        rs = [r for r in rows if r['step'].startswith('V1' if var == 'a' else 'V2') and r.get('44')]
        if rs:
            pq = [r['44']['PQ'] for r in rs if r['44'].get('PQ') is not None]
            means['V1' if var == 'a' else 'V2'] = dict(seeds=len(rs), PQ_44_mean=mean(pq), PQ_44_seed_range=[min(pq), max(pq)] if pq else None,
                                                     paired_gain_mean=mean([g(r, '44_paired_gain', 'PQ', 'mean') for r in rs]), PQ_1A_region_mean=mean([g(r, '1A_region', 'PQ') for r in rs]))
    S = dict(made=time.strftime('%Y-%m-%d %H:%M:%S'), iters=iters, rows=rows, by_variant=means, decision=decide(rows),
             note='44: mean over the 6 tile grids of bench44 with the merged outline step (eval_v2.py); paired gain = this pair minus area_ng1 + lines_ng1, grid by grid. 44 was never used to choose a checkpoint. '
                  '1A region: the ground right of Elm Street (train_v2/1A/valmask.png). It is NOT a test: the checkpoints were chosen on it, the pseudo-label thresholds were tuned on the whole of 1A, and it holds 9 of Ben\'s blocks (one block moves its PQ by about 0.1). '
                  'Ben\'s 1A lines started from the batch\'s, so the baseline starts ahead there.')
    jsave(os.path.join(OUT, 'summary.json'), S)
    f = lambda v, n=3: '-' if v is None else (f'{v:.{n}f}' if isinstance(v, float) else str(v))
    L = ['# train_v2: the second blank-guide pair', '', f'Made {S["made"]}, {iters} iterations per network. {S["note"]}', '',
         '| step | variant | seed | area best it / val IoU street | lines best it / val F1 | 44 PQ (sd over grids) | 44 paired gain PQ (grids up) | 44 recall | 44 precision | 44 merges | 44 fp | 1A region PQ (not a test) | 1A recall | 1A precision |',
         '|---|---|---|---|---|---|---|---|---|---|---|---|---|---|']
    for r in rows:
        a, l_, q, p, v = r.get('area') or {}, r.get('lines') or {}, r.get('44') or {}, r.get('44_paired_gain') or {}, r.get('1A_region') or {}
        L.append(f"| {r['step']} | {r['variant']} | {f(r['seed'])} | {f(a.get('best_iter'))} / {f(a.get('val'))} | {f(l_.get('best_iter'))} / {f(l_.get('val'))} | {f(q.get('PQ'))} ({f(q.get('PQ_sd_over_grids'))}) | "
                 f"{f((p.get('PQ') or {}).get('mean'))} ({f((p.get('PQ') or {}).get('grids_up'))}/{f((p.get('PQ') or {}).get('of'))}) | {f(q.get('recall_interior'))} | {f(q.get('precision'))} | {f(q.get('merges'), 1)} | {f(q.get('fp'), 1)} | "
                 f"{f(v.get('PQ'))} | {f(v.get('recall_interior'))} | {f(v.get('precision'))} |")
    if means:
        L += ['', '| variant | seeds | 44 PQ mean | 44 PQ by seed (min, max) | paired gain mean | 1A region PQ mean |', '|---|---|---|---|---|---|']
        for k, m in means.items():
            rg = m['PQ_44_seed_range'] or [None, None]
            L.append(f"| {k} | {m['seeds']} | {f(m['PQ_44_mean'])} | {f(rg[0])}, {f(rg[1])} | {f(m['paired_gain_mean'])} | {f(m['PQ_1A_region_mean'])} |")
    D = S['decision']; L += ['', '## The rule\'s decision (written down before the run; see train_v2.py)', '']
    if not D.get('done'): L.append(D['note'])
    else:
        L += [f"- noise (largest seed-to-seed spread of 44 PQ): {f(D['noise_pq'], 4)}", f"- V2 minus V1 by seed: {D['v2_minus_v1_by_seed']} -> {D['variant']} ({D['variant_why']})",
              f"- {D['variant']} paired gain over area_ng1 + lines_ng1 by seed: {D['paired_gain_by_seed']} -> {'ships' if D['ships'] else 'does not ship'} ({D['ship_why']})",
              f"- the pair: {D['pair']}" + (f" (seed by {D['seed_why']})" if D['ships'] else ''), f"- {D['caution']}"]
    jsave(os.path.join(OUT, 'summary.md'), None, '\n'.join(L) + '\n')
    return S


def main():
    ap = argparse.ArgumentParser(description='train_v2 (see the docstring)', allow_abbrev=False)
    ap.add_argument('--iters', type=int, default=4000); ap.add_argument('--out', default=os.path.join(SP, 'train_v2_runs'))
    ap.add_argument('--data', default=os.path.join(SP, 'train_v2')); ap.add_argument('--only'); ap.add_argument('--dry-run', action='store_true'); ap.add_argument('--summary', action='store_true')
    ap.add_argument('--baseline-runs', help='the baseline bench44 runs every eval is paired with (default OUT/eval/runs_baseline44; one already there for the same maps and code is reused)')
    a = ap.parse_args(); OUT = os.path.abspath(a.out); DATA = os.path.abspath(a.data); MODELS = os.path.join(OUT, 'models'); LOGS = os.path.join(OUT, 'logs')
    if a.summary: summary(OUT, a.iters); print(open(os.path.join(OUT, 'summary.md'), encoding='utf8').read()); return
    only = {s.strip() for s in a.only.split(',')} if a.only else None
    if only and only - {s for s, _, _ in STEPS}: sys.exit(f'--only: steps are {", ".join(s for s, _, _ in STEPS)}')
    # checks before anything runs
    if not os.path.exists(PY): sys.exit(f'the networks\' Python is not there: {PY}')
    for f, w in (('unet.py', 'def train_data'), ('edgenet.py', '--area-blank'), ('eval_v2.py', 'def main'), ('bench_plate.py', 'def make_truth')):
        p = os.path.join(HERE, f)
        if not os.path.exists(p) or w not in open(p, encoding='utf8').read(): sys.exit(f'{p} is not the 24 Nov version ({w!r} missing): apply the staged code first')
    mf = os.path.join(DATA, 'manifest.json')
    if not os.path.exists(mf): sys.exit(f'no {mf}: build the data folder first (make_labels_v2.py)')
    man = json.load(open(mf, encoding='utf8')); have = set(man.get('plates', {}))
    if have & set(FORBIDDEN): sys.exit(f'the data folder holds {sorted(have & set(FORBIDDEN))}: never trained on')
    if set(LABELLED + PSEUDO) - have: sys.exit(f'the data folder lacks {sorted(set(LABELLED + PSEUDO) - have)}')
    truth, region = os.path.join(DATA, '1A', 'streetmap.json'), os.path.join(DATA, '1A', 'valmask.png')
    for f_ in (truth, region):
        if not os.path.exists(f_): sys.exit(f'{f_} is missing: the checkpoints are chosen on 1A\'s validation ground against it')
    man_sha = sha(mf); os.makedirs(MODELS, exist_ok=True); os.makedirs(LOGS, exist_ok=True)
    log = Log(os.path.join(OUT, 'train_v2.log'))
    log(f'== train_v2 {"(dry run) " if a.dry_run else ""}iters {a.iters}, data {DATA} (manifest {man_sha[:12]}), out {OUT}')
    un, en, ev = (os.path.join(HERE, f) for f in ('unet.py', 'edgenet.py', 'eval_v2.py'))
    BR = os.path.abspath(a.baseline_runs) if a.baseline_runs else os.path.join(OUT, 'eval', 'runs_baseline44')
    T0 = time.time(); failed = []
    for step, var, seed in STEPS:
        if only and step not in only: continue
        edir = os.path.join(OUT, 'eval', step)
        if var is None:
            ap_, lp_ = os.path.join(SP, 'unet_data', 'models', 'area_ng1.pt'), os.path.join(SP, 'unet_data', 'models', 'lines_ng1.pt')
        else:
            plates, w, blank = plates_of(var); ok_all = True
            for kind, script in (('area', un), ('lines', en)):
                name = f'{kind}_v2{var}_s{seed}'
                wa = (['--weights', w] if w else []) + (['--area-blank', blank] if blank and kind == 'lines' else [])
                if model_done(MODELS, name, a.iters, man_sha, seed, plates, w, blank): log(f'{step}: {name} already trained, skipped'); continue
                if os.path.exists(os.path.join(MODELS, name + '.json')): log(f'{step}: {name} was cut off part way: training it again from the start')
                log(f'{step}: training {name} ({len(plates)} plates, seed {seed})')
                ok, m = run([PY, '-B', '-W', 'ignore', script, 'train', name, '--data', DATA] + plates + ['--seed', str(seed), '--iters', str(a.iters), '--out', MODELS] + wa, os.path.join(LOGS, f'{step}_{name}.log'), log, a.dry_run)
                if not ok: ok_all = False; failed.append(f'{step} {name}'); log(f'{step}: {name} FAILED after {m} min: the step\'s eval is skipped, the run goes on'); break
                log(f'{step}: {name} done in {m} min')
            if not ok_all: continue
            ap_, lp_ = os.path.join(MODELS, f'area_v2{var}_s{seed}.pt'), os.path.join(MODELS, f'lines_v2{var}_s{seed}.pt')
        if not a.dry_run and eval_done(edir, ap_, lp_): log(f'{step}: eval already there, skipped'); continue
        cmd = [PY, '-B', '-W', 'ignore', ev, '--area-model', ap_, '--lines-model', lp_, '--out', edir, '--grids', GRIDS, '--baseline-runs', BR, '--truth-1a', truth, '--region-1a', region]
        log(f'{step}: eval_v2'); ok, m = run(cmd, os.path.join(LOGS, f'{step}_eval.log'), log, a.dry_run)
        if ok: log(f'{step}: eval done in {m} min')
        else: failed.append(f'{step} eval'); log(f'{step}: eval FAILED after {m} min: the run goes on (a rerun redoes it)')
        if not a.dry_run: summary(OUT, a.iters)
    if not a.dry_run:
        summary(OUT, a.iters); log(f'== finished in {(time.time() - T0) / 3600:.1f} h; table: {os.path.join(OUT, "summary.md")}' + (f'; FAILED: {", ".join(failed)} (run the same command again to redo them)' if failed else ''))
        print(open(os.path.join(OUT, 'summary.md'), encoding='utf8').read())
    if failed: sys.exit(1)


if __name__ == '__main__':
    main()
