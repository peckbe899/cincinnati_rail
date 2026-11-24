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
  - ten pseudo-labelled plates (source 'pseudo'): 5, 54A, 53, 7, 51 at 100 ft; 66, 68, 76 and the PDF sheets 79, 89 at
    200 ft. Their labels are the batch's own outputs (area_ng1, lines_ng1, the merged outline step) kept only where
    confident: the networks' guesses, filtered, not truth.
Plate 44 (the benchmark) and plate 90 (the next truth plate) are not in the data folder, and the trainers refuse them.

The steps, in order (a step already finished is skipped, so after an interruption the same command carries on):
  baseline  eval_v2.py on area_ng1 + lines_ng1 (the batch's pair): the reference row, and the baseline bench44 runs
            (6 tile grids) every later eval is paired with.
  V1S1      area_v2a_s1, lines_v2a_s1: the four labelled plates and 1A (3/4 + validation), seed 1; then eval_v2.
  V2S1      area_v2b_s1, lines_v2b_s1: V1 plus the ten pseudo plates at weight 0.5 each, so half the crops come from
            labelled ground and half from pseudo ground (5 x 1.0 against 10 x 0.5), seed 1; then eval_v2.
  V1S2, V2S2  the same with seed 2: the spread between two seeds is the bar a difference between V1 and V2 must clear.
Each network trains ITERS iterations (default 4000, as area_ng1 and lines_ng1), checks the 1A validation ground every
250 and keeps the best checkpoint (NAME.pt) and the last (NAME_last.pt). The line network's 7th input is each plate's
area_in.png (the batch's area_ng1 map; in sample on 43, 45, 80, 82A), NOT the new area network's answer. eval_v2.py
feeds it the new area network's map, as the batch would.

Files (OUT, default data/sanborn/train_v2_runs/):
  models/NAME.pt, NAME_last.pt, NAME.json     the trainers' output (seed, data manifest sha256, git commit, history)
  eval/STEP/eval_v2.json                      eval_v2.py's output (44 on 6 grids with the merged outline step, 1A region)
  eval/runs_baseline44/                       the baseline's bench44 runs, shared by every eval
  logs/STEP_*.log                             each command's own output
  train_v2.log                                what ran, when, how long
  summary.json, summary.md                    the table (rewritten after every step)
A model counts as finished when NAME_last.pt is there and NAME.json's history reaches ITERS with the data folder's
current manifest; an eval when eval/STEP/eval_v2.json names the current model files (sha256). A training cut off part
way starts again from the beginning (the trainers do not resume inside a run).
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
PSEUDO = ['5', '54A', '53', '7', '51', '66', '68', '76', '79', '89']
PSEUDO_W = 0.5                                     # 10 x 0.5 = 5 x 1.0: labelled and pseudo crops 1:1
FORBIDDEN = ('44', '90')
GRIDS = '0,1,2,3,4,5'
STEPS = [('baseline', None, None), ('V1S1', 'a', 1), ('V2S1', 'b', 1), ('V1S2', 'a', 2), ('V2S2', 'b', 2)]


def sha(p):
    if not os.path.exists(p): return None
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()


class Log:
    def __init__(self, path): self.path = path; os.makedirs(os.path.dirname(path), exist_ok=True)
    def __call__(self, *a):
        s = time.strftime('%Y-%m-%d %H:%M:%S') + ' ' + ' '.join(str(x) for x in a)
        print(s, flush=True)
        with open(self.path, 'a', encoding='utf8', newline='\n') as f: f.write(s + '\n')


def run(cmd, logfile, log, dry):
    log('RUN', ' '.join(f'"{c}"' if ' ' in c else c for c in cmd))
    if dry: return 0.0
    t0 = time.time(); env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    env['PYTHONPATH'] = os.pathsep.join([TOOLS, os.path.join(TOOLS, 'unet')] + ([env['PYTHONPATH']] if env.get('PYTHONPATH') else []))   # _ws and the pipeline's modules (the scripts beside this file come first)
    with open(logfile, 'a', encoding='utf8', newline='\n') as f:
        f.write(f'===== {time.strftime("%Y-%m-%d %H:%M:%S")} {" ".join(cmd)}\n'); f.flush()
        p = subprocess.Popen(cmd, cwd=SP, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf8', errors='replace', env=env)
        for line in p.stdout: f.write(line); f.flush(); print('   ' + line.rstrip()[:200], flush=True)
        if p.wait(): log(f'FAILED (exit {p.returncode}); see {logfile}'); sys.exit(f'step failed: see {logfile}')
    return round((time.time() - t0) / 60, 1)


def plates_of(variant):
    """the plate specs and --weights of a variant"""
    if variant == 'a': return list(LABELLED), None
    return LABELLED + PSEUDO, ','.join(f'{p}={PSEUDO_W}' for p in PSEUDO)


def model_done(models, name, iters, man_sha):
    j = os.path.join(models, name + '.json')
    if not (os.path.exists(j) and os.path.exists(os.path.join(models, name + '_last.pt')) and os.path.exists(os.path.join(models, name + '.pt'))): return False
    d = json.load(open(j, encoding='utf8')); h = d.get('history') or []
    if not h or h[-1].get('iter') != iters: return False
    if d.get('manifest_sha256') != man_sha: sys.exit(f'{name} was trained on another version of the data folder (manifest {str(d.get("manifest_sha256"))[:12]}, now {man_sha[:12]}): move models/{name}.* aside to train it again')
    return True


def eval_done(edir, area_pt, lines_pt):
    f = os.path.join(edir, 'eval_v2.json')
    if not os.path.exists(f): return False
    m = json.load(open(f, encoding='utf8')).get('models', {})
    return (m.get('area') or {}).get('sha256') == sha(area_pt) and (m.get('lines') or {}).get('sha256') == sha(lines_pt)


def g(d, *ks):
    for k in ks:
        if not isinstance(d, dict) or k not in d: return None
        d = d[k]
    return d


def summary(OUT, iters):
    """summary.json and summary.md from what is there"""
    rows = []
    for step, var, seed in STEPS:
        e = os.path.join(OUT, 'eval', step, 'eval_v2.json'); E = json.load(open(e, encoding='utf8')) if os.path.exists(e) else None
        r = dict(step=step, variant={'a': 'V1', 'b': 'V2'}.get(var, 'baseline (area_ng1 + lines_ng1)'), seed=seed, eval=os.path.relpath(e, SP) if E else None)
        if var:
            for kind in ('area', 'lines'):
                j = os.path.join(OUT, 'models', f'{kind}_v2{var}_s{seed}.json')
                if os.path.exists(j):
                    d = json.load(open(j, encoding='utf8')); b = d.get('best') or {}
                    r[kind] = dict(best_iter=b.get('iter'), val=b.get('iou_street', b.get('f1')), last_val=g((d.get('history') or [{}])[-1], 'val_pooled', 'iou_street' if kind == 'area' else 'f1'),
                                   minutes=d.get('minutes'), iters=(d.get('history') or [{}])[-1].get('iter'), seed=d.get('seed'), manifest=str(d.get('manifest_sha256'))[:12])
        if E:
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
            pq = [r['44']['PQ'] for r in rs]; gain = [r['44_paired_gain']['PQ']['mean'] for r in rs]; vq = [r['1A_region']['PQ'] for r in rs]
            means['V1' if var == 'a' else 'V2'] = dict(seeds=len(rs), PQ_44_mean=round(sum(pq) / len(pq), 4), PQ_44_seed_range=[min(pq), max(pq)], paired_gain_mean=round(sum(gain) / len(gain), 4),
                                                         PQ_1A_region_mean=round(sum(vq) / len(vq), 4) if all(v is not None for v in vq) else None)
    S = dict(made=time.strftime('%Y-%m-%d %H:%M:%S'), iters=iters, rows=rows, by_variant=means,
             note='44: mean over the tile grids of bench44 with the merged outline step (eval_v2.py); paired gain = this pair minus area_ng1 + lines_ng1, grid by grid. '
                  '1A region: the ground right of Elm Street (train_v2/1A/valmask.png), out of sample for the v2 pairs; Ben\'s 1A lines started from the batch\'s, so the baseline starts ahead there. '
                  'The checkpoints were chosen on the 1A region only; 44 was never used to choose anything.')
    json.dump(S, open(os.path.join(OUT, 'summary.json'), 'w', encoding='utf8', newline='\n'), indent=1)
    f = lambda v, n=3: '-' if v is None else (f'{v:.{n}f}' if isinstance(v, float) else str(v))
    L = ['# train_v2: the second blank-guide pair', '', f'Made {S["made"]}, {iters} iterations per network. {S["note"]}', '',
         '| step | variant | seed | area best it / val IoU street | lines best it / val F1 | 44 PQ (sd over grids) | 44 paired gain PQ (grids up) | 44 recall | 44 precision | 44 merges | 44 fp | 1A region PQ | 1A recall | 1A precision |',
         '|---|---|---|---|---|---|---|---|---|---|---|---|---|---|']
    for r in rows:
        a, l_, q, p, v = r.get('area') or {}, r.get('lines') or {}, r.get('44') or {}, r.get('44_paired_gain') or {}, r.get('1A_region') or {}
        L.append(f"| {r['step']} | {r['variant']} | {f(r['seed'])} | {f(a.get('best_iter'))} / {f(a.get('val'))} | {f(l_.get('best_iter'))} / {f(l_.get('val'))} | {f(q.get('PQ'))} ({f(q.get('PQ_sd_over_grids'))}) | "
                 f"{f((p.get('PQ') or {}).get('mean'))} ({f((p.get('PQ') or {}).get('grids_up'))}/{f((p.get('PQ') or {}).get('of'))}) | {f(q.get('recall_interior'))} | {f(q.get('precision'))} | {f(q.get('merges'), 1)} | {f(q.get('fp'), 1)} | "
                 f"{f(v.get('PQ'))} | {f(v.get('recall_interior'))} | {f(v.get('precision'))} |")
    if means:
        L += ['', '| variant | seeds | 44 PQ mean | 44 PQ by seed (min, max) | paired gain mean | 1A region PQ mean |', '|---|---|---|---|---|---|']
        for k, m in means.items(): L.append(f"| {k} | {m['seeds']} | {f(m['PQ_44_mean'])} | {f(m['PQ_44_seed_range'][0])}, {f(m['PQ_44_seed_range'][1])} | {f(m['paired_gain_mean'])} | {f(m['PQ_1A_region_mean'])} |")
    open(os.path.join(OUT, 'summary.md'), 'w', encoding='utf8', newline='\n').write('\n'.join(L) + '\n')
    return S


def main():
    ap = argparse.ArgumentParser(description='train_v2 (see the docstring)', allow_abbrev=False)
    ap.add_argument('--iters', type=int, default=4000); ap.add_argument('--out', default=os.path.join(SP, 'train_v2_runs'))
    ap.add_argument('--data', default=os.path.join(SP, 'train_v2')); ap.add_argument('--only'); ap.add_argument('--dry-run', action='store_true'); ap.add_argument('--summary', action='store_true')
    ap.add_argument('--baseline-runs', help='the baseline bench44 runs every eval is paired with (default OUT/eval/runs_baseline44; one already there for the same maps is reused)')
    a = ap.parse_args(); OUT = os.path.abspath(a.out); DATA = os.path.abspath(a.data); MODELS = os.path.join(OUT, 'models'); LOGS = os.path.join(OUT, 'logs')
    if a.summary: summary(OUT, a.iters); print(open(os.path.join(OUT, 'summary.md'), encoding='utf8').read()); return
    only = {s.strip() for s in a.only.split(',')} if a.only else None
    if only and only - {s for s, _, _ in STEPS}: sys.exit(f'--only: steps are {", ".join(s for s, _, _ in STEPS)}')
    # checks before anything runs
    if not os.path.exists(PY): sys.exit(f'the networks\' Python is not there: {PY}')
    for f, w in (('unet.py', 'def train_data'), ('edgenet.py', 'def train_data'), ('eval_v2.py', 'def main'), ('bench_plate.py', 'def make_truth')):
        p = os.path.join(HERE, f)
        if not os.path.exists(p) or w not in open(p, encoding='utf8').read(): sys.exit(f'{p} is not the 23 Nov version ({w!r} missing): apply the staged code first')
    mf = os.path.join(DATA, 'manifest.json')
    if not os.path.exists(mf): sys.exit(f'no {mf}: build the data folder first (make_labels_v2.py)')
    man = json.load(open(mf, encoding='utf8')); have = set(man.get('plates', {}))
    if have & set(FORBIDDEN): sys.exit(f'the data folder holds {sorted(have & set(FORBIDDEN))}: never trained on')
    if set(LABELLED + PSEUDO) - have: sys.exit(f'the data folder lacks {sorted(set(LABELLED + PSEUDO) - have)}')
    if not os.path.exists(os.path.join(DATA, '1A', 'valmask.png')): sys.exit('train_v2/1A/valmask.png is missing: the checkpoints are chosen there')
    man_sha = sha(mf); os.makedirs(MODELS, exist_ok=True); os.makedirs(LOGS, exist_ok=True)
    log = Log(os.path.join(OUT, 'train_v2.log'))
    log(f'== train_v2 {"(dry run) " if a.dry_run else ""}iters {a.iters}, data {DATA} (manifest {man_sha[:12]}), out {OUT}')
    un, en, ev = (os.path.join(HERE, f) for f in ('unet.py', 'edgenet.py', 'eval_v2.py'))
    BR = os.path.abspath(a.baseline_runs) if a.baseline_runs else os.path.join(OUT, 'eval', 'runs_baseline44'); truth = os.path.join(OUT, 'eval', 'baseline', 'truth', '22-1A.json')
    T0 = time.time()
    for step, var, seed in STEPS:
        if only and step not in only: continue
        edir = os.path.join(OUT, 'eval', step)
        if var is None:
            ap_, lp_ = os.path.join(SP, 'unet_data', 'models', 'area_ng1.pt'), os.path.join(SP, 'unet_data', 'models', 'lines_ng1.pt')
        else:
            plates, w = plates_of(var); wa = ['--weights', w] if w else []
            for kind, script in (('area', un), ('lines', en)):
                name = f'{kind}_v2{var}_s{seed}'
                if model_done(MODELS, name, a.iters, man_sha): log(f'{step}: {name} already trained, skipped'); continue
                if os.path.exists(os.path.join(MODELS, name + '.json')): log(f'{step}: {name} was cut off part way: training it again from the start')
                log(f'{step}: training {name} ({len(plates)} plates, seed {seed})')
                m = run([PY, '-B', '-W', 'ignore', script, 'train', name, '--data', DATA] + plates + ['--seed', str(seed), '--iters', str(a.iters), '--out', MODELS] + wa, os.path.join(LOGS, f'{step}_{name}.log'), log, a.dry_run)
                log(f'{step}: {name} done in {m} min')
            ap_, lp_ = os.path.join(MODELS, f'area_v2{var}_s{seed}.pt'), os.path.join(MODELS, f'lines_v2{var}_s{seed}.pt')
        if not a.dry_run and eval_done(edir, ap_, lp_): log(f'{step}: eval already there, skipped'); continue
        cmd = [PY, '-B', '-W', 'ignore', ev, '--area-model', ap_, '--lines-model', lp_, '--out', edir, '--grids', GRIDS, '--baseline-runs', BR]
        if var is not None and os.path.exists(truth): cmd += ['--truth-1a', truth]      # the same 1A truth file for every eval
        log(f'{step}: eval_v2'); m = run(cmd, os.path.join(LOGS, f'{step}_eval.log'), log, a.dry_run); log(f'{step}: eval done in {m} min')
        if not a.dry_run: summary(OUT, a.iters)
    if not a.dry_run:
        summary(OUT, a.iters); log(f'== finished in {(time.time() - T0) / 3600:.1f} h; table: {os.path.join(OUT, "summary.md")}')
        print(open(os.path.join(OUT, 'summary.md'), encoding='utf8').read())


if __name__ == '__main__':
    main()
