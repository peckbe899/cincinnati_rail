"""Draw order of the block-number candidates (sealed builder A, 26 Nov 2026).
Each plate's candidate list (truth/annot/block_candidates.json, in the order written) is shuffled with
random.Random(plate name) (Python's random, seeded with the plate name string, e.g. '6'). The words are taken in
that order: the first K that are block numbers at 1:1 (K: 3 per plate at 100 and 200 ft, 5 on plate 46 at 400 ft).
    python -B scripts/draw_blocks.py   (run from sealed_A; prints the order)"""
import json, random, os
HERE = os.path.dirname(os.path.abspath(__file__))
C = json.load(open(os.path.join(HERE, '..', 'truth', 'annot', 'block_candidates.json'), encoding='utf8'))
K = {'6': 3, '9': 3, '52': 3, '35': 3, '38': 3, '41': 3, '66': 3, '46': 5}
out = {}
for p, k in K.items():
    labels = list(C[p].keys()); r = random.Random(p); r.shuffle(labels)
    out[p] = [(l, C[p][l]) for l in labels]
    print(p, 'take', k, 'of', len(labels), ':', ' '.join(f'{l}@{x},{y}' for l, (x, y) in out[p]))
json.dump({p: [[l, xy] for l, xy in v] for p, v in out.items()}, open(os.path.join(HERE, '..', 'truth', 'annot', 'block_draw_order.json'), 'w', encoding='utf8'), indent=1, ensure_ascii=False)
