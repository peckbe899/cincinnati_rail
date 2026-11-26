"""How many of the classifier's training rows lie inside given windows (for the gate scorer: are any held-out windows in
the training data?). Reads only data/NAME.npz (default train) and the windows file; this script never opens a truth file.
    cd data/sanborn; python -B .../train_overlap.py WINDOWS.json [NAME]
WINDOWS.json: {plate: [[x0, y0, x1, y1], ...]}. Prints, per window, the training rows whose box overlaps it, by source
and by label. To refit without them: build_train.py --exclude WINDOWS.json --out train_ex, then train.py cnn --train
train_ex --out out/model_ex.npz, stack.py out/model_ex.npz --out out/combiner_ex.npz, and finder3.py N --model
out/model_ex.npz --combiner out/combiner_ex.npz (the combiner is fitted on T1-T7 only, so it needs no change, but
its inputs come from the shape model, so it is refitted with it)."""
import json, os, sys
from collections import Counter
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
W = json.load(open(sys.argv[1])); name = sys.argv[2] if len(sys.argv) > 2 else 'train'
D = np.load(os.path.join(HERE, '..', 'data', f'{name}.npz')); bb = D['bbox']; pl = D['plate']
for N, wins in W.items():
    for x0, y0, x1, y1 in wins:
        m = (pl == N) & (bb[:, 0] < x1) & (bb[:, 1] < y1) & (bb[:, 0] + bb[:, 2] > x0) & (bb[:, 1] + bb[:, 3] > y0)
        print(N, [x0, y0, x1, y1], int(m.sum()), 'training rows;', dict(Counter(D['source'][m])), dict(Counter(D['label'][m]).most_common(8)))
