"""Draw the block-number sample (dev_block, 26 Nov 2026).

    cd data/sanborn
    python -B bench_2026-11-26/text_fix/dev_block/scripts/draw.py

For each plate, the candidate list dev_block/candidates/PLATE.txt (every block number seen on the 1/4-size survey, checked
on a contact sheet of the scan) is put in a random order with python's random.Random(PLATE) (the seed is the plate name
as a string), and the first K eligible ones are taken. Eligible: the rough window (centre +- 160 px, i.e. a word up to
200 px across plus the 60 px crop margin) does not overlap the old held-out windows H1-H4. K per plate was fixed before
the draw (below). Writes dev_block/candidates/draw.json (seeds, the full order, the picks) and prints the picks."""
import os, sys, json, random
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__)); DB = os.path.normpath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
from cands import read_cands  # noqa: E402

K = {'3': 5, '54A': 5, '12': 5,                                   # 100 ft: 15
     '30': 4, '19': 4, '26A': 4, '64A': 4, '74': 3, '60B': 3,     # 200 ft: 22
     '49': 4, '93A': 2, '48': 2}                                   # 400 ft: 8
SCALE = {'3': 100, '54A': 100, '12': 100, '30': 200, '19': 200, '26A': 200, '64A': 200, '74': 200, '60B': 200, '49': 400, '93A': 400, '48': 400}
H = {'90': [[5640, 3950, 7140, 4950], [880, 2100, 2380, 3100]], '47': [[7040, 4560, 8540, 5560]], '54A': [[7190, 3950, 8690, 4950]]}
R = 160


def overlaps(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


if __name__ == '__main__':
    out = dict(rule='random.Random(plate).sample(range(n), n); first K eligible (window centre +-160 px not overlapping H1-H4)', K=K, plates={})
    n_id = 0
    for N, k in K.items():
        C = read_cands(N); rng = random.Random(N); order = rng.sample(range(len(C)), len(C))
        picks, skipped = [], []
        for i in order:
            c = C[i]; w = [c['x'] - R, c['y'] - R, c['x'] + R, c['y'] + R]
            if any(overlaps(w, h) for h in H.get(N, [])): skipped.append(dict(i=i, reading=c['reading'], why='overlaps an H window')); continue
            if len(picks) < k: picks.append(dict(i=i, **c))
        out['plates'][N] = dict(scale=SCALE[N], n_candidates=len(C), seed=N, order=order, order_readings=[C[i]['reading'] for i in order], picks=picks, skipped=skipped)
        for p in picks:
            n_id += 1; p['id'] = f'DB{n_id:02d}'
            print(p['id'], N, SCALE[N], p['reading'], p['x'], p['y'], p['note'])
    json.dump(out, open(os.path.join(DB, 'candidates', 'draw.json'), 'w', encoding='utf8'), indent=1, ensure_ascii=False)
    print('total', n_id)
