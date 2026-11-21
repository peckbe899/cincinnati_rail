"""Check fold_score.py against score_rail_bench.score() on the whole plate, and that folds A + B add up (rail-rules).
    cd data/sanborn
    python bench_2026-11-21/rail-rules/check_fold_score.py RULE.json"""
import sys, json
sys.path.insert(0, 'bench_2026-11-21/rail-rules')
from fold_score import fscore
TJ = json.load(open('picks22_guided/22-44/rail_ben.page_2026-11-21.json', encoding='utf8'))
rule = json.load(open(sys.argv[1]))['tracks']
o, full = fscore('44', rule, TJ, 7219, 10768)
bad = 0
for k in ('railroad', 'streetcar'):
    for tol in (10, 30):
        a = o['all'][k][f'tol{tol}']; f = full['kinds'][k][f'tol{tol}']
        for x in ('recall', 'precision', 'found', 'partial', 'missed', 'broken_interior', 'gaps', 'false_tracks'):
            if a[x] != f[x]: bad += 1; print('MISMATCH', k, tol, x, a[x], f[x])
        A, B = o['A'][k][f'tol{tol}'], o['B'][k][f'tol{tol}']
        print(k, tol, 'all R/P', a['recall'], a['precision'], '| A', A['recall'], A['precision'], A['ben_len'], A['rule_len'], A['n_ben'], A['false_tracks'], '| B', B['recall'], B['precision'], B['ben_len'], B['rule_len'], B['n_ben'], B['false_tracks'],
              '| sums ben', A['ben_len'] + B['ben_len'], a['ben_len'], 'rule', A['rule_len'] + B['rule_len'], a['rule_len'], 'n_ben', A['n_ben'] + B['n_ben'], a['n_ben'])
print('mismatches', bad)
