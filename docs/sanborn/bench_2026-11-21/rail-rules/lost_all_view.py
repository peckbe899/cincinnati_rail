"""Every railroad track the group 600/60 filter drops on the plates where it drops all of them (rail-rules, 21 Nov 2026):
one tile per track, for checking by eye whether any is a real railroad. Read-only; writes sample/lost_all_railroad.jpg.
    cd data/sanborn
    python bench_2026-11-21/rail-rules/lost_all_view.py"""
import os, json, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
S = json.load(open(os.path.join(HERE, 'batch', 'summary.json'))); R = {r['plate']: r for r in json.load(open(os.path.join(HERE, 'batch', 'tracks_compare.json')))['plates']}
L = [dict(d, label=f"{d['len']}") for N in S['filters']['g600_60']['plates_losing_all_railroad'] for d in R[N]['filters']['g600_60']['dropped']]
print(len(L), 'tracks on', S['filters']['g600_60']['plates_losing_all_railroad'])
json.dump(L, open(os.path.join(HERE, 'sample', 'lost_all_railroad.json'), 'w'), indent=1)
subprocess.run([sys.executable, os.path.join(HERE, 'montage.py'), os.path.join(HERE, 'sample', 'lost_all_railroad.json'), os.path.join(HERE, 'sample', 'lost_all_railroad.jpg'), '--max', '200', '--cols', '8', '--cell', '230'])
