"""lines_score.py (text/effect, 25 Nov 2026): the editor lines of plate 44 against text, for the stored runs (no mask) and
the masked runs of run_bench_text.py. Read-only outside text/effect.
    cd data/sanborn; python -B bench_2026-11-25/text/effect/code/lines_score.py      -> scores/lines_score.json

Definitions (as diag/verify numbers_check.py and diag/ben-labels false_response.py):
  shown lines      RUN/44_shown.json less the sheet outline (state 'sheet'), sampled every 1 px
  false length     samples more than 5 px from Ben's street-map lines (streetmap/22-44.json, all kinds)
  false line       a shown line with under 20% of its samples within 8 px of his lines
  on text          a text-mask pixel within 3 px of the sample (the 7 x 7 window numbers_check.py used)
  mostly on text   a false line with 50% or more of its samples on text
  near-street text text px within 40 px of his lines (numbers_check's 'near-street numbers')
  Ben line found   50% or more of its samples within 5 px of a shown line (no angle test); lost / gained against the
                   chain's own stored run on the same grid
  touched by text  a Ben line with text-mask ink within 2 px of 10% or more of its samples (numbers written against it)
Masks: Sref (bin 8 of unet_data/44_bins.png), I2 (idealised, make_masks2.py), I2p (I2 with a 3 px keep-out round lines,
make_I2p44.py), B2 / B2L (word boxes, make_boxes44.py)."""
import json, os, glob
import numpy as np, cv2
from scipy.spatial import cKDTree
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; E = SP + 'bench_2026-11-25/text/effect/'
H, W = 7219, 10768
STORED = {'base': SP + 'bench_2026-11-25/diag/swap/runs_baseline44/base__grid{g}/'}
for s in ('V1S1', 'V1S2', 'V2S1', 'V2S2'): STORED[s] = SP + f'train_v2_runs/eval/{s}/runs44/v2__grid{{g}}/'
MASKS = ('Sref', 'I2', 'I2p', 'B2', 'B2L')


def samples(lines):
    P, I = [], []
    for k, e in enumerate(lines):
        a, b = np.array(e['a'], float), np.array(e['b'], float); n = max(1, int(np.ceil(np.hypot(*(b - a)))))
        t = (np.arange(n) + 0.5) / n; P.append(a[None] + t[:, None] * (b - a)[None]); I.append(np.full(n, k))
    return (np.concatenate(P), np.concatenate(I)) if P else (np.zeros((0, 2)), np.zeros(0, int))


SM = json.load(open(SP + 'streetmap/22-44.json', encoding='utf8')); BL = [l for l in SM['lines']]
BP, BI = samples(BL); BT = cKDTree(BP); Bkind = np.array([l.get('kind', '') for l in BL])
ben_r = np.zeros((H, W), np.uint8)
for l in BL: cv2.line(ben_r, tuple(np.round(l['a']).astype(int).tolist()), tuple(np.round(l['b']).astype(int).tolist()), 1, 1)
near40 = cv2.distanceTransform((ben_r == 0).astype(np.uint8), cv2.DIST_L2, 5) <= 40
M = {k: cv2.imread(E + f'masks/44_map_{k}.png', 0) > 0 for k in MASKS}
WIN = {k: cv2.dilate(m.astype(np.uint8), np.ones((7, 7), np.uint8)) > 0 for k, m in M.items()}
WINN = {k: WIN[k] & (cv2.dilate((M[k] & near40).astype(np.uint8), np.ones((7, 7), np.uint8)) > 0) for k in ('Sref', 'I2')}
qb = np.clip(np.round(BP).astype(int), 0, [W - 1, H - 1])
# Ben's lines touched by text (ink within 2 px) and covered by each mask (the mask on the line itself, +-1 px)
touch = {}; cov = {}
for k in ('Sref', 'I2'):
    t2 = cv2.dilate(M[k].astype(np.uint8), np.ones((5, 5), np.uint8)) > 0; on = t2[qb[:, 1], qb[:, 0]]
    sh = np.bincount(BI, on, len(BL)) / np.maximum(np.bincount(BI, minlength=len(BL)), 1); touch[k] = sh >= 0.1
for k in MASKS:
    c1 = cv2.dilate(M[k].astype(np.uint8), np.ones((3, 3), np.uint8)) > 0; cov[k] = c1[qb[:, 1], qb[:, 0]]
blen = np.bincount(BI, minlength=len(BL)).astype(float)
static = dict(ben_lines=len(BL), ben_len=int(len(BP)), kinds={k: int((Bkind == k).sum()) for k in set(Bkind)},
              touched_by_text={k: dict(lines=int(touch[k].sum()), len=int(blen[touch[k]].sum())) for k in touch},
              ben_len_under_mask_1px={k: dict(px=int(cov[k].sum()), share=round(float(cov[k].mean()), 4), lines_with_10pct=int(((np.bincount(BI, cov[k], len(BL)) / np.maximum(blen, 1)) >= 0.1).sum())) for k in MASKS})
print('static', json.dumps(static), flush=True)


def score_run(rd):
    sh = [e for e in json.load(open(rd + '44_shown.json', encoding='utf8')) if e.get('state') != 'sheet']
    P, I = samples(sh); d, _ = BT.query(P, k=1, workers=-1); q = np.clip(np.round(P).astype(int), 0, [W - 1, H - 1])
    n = len(sh); L = np.bincount(I, minlength=n).astype(float); near8 = np.bincount(I, d <= 8, n) / np.maximum(L, 1); fl = near8 < 0.2; f = d > 5
    r = dict(lines=n, len=int(len(P)), false_len=int(f.sum()), false_lines=int(fl.sum()), false_lines_len=int(L[fl].sum()), text={})
    for k in ('Sref', 'I2', 'B2'):
        on = WIN[k][q[:, 1], q[:, 0]]; share = np.bincount(I, on, n) / np.maximum(L, 1); most = fl & (share >= 0.5)
        r['text'][k] = dict(false_len_on_text=int((f & on).sum()), share=round(float((f & on).sum() / max(1, f.sum())), 4), false_lines_mostly_on_text=int(most.sum()), their_len=int(L[most].sum()))
        if k in WINN: r['text'][k]['false_len_on_near_street_text'] = int((f & WINN[k][q[:, 1], q[:, 0]]).sum())
    if len(P):
        dd, _ = cKDTree(P).query(BP, k=1, workers=-1); ok = dd <= 5
    else: ok = np.zeros(len(BP), bool)
    found = (np.bincount(BI, ok, len(BL)) / np.maximum(blen, 1)) >= 0.5
    return r, found


out = dict(static=static, stored={}, masked={})
FOUND = {}
for c, pat in STORED.items():
    rows = []
    for g in range(6):
        r, fd = score_run(pat.format(g=g)); FOUND[(c, g)] = fd; r['ben_found'] = int(fd.sum()); r['ben_found_touched_Sref'] = int((fd & touch['Sref']).sum()); r['ben_found_touched_I2'] = int((fd & touch['I2']).sum()); rows.append(r)
    out['stored'][c] = rows; mm = lambda f: round(float(np.mean([f(x) for x in rows])), 4)
    out['stored_mean'] = out.get('stored_mean', {}); out['stored_mean'][c] = dict(false_len=mm(lambda x: x['false_len']), false_lines=mm(lambda x: x['false_lines']), ben_found=mm(lambda x: x['ben_found']),
        **{f'{k}_share_false_len_on_text': mm(lambda x, k=k: x['text'][k]['share']) for k in ('Sref', 'I2', 'B2')}, **{f'{k}_false_lines_mostly_on_text': mm(lambda x, k=k: x['text'][k]['false_lines_mostly_on_text']) for k in ('Sref', 'I2', 'B2')},
        **{f'{k}_their_len': mm(lambda x, k=k: x['text'][k]['their_len']) for k in ('Sref', 'I2')}, Sref_near_street=mm(lambda x: x['text']['Sref']['false_len_on_near_street_text']))
    print('stored', c, json.dumps(out['stored_mean'][c]), flush=True)
for rd in sorted(glob.glob(E + 'bench/*__*__*/')):
    name = os.path.basename(os.path.normpath(rd)); c = name.split('__')[0]
    if name.endswith('none__none'): continue
    if not os.path.exists(rd + 'runs44/v2_grids.json'): print('incomplete', name); continue
    rows = []
    for g in range(6):
        r, fd = score_run(rd + f'runs44/v2__grid{g}/'); f0 = FOUND[(c, g)]
        r['ben_found'] = int(fd.sum()); r['lost'] = int((f0 & ~fd).sum()); r['gained'] = int((~f0 & fd).sum())
        r['lost_touched_Sref'] = int((f0 & ~fd & touch['Sref']).sum()); r['lost_touched_I2'] = int((f0 & ~fd & touch['I2']).sum()); r['lost_len'] = int(blen[f0 & ~fd].sum()); r['gained_len'] = int(blen[~f0 & fd].sum())
        r['lost_lines'] = [int(i) for i in np.nonzero(f0 & ~fd)[0]]
        rows.append(r)
    gj = json.load(open(rd + 'runs44/v2_grids.json', encoding='utf8')).get('paired', {}).get('all', {})
    out['masked'][name] = dict(per_grid=rows, bench_paired={k: gj[k] for k in ('PQ', 'PQ_decided', 'precision', 'recall_interior', 'delete_len', 'draw_len', 'ben_blocks_closed', 'merges', 'fp') if k in gj})
    m = lambda k: round(float(np.mean([x[k] for x in rows])), 2)
    out['masked'][name]['mean'] = {k: m(k) for k in ('false_len', 'false_lines', 'ben_found', 'lost', 'gained', 'lost_touched_Sref', 'lost_touched_I2', 'lost_len', 'gained_len')}
    out['masked'][name]['mean'].update({f'{k}_false_lines_mostly_on_text': round(float(np.mean([x['text'][k]['false_lines_mostly_on_text'] for x in rows])), 2) for k in ('Sref', 'I2')})
    print(name, dict(false_len=m('false_len'), false_lines=m('false_lines'), lost=m('lost'), gained=m('gained'), lost_touched=m('lost_touched_I2')), {k: (v['mean'], v['gains']) for k, v in out['masked'][name]['bench_paired'].items()}, flush=True)
json.dump(out, open(E + 'scores/lines_score.json', 'w'), indent=1)
