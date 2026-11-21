"""Final scores of the batch rules and the proposed rules on plate 44 and 1A (rail-rules, 21 Nov 2026). Read-only on the
repo; writes final/.
Configurations (tracks from the same bins; the proposed KEY change finds no KEY on 44 or 1A, so their bins are the batch
rules' bins, checked pixel for pixel in runs/):
  batch          orig/rail_tracks.py (the repo's)
  proposed       proposed/rail_tracks.py tracks() with its TRACKS (group 600/60 railroad filter, streetcar reach 350)
  each change alone, and the other candidate settings: filter s300_30 / s600_60 (single-track form), reach 300 / 500
Bins: 44 as never placed (runs/44_nomap_prop_bins.png), 44 as the batch ran it (with the street map,
runs/44_map_prop_bins.png), 1A (runs/1A_prop_bins.png).
Truth: Ben's 28 tracks on 44 (rail_ben.page_2026-11-21.json); 1A's 10 checked tracks; streetcar also against the rail
agent's bridged scratch truth (5 gaps under street names on 44 bridged; not Ben's file).
Scored with score_rail_bench.py (whole plate: length recall / precision at 10 and 30 px, tracks found / partial / missed,
broken, gaps, false tracks) and fold_score.py (folds A and B).
    cd data/sanborn
    python bench_2026-11-21/rail-rules/final_scores.py"""
import sys, os, json, importlib.util
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from fold_score import fscore
from score_rail_bench import summary_lines, picture
OUT = os.path.join(HERE, 'final'); os.makedirs(OUT, exist_ok=True)


def load(which):
    spec = importlib.util.spec_from_file_location(f'rt_{which}', os.path.join(HERE, which, 'rail_tracks.py')); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


RO = load('orig'); RP = load('proposed')
sys.path.insert(0, HERE); from batch_tracks import drop_group, drop_single
T = {'44': json.load(open('picks22_guided/22-44/rail_ben.page_2026-11-21.json', encoding='utf8')), '1A': json.load(open('picks22_guided/22-1A/rail_ben.json', encoding='utf8')),
     '44br': json.load(open('bench_2026-11-21/rail/exp/44_truth_bridged.json', encoding='utf8'))}
BINS = {'44_nomap': ('44', 'runs/44_nomap_prop_bins.png'), '44_map': ('44', 'runs/44_map_prop_bins.png'), '1A': ('1A', 'runs/1A_prop_bins.png')}


def J(P, kind): return [dict(kind=kind, src='rule', pts=[[round(float(x), 1), round(float(y), 1)] for x, y in p]) for p in P]


res = {}
for bn, (N, bp) in BINS.items():
    B = cv2.imread(os.path.join(HERE, bp), 0); H, W = B.shape
    rr = RO.railroad_tracks((B == 4).astype(np.uint8)); car = {r: RP.streetcar_tracks((B == 5).astype(np.uint8), reach=r) for r in (150, 300, 350, 500)}
    assert J(car[150], 'streetcar') == J(RO.streetcar_tracks((B == 5).astype(np.uint8)), 'streetcar')
    F = {'none': rr, 's600_60': drop_single(rr, 600, 60), 's300_30': drop_single(rr, 300, 30), 'g600_60': drop_group(rr, 600, 60)}
    prop = RP.tracks(B)
    configs = {'batch': J(F['none'], 'railroad') + J(car[150], 'streetcar'),
               'proposed': prop,
               'filter_g600_60_only': J(F['g600_60'], 'railroad') + J(car[150], 'streetcar'),
               'reach350_only': J(F['none'], 'railroad') + J(car[350], 'streetcar'),
               'alt_filter_s300_30': J(F['s300_30'], 'railroad') + J(car[350], 'streetcar'),
               'alt_filter_s600_60': J(F['s600_60'], 'railroad') + J(car[350], 'streetcar'),
               'alt_reach300': J(F['g600_60'], 'railroad') + J(car[300], 'streetcar'),
               'alt_reach500': J(F['g600_60'], 'railroad') + J(car[500], 'streetcar')}
    assert tuple(RP.TRACKS['rr_alone']) == (600, 60) and configs['proposed'] == J(F['g600_60'], 'railroad') + J(car[RP.TRACKS['car_reach']], 'streetcar')
    for cn, tr in configs.items():
        regs = ('all', 'A', 'B') if N == '44' else ('all',)
        o, full = fscore(N, tr, T[N], H, W, regs)
        r = res[f'{bn}|{cn}'] = dict(bins=bn, config=cn, n_rule=full['n_rule'], rule_px=full['rule_px'], folds=o,
                                    whole={k: {f'tol{t}': {x: v for x, v in full['kinds'][k][f'tol{t}'].items() if x not in ('tracks', 'false_track_list')} for t in (10, 30)} for k in ('railroad', 'streetcar')})
        if N == '44':
            ob, _ = fscore(N, tr, T['44br'], H, W, ('all', 'A', 'B')); r['bridged_streetcar'] = {reg: ob[reg]['streetcar'] for reg in ('all', 'A', 'B')}
        json.dump(dict(plate=N, settings=cn, bins=bp, tracks=tr), open(os.path.join(OUT, f'{bn}_{cn}_rail_rule.json'), 'w'), separators=(',', ':'))
        print(f'== {bn} {cn}'); [print('  ' + l) for l in summary_lines(full)]
        if cn in ('batch', 'proposed'): picture(os.path.join(OUT, f'{bn}_{cn}.jpg'), N, tr, T[N], full, H, W)
json.dump(dict(settings=RP.TRACKS, results=res), open(os.path.join(OUT, 'final_scores.json'), 'w'), indent=1)
