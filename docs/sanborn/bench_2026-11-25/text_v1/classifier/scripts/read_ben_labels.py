"""Read Ben's labelling sheets back (classifier step, 26 Nov 2026).

    cd data/sanborn; python -B bench_2026-11-25/text_v1/classifier/scripts/read_ben_labels.py

Reads for_ben/labels_A_digits.csv, labels_B_capitals.csv and labels_C_marks_junk.csv (column 'label': a character, 'junk',
'pair', or empty for a mixed row) and for_ben/members.npz (the glyphs of every row: plate and index into
text/shapes/glyphs/N.npz). Writes data/ben_glyph_labels.npz: plate, idx, label, row_key, changed (1 where 'label' differs
from 'classifier_guess'), and prints how many rows and glyphs each label got. Rows left empty are skipped."""
import csv, os, sys
from collections import Counter
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); FB = os.path.join(HERE, '..', 'for_ben')
OK = set('0123456789') | set('ABCDEFGHIJKLMNOPQRSTUVWXYZ') | set('abcdefghijklmnopqrstuvwxyz') | {'\'', '"', '.', '-', '&', ',', 'junk', 'pair'}


def main():
    M = np.load(os.path.join(FB, 'members.npz')); plates = [str(p) for p in M['plates']]
    out = dict(plate=[], idx=[], label=[], row_key=[], changed=[]); rows = Counter(); bad = []
    for name in ('A_digits', 'B_capitals', 'C_marks_junk'):
        for r in csv.DictReader(open(os.path.join(FB, f'labels_{name}.csv'), encoding='utf-8-sig')):
            lab = r['label'].strip()
            if not lab: continue
            if lab not in OK: bad.append((name, r['row'], lab)); continue
            mem = M[r['row_key'].replace(':', '__')]; rows[lab] += 1
            for p, i in mem:
                out['plate'].append(plates[p]); out['idx'].append(int(i)); out['label'].append(lab); out['row_key'].append(r['row_key'])
                out['changed'].append(int(lab != r['classifier_guess']))
    np.savez_compressed(os.path.join(HERE, '..', 'data', 'ben_glyph_labels.npz'), **{k: np.array(v) for k, v in out.items()})
    g = Counter(out['label'])
    print(len(out['label']), 'glyphs labelled from', sum(rows.values()), 'rows')
    print('rows per label:', dict(rows.most_common())); print('glyphs per label:', dict(g.most_common()))
    if bad: print('NOT UNDERSTOOD (left out):', bad)


if __name__ == '__main__':
    main()
