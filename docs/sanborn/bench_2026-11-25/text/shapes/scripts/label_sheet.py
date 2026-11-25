"""Make the cluster label sheet for Ben (shapes prototype, 25 Nov 2026).

    python -B bench_2026-11-25/text/shapes/scripts/label_sheet.py      (from data/sanborn)

Writes labels/ben_label_sheet.json: one entry per cluster of round 1 (clusters.npz, montage/) and round 2
(clusters2.npz, montage2/), in the order of the montage sheets, with the sheet file and row, the cluster size and
median glyph size, and Claude's label where Claude gave one. 'ben' is empty for Ben to fill:
  a character (0-9, A-Z, a-z, ' " . - &) when nearly every glyph in the row (about 24 of 26 or more) is that
  character; 'junk' when no glyph in the row is lettering; 'pair' for two touching figures; leave empty if mixed.
Round 2 holds only the glyphs the round-1 reader did not call junk, so it is the more useful sheet for digits.
"""
import json, os
import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PER_SHEET = 20


def main():
    out = []
    for cfile, mdir, lfile, bases in (('clusters.npz', 'montage', 'claude_round1.json', (('tiny', 0), ('small', 1000), ('large', 2000))),
                                      ('clusters2.npz', 'montage2', 'claude_round2.json', (('small', 3000), ('large', 4000)))):
        C = np.load(os.path.join(HERE, cfile)); L = json.load(open(os.path.join(HERE, 'labels', lfile)))['labels']
        G = {}
        for p in np.unique(C['plate']):
            D = np.load(os.path.join(HERE, 'glyphs', f'{p}.npz')); G[p] = D['hw'].max(1)
        mx = np.array([G[p][i] for p, i in zip(C['plate'], C['idx'])])
        ids = np.unique(C['cl'][C['cl'] >= 0])
        for name, base in bases:
            cids = [int(c) for c in ids if base <= c < base + 1000]
            for j, c in enumerate(cids):
                m = C['cl'] == c
                out.append(dict(cluster=c, clusters_file=cfile, sheet=f'{mdir}/{name}_{j // PER_SHEET:02d}.png', row=j % PER_SHEET + 1,
                                n=int(m.sum()), median_px=int(np.median(mx[m])), claude=L.get(str(c), ''), ben=''))
    json.dump(dict(note=__doc__, n_rows=len(out), rows=out), open(os.path.join(HERE, 'labels', 'ben_label_sheet.json'), 'w'), indent=0)
    print(len(out), 'rows;', sum(1 for r in out if r['claude']), 'with a Claude label')


if __name__ == '__main__':
    main()
