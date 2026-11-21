"""merge/v-eye: my eye verdicts on the random samples (21 Nov 2026), and their tallies -> verdicts.json.
R right, W wrong, U unsure. Samples: samples/{rail,edge,bridges,holes}.json (sample_sides.py, seed 0, uniform by length)
and bins/samples/N.json (bins_view.py sample N 9 1, uniform over the bin's pixels)."""
import json, collections
V = {
 'rail (merged sides dropped on rail; R = a track, right to drop)': ('RRRRRR' 'RRRRRR' 'URRUR' 'R' 'RRRRRR' 'RRRRRR' 'RRRRRR',
   {7: 'track or lot line across lots (3): not a street side, so right to drop', 12: 'lot 16 edge against the yard (3): possible block side', 15: 'ROW edge by the canal (64A)'}),
 'edge (merged sides within 40 px inside the map edge, PDF sheets 90 30 23 21 47)': ('WWWWWW' 'RWWWUW' 'WWRWWW' 'WWWWWR' 'WWWWUW' 'WWUWRW',
   {'banks': [0, 2, 3, 7, 8, 11, 13, 15, 17, 18, 20, 21, 22, 25, 26, 27, 30, 34], 'city limits': [1, 16, 24, 33, 35], 'property or map-limit lines': [4, 5, 9, 12, 19], 'chord': [29], 'street sides': [6, 14, 23, 32], 'unsure': [10, 28, 31]}),
 'bridges (exported bridging sides)': ('RRRWRR' 'WRRRWR' 'RURRRW' 'RWRWWR', {3: 'far bridge across a street (90)', 6: 'street centre / track (1B)', 10: 'creek bank (90)', 17: 'corner chord across a side-street mouth (90)', 19: 'on a track (1B)', 21: 'far bridge along the ROW (1B)', 22: 'on a pipe line in a street (47)'}),
 'holes (exported street-hole sides, plates 5 and 90)': ('RRWWRW' 'RRRRRW' 'RRRRUR' 'RWRRRR', {2: 'lot-line pocket in block 15 (90)', 3: 'same pocket', 5: 'across the mouth of Bailey Ct at Pugh (5)', 11: 'same pocket (90)', 19: 'lot line between lots 15 and 16 (5)'}),
}
B = {  # ink bins, 9 per bin per plate, in sample order
 '90':  {'block line': 'RWWRRRRRR', 'lot line': 'RRWRRRRRU', 'water pipe': 'RWWWWRRRW', 'sewer': 'RRRRRRRRR'},
 '60B': {'block line': 'RRRRRRRRR', 'lot line': 'RWWRRRRRR', 'water pipe': 'RRRRRRRRR', 'sewer': 'WWWRRWWWW'},
 '5':   {'block line': 'RRRRRRRRR', 'lot line': 'RWRRWRUWR', 'water pipe': 'RRRRRRRRR', 'sewer': 'RRRRRRRRR'},
}
BN = {'90': {'block line': 'W 1, 2: the CITY LIMITS line', 'lot line': 'W 2: south side of Muscogee; U 8: curved line in open ground',
             'water pipe': 'W 1: canal/ROW line, 2: a street side, 3: label stroke, 4: block side along the railroad, 8: south side of Carthage Ave'},
      '60B': {'lot line': 'W 1, 2: mid-block alley sides (alley convention still open)', 'sewer': 'W 0, 1, 5, 8: the cut sheet edge (a street side); 2, 6, 7: pieces of block lines'},
      '5': {'lot line': 'W 1: a pipe line in an alley, 4: an alley side, 7: a block side by the church; U 6: building outline corner'}}
out = {}
for k, (s, notes) in V.items():
    out[k] = dict(n=len(s), tally=dict(collections.Counter(s)), verdicts=s, notes=notes)
bins = {}
for n, d in B.items():
    bins[n] = {b: dict(n=len(s), tally=dict(collections.Counter(s)), verdicts=s) for b, s in d.items()}
tot = collections.defaultdict(collections.Counter)
for n, d in B.items():
    for b, s in d.items(): tot[b].update(s)
out['ink bins'] = dict(per_plate=bins, total={b: dict(c) for b, c in tot.items()}, notes=BN)
json.dump(out, open('../verdicts.json', 'w'), indent=1)
for k, v in out.items():
    print(k, v.get('n'), v.get('tally') or v['total'])
