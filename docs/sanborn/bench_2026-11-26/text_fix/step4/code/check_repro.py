"""check_repro.py (text_fix/step4, 27 Nov 2026): do the step4 copies, run with the finder3 masks, give the hand-off's stored
outputs exactly? Reads text_v1/handoff (read only) and step4. Writes step4/scores/repro.json and repro.txt.
    cd data/sanborn; python -B bench_2026-11-26/text_fix/step4/code/check_repro.py
Checks:
  bins     every runs/bins/f3/<run>_<when>.png against handoff/runs/bins/<run>_<when>.png: px that differ (must be 0);
           the f4 set's before runs against the same (must be 0: 'before' has no mask)
  tracks   the tracks of every json (after, after_nojoin, afterstrict, before): the same points (must be equal)
  rail     scores/f3/rail.json against handoff/scores/rail.json for before, after, afterstrict (must be equal)
  bench44  control, f3_ink, f3_states0 against the hand-off's control, ink, states0: per-grid scores, headline and paired
           gains (must be equal)
  plates   5 and 1A control, f3_ink, f3_states0 against the hand-off's: the whole bench_plate scores (must be equal)
  lines    scores/lines.json f3_* against handoff lines.json (counts, lost and gained lines)
  bins44   scores/bins44.json f3 move table and the no-truth agreement against handoff bins44.json"""
import json, os, glob
import numpy as np, cv2
SP = os.getcwd().replace('\\', '/') + '/'; ST = SP + 'bench_2026-11-26/text_fix/step4/'; HO = SP + 'bench_2026-11-25/text_v1/handoff/'
res = {}; L = []
def ok(name, good, detail=''):
    res[name] = dict(ok=bool(good), detail=detail); L.append(f"{'OK  ' if good else 'DIFF'} {name} {detail}")
# bins and tracks
for f in sorted(glob.glob(HO + 'runs/bins/*.png')):
    b = os.path.basename(f); mine = ST + 'runs/bins/f3/' + b
    if not os.path.exists(mine): ok('bins ' + b, False, 'missing'); continue
    d = int((cv2.imread(f, 0) != cv2.imread(mine, 0)).sum()); ok('bins f3 ' + b, d == 0, f'{d} px differ')
    if b.endswith('_before.png') and os.path.exists(ST + 'runs/bins/f4/' + b):
        d = int((cv2.imread(f, 0) != cv2.imread(ST + 'runs/bins/f4/' + b, 0)).sum()); ok('bins f4 ' + b, d == 0, f'{d} px differ')
for f in sorted(glob.glob(HO + 'runs/bins/*_tracks*.json')):
    b = os.path.basename(f); mine = ST + 'runs/bins/f3/' + b
    if not os.path.exists(mine): ok('tracks ' + b, False, 'missing'); continue
    A = json.load(open(f, encoding='utf8'))['tracks']; B = json.load(open(mine, encoding='utf8'))['tracks']
    same = [(t['kind'], t['pts']) for t in A] == [(t['kind'], t['pts']) for t in B]; ok('tracks f3 ' + b, same, f'{len(A)} vs {len(B)} tracks')
    if b.endswith('_before_tracks.json') and os.path.exists(ST + 'runs/bins/f4/' + b):
        B4 = json.load(open(ST + 'runs/bins/f4/' + b, encoding='utf8'))['tracks']; ok('tracks f4 ' + b, [(t['kind'], t['pts']) for t in A] == [(t['kind'], t['pts']) for t in B4])
# rail scores
if os.path.exists(ST + 'scores/f3/rail.json'):
    A = json.load(open(HO + 'scores/rail.json', encoding='utf8')); B = json.load(open(ST + 'scores/f3/rail.json', encoding='utf8'))
    for run in A:
        for w in ('before', 'after', 'afterstrict'):
            ok(f'rail {run} {w}', A[run].get(w) == B.get(run, {}).get(w))
# bench44
for mine, theirs in (('control', 'control'), ('f3_ink', 'ink'), ('f3_states0', 'states0')):
    fm = ST + f'runs/bench44/{mine}/runs44/v2_grids.json'; ft = HO + f'runs/bench44/{theirs}/runs44/v2_grids.json'
    if not os.path.exists(fm): ok(f'bench44 {mine}', False, 'missing'); continue
    A = json.load(open(ft, encoding='utf8')); B = json.load(open(fm, encoding='utf8'))
    for k in ('per_grid', 'headline'): ok(f'bench44 {mine} vs {theirs} {k}', A[k] == B[k])
    if mine != 'control': ok(f'bench44 {mine} vs {theirs} paired', A['paired'] == B['paired'])
    else: ok('bench44 control paired with the stored baseline: every gain 0', all(v['mean'] == 0 and v['min'] == 0 and v['max'] == 0 for fo in B['paired'].values() for v in fo.values()))
    for g in range(6):
        sa = json.load(open(HO + f'runs/bench44/{theirs}/runs44/v2__grid{g}/44_shown.json', encoding='utf8')); sb = json.load(open(ST + f'runs/bench44/{mine}/runs44/v2__grid{g}/44_shown.json', encoding='utf8'))
        ok(f'bench44 {mine} grid{g} 44_shown.json', sa == sb)
# plates
for N in ('5', '1A'):
    for mine, theirs in (('control', 'control'), ('f3_ink', 'ink'), ('f3_states0', 'states0')):
        fm = ST + f'runs/plates/{N}_{mine}/bench_plate.json'; ft = HO + f'runs/plates/{N}_{theirs}/bench_plate.json'
        if not os.path.exists(fm): ok(f'plates {N} {mine}', False, 'missing'); continue
        A = json.load(open(ft, encoding='utf8')); B = json.load(open(fm, encoding='utf8'))
        for k in A:
            if k == 'meta': continue
            ok(f'plates {N} {mine} vs {theirs} {k}', A[k] == B.get(k))
        sa = json.load(open(HO + f'runs/plates/{N}_{theirs}/44_shown.json', encoding='utf8')); sb = json.load(open(ST + f'runs/plates/{N}_{mine}/44_shown.json', encoding='utf8'))
        ok(f'plates {N} {mine} shown lines', sa == sb)
# lines
if os.path.exists(ST + 'scores/lines.json'):
    A = json.load(open(HO + 'scores/lines.json', encoding='utf8')); B = json.load(open(ST + 'scores/lines.json', encoding='utf8'))
    for k, v in A.items():
        cfg = k.split('_grid')[0] if '_grid' in k else k.split('_', 1)[1]
        if cfg not in ('ink', 'states0'): continue
        mk = k.replace(cfg, 'f3_' + cfg, 1) if '_grid' in k else k.split('_', 1)[0] + '_f3_' + cfg
        b = B.get(mk)
        if b is None: ok(f'lines {k}', False, 'missing ' + mk); continue
        same = all(v[x] == b[x] for x in ('control', 'masked', 'ben_found0', 'ben_found1', 'lost', 'gained')) and [l['k'] for l in v['lost_lines']] == [l['k'] for l in b['lost_lines']] and [l['k'] for l in v['gained_lines']] == [l['k'] for l in b['gained_lines']]
        ok(f'lines {k} vs {mk}', same)
# bins44
if os.path.exists(ST + 'scores/bins44.json'):
    A = json.load(open(HO + 'scores/bins44.json', encoding='utf8')); B = json.load(open(ST + 'scores/bins44.json', encoding='utf8'))['f3']
    ok('bins44 f3 move table', A['table_R_rows_X_cols'] == B['table_R_rows_X_cols']); ok('bins44 f3 moved px', A['moved_px'] == B['moved_px'], f"{A['moved_px']} vs {B['moved_px']}")
    ok('bins44 f3 no-truth agreement', A['nets_vs_map'] == B['nets_vs_map'])
bad = [k for k, v in res.items() if not v['ok']]
L.insert(0, f'{len(res)} checks, {len(bad)} differ' + (f': {bad}' if bad else ''))
json.dump(res, open(ST + 'scores/repro.json', 'w', encoding='utf8', newline='\n'), indent=1)
open(ST + 'scores/repro.txt', 'w', encoding='utf8', newline='\n').write('\n'.join(L) + '\n'); print('\n'.join(L[:1] + [x for x in L[1:] if x.startswith('DIFF')]))
