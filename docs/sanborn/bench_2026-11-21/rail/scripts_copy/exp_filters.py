"""Experiment: post-filters on the rules' railroad tracks (bench_2026-11-21/rail). Read-only on the repo.
  F1 drop_lone_short: railroad tracks < SHORT px with no other railroad track within NEAR px
  F2 drop_in_box: rail tracks inside the printed KEY (census/key_boxes.json)
Scores F1 on 44 (with map and no map) against Ben's 28 tracks, then counts what F1 and F2 remove on every batch plate
(the batch's own unet_data/N_rail_rule.json; 44 and 1A excluded, their files mix in Ben's tracks).
    cd data/sanborn
    python bench_2026-11-21/rail/exp_filters.py [SHORT NEAR]"""
import sys, json, os, re
sys.path.insert(0, 'bench_2026-11-21/rail')
import numpy as np, cv2
import rail_tracks_copy as rt
from rail_variants import drop_lone_short, drop_in_box
from score_rail_bench import score
SHORT = float(sys.argv[1]) if len(sys.argv) > 1 else 600; NEAR = float(sys.argv[2]) if len(sys.argv) > 2 else 60
OUT = 'bench_2026-11-21/rail/exp'; TJ = json.load(open('picks22_guided/22-44/rail_ben.page_2026-11-21.json', encoding='utf8'))
H, W = 7219, 10768
for tag in ('map', 'nomap'):
    T = json.load(open(f'bench_2026-11-21/rail/runs/44_{tag}_rail_rule.json', encoding='utf8'))['tracks']
    for name, tr in (('as batch', T), (f'F1 lone<{SHORT:.0f} near {NEAR:.0f}', drop_lone_short(T, SHORT, NEAR)[0])):
        o = score('44', tr, TJ, H, W)['kinds']['railroad']
        print(f"44 {tag:5s} {name:24s} rr tracks {sum(t['kind'] == 'railroad' for t in tr):3d} | 10px R {100 * o['tol10']['recall']:.1f} P {100 * o['tol10']['precision']:.1f} false {o['tol10']['false_len']} | 30px R {100 * o['tol30']['recall']:.1f} P {100 * o['tol30']['precision']:.1f} false tracks {o['tol30']['false_tracks']} ({o['tol30']['false_tracks_len']} px)")
S = json.load(open('unet_data/run_plates.json', encoding='utf8')); order = lambda n: (int(re.match(r'\d+', n).group()), n)
KB = {k['plate']: k['box'] for k in json.load(open('bench_2026-11-21/rail/census/key_boxes.json')) if k.get('score') and k['score'] >= 0.5}
tot = dict(n=0, px=0, n_rr=0, px_rr=0, key_n=0, key_px=0); drops = []; per = {}
for N in sorted(S, key=order):
    if N in ('44', '1A'): continue
    T = json.load(open(f'unet_data/{N}_rail_rule.json', encoding='utf8'))['tracks']
    keep, drop = drop_lone_short(T, SHORT, NEAR)
    rr = [t for t in T if t['kind'] == 'railroad']; tot['n_rr'] += len(rr); tot['px_rr'] += sum(rt.plen(t['pts']) for t in rr)
    tot['n'] += len(drop); tot['px'] += sum(rt.plen(t['pts']) for t in drop)
    for t in drop:
        p = np.asarray(t['pts']); drops.append(dict(plate=N, len=round(rt.plen(p)), a=[round(v) for v in p[0]], b=[round(v) for v in p[-1]]))
    kd = drop_in_box(T, KB[N])[1] if N in KB else []
    tot['key_n'] += len(kd); tot['key_px'] += sum(rt.plen(t['pts']) for t in kd)
    per[N] = dict(lone_dropped=len(drop), lone_px=round(sum(rt.plen(t['pts']) for t in drop)), rr=len(rr), key_dropped=len(kd))
print(f"batch plates (107, not 44/1A): railroad tracks {tot['n_rr']} ({tot['px_rr']:.0f} px); F1 drops {tot['n']} tracks ({tot['px']:.0f} px); F2 (KEY) drops {tot['key_n']} tracks ({tot['key_px']:.0f} px)")
print('F1 drops per plate (top):', sorted(((v['lone_dropped'], N) for N, v in per.items()), reverse=True)[:25])
json.dump(dict(short=SHORT, near=NEAR, totals=tot, per_plate=per, dropped=drops), open(f'{OUT}/filters_{SHORT:.0f}_{NEAR:.0f}.json', 'w'), indent=1)
json.dump(drops, open(f'{OUT}/lone_dropped_{SHORT:.0f}_{NEAR:.0f}.json', 'w'), indent=1)
