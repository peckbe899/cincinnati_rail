"""Error tally of the visual audit, with lengths and an estimate of Ben's editor time (visual-cut, 21 Nov 2026).

    python tally.py          -> prints the per-plate table and the ranking, writes tally.json here

Two kinds of number:
  MEASURED (auto)  from audit/N_audit.json (auto_audit.py), audit/N_slivers.json (slivers.py), audit/N_linebins.json
                   (linebins.py): broken sides, open corners, dangling ends, rail-bin lines, small/thin pieces, dropped
                   short length. Plate 44 also from audit/44_merges.json (merges44.py) and audit/44_score.json.
  BY EYE           counted on views/N_overview.jpg and the zoom crops (views/, annotated/): merges across alleys and
                   streets, missed stub alleys and courts, spills into the street, water called block, building walls,
                   lot lines, KEY / scale print, sheet-edge slivers. Counted once; expect +-30 %. Lengths of these are
                   ESTIMATES: count x a typical length on that plate (block side ~ sqrt(median block-mask piece)).
Editor time per operation (ESTIMATES, from the editor's controls in edit_page.html: click+Del, Shift+click+J, select
two+C, N+two clicks): delete a line 3 s; join a break 5 s; close a corner end 3 s; a dangling end (part of a side
missing; two ends per missing piece) 4 s; draw a missing side 8 s; plus 10 s to find a missed alley or street on the print (nothing marks it).
"""
import json, os
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
A = lambda n, f: json.load(open(os.path.join(HERE, 'audit', f'{n}_{f}.json')))

# by eye: through-alley merges (full, partial), stub alleys / courts, street merges, spills / structures in the street,
# water bodies called block, bank lines (length est.), building walls, lot lines, KEY / scale print lines, sheet slivers
EYE = {
    #      scale  tint   alley_full alley_part stub  street  spill water  bank_len  bldg  lot  key  sliver
    '44':  (200, 0.26, None, None, 2, None, 0, 1, 2500, 2, None, 0, 2),
    '5':   (100, 0.49, 9, 7, 5, 0, 5, 0, 0, 0, 1, 0, 3),
    '1A':  (100, 0.75, 4, 3, 2, 0, 2, 0, 0, 0, 0, 0, 2),
    '10':  (100, 0.26, 5, 4, 2, 1, 2, 0, 0, 0, 0, 0, 1),
    '53':  (100, 0.59, 4, 4, 2, 2, 4, 0, 0, 0, 1, 0, 4),
    '66':  (200, 0.31, 3, 3, 3, 0, 0, 0, 0, 0, 2, 0, 0),   # alleys at 200 ft are 15-30 px: likely more than seen at overview scale
    '60B': (200, 0.05, 22, 5, 0, 0, 0, 0, 3000, 0, 0, 0, 0),
    '1B':  (100, 0.66, 1, 2, 1, 3, 2, 1, 1500, 5, 0, 2, 1),
    '2':   (100, 0.49, 4, 4, 1, 2, 2, 1, 500, 6, 0, 0, 2),
    '8B':  (50, 0.65, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0),
    '54B': (100, 0.85, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0),
    '26A': (200, 0.17, 1, 2, 2, 4, 2, 1, 2000, 0, 0, 0, 1),
    '52':  (100, 0.51, 1, 1, 1, 4, 2, 1, 1500, 2, 0, 0, 0),
    '64A': (200, 0.22, 0, 2, 2, 5, 1, 0, 0, 0, 0, 0, 0),
    '3':   (100, 0.26, 1, 1, 1, 2, 1, 2, 2500, 2, 0, 0, 2),
}
T = dict(delete=3, join=5, corner=3, dangle=4, draw=8, find=10)   # dangle: half a drawn side (a missing piece leaves two dangling ends)
rows = {}
for n, (scale, tint, af, ap, stub, street, spill, water, bank_len, bldg, lot, key, sliver) in EYE.items():
    au, sl, lb = A(n, 'audit'), A(n, 'slivers'), A(n, 'linebins')
    side = float(np.sqrt(sl['summary']['median_area']))
    E = au['ends']; br = [e for e in E if e['kind'] == 'broken']; co = [e for e in E if e['kind'] == 'corner']; da = [e for e in E if e['kind'] == 'dangling']
    rail = [l for l in au['lines'] if l['rail'] > 0.5]
    r = dict(plate=n, scale_ft_in=scale, tint=tint, polygons=len(au['polys']), editor_lines=len(au['lines']), editor_len=round(sum(l['L'] for l in au['lines'])),
             dropped_short_len=lb['summary']['short_len'], dropped_short_share=lb['summary']['short_share_of_outline'],
             breaks=len(br) // 2, break_gap=round(sum(e['gap'] for e in br) / 2), corner_ends=len(co), corner_gap=round(sum(e['gap'] for e in co)), dangling_ends=len(da),
             rail_lines=len(rail), rail_len=round(sum(l['L'] for l in rail)), small_or_thin=sl['summary']['small_or_thin'], big_piece_share=sl['summary']['big_share'])
    if n == '44':
        m = A('44', 'merges'); alley_pairs = sum(1 for mm in m['merges'] for g in mm['gaps'] if g < 45); street_pairs = sum(1 for mm in m['merges'] for g in mm['gaps'] if g >= 45)
        r.update(alley_merges=alley_pairs, alley_len_est=round(alley_pairs * 2 * 1.2 * side), street_merges=street_pairs, street_len_est=round(street_pairs * 2 * 1.2 * side),
                 lot_lines=m['false_by_bin'].get('lot line', [0, 0])[0], lot_len=m['false_by_bin'].get('lot line', [0, 0])[1],
                 text_lines=m['false_by_bin'].get('text and numbers', [0, 0])[0], text_len=m['false_by_bin'].get('text and numbers', [0, 0])[1],
                 pipe_lines=m['false_by_bin'].get('water pipe', [0, 0])[0] + m['false_by_bin'].get('sewer', [0, 0])[0],
                 pipe_len=m['false_by_bin'].get('water pipe', [0, 0])[1] + m['false_by_bin'].get('sewer', [0, 0])[1], pq=m['pq']['PQ'])
    else:
        r.update(alley_merges=af + ap, alley_len_est=round(af * 2 * 1.2 * side + ap * 1.0 * side), street_merges=street, street_len_est=round(street * 2 * 1.2 * side),
                 lot_lines=lot, lot_len=round(lot * 0.8 * side), text_lines=None, text_len=None, pipe_lines=None, pipe_len=None)
    r.update(stub_alleys=stub, stub_len_est=round(stub * 2 * 0.5 * side), spills=spill, spill_len_est=round(spill * 1.0 * side), water_bodies=water, bank_len_est=bank_len,
             building_walls=bldg, key_lines=key, slivers=sliver)
    # Ben's time, seconds (ESTIMATE)
    am = r['alley_merges']; sm = r['street_merges']
    t = dict(alleys_streets=(am + sm) * (2 * T['draw'] + 4 * T['corner'] + T['find']) + stub * (2 * T['draw'] + 2 * T['corner'] + T['find']),
             spills=spill * (T['draw'] + 2 * T['delete'] + T['find']), rail=r['rail_lines'] * T['delete'], water_banks=round(bank_len / 300) * T['delete'],
             walls_lots_text_pipes=(bldg * (3 * T['delete'] + T['draw'])) + (r['lot_lines'] or 0) * T['delete'] + (r['text_lines'] or 0) * T['delete'] + (r['pipe_lines'] or 0) * T['delete'] + key * T['delete'],
             small_slivers=r['small_or_thin'] * 3 * T['delete'], broken=r['breaks'] * T['join'], corners=r['corner_ends'] * T['corner'], dangling=r['dangling_ends'] * T['dangle'])
    r['ben_seconds'] = t; r['ben_minutes_total'] = round(sum(t.values()) / 60, 1)
    rows[n] = r
json.dump(rows, open(os.path.join(HERE, 'tally.json'), 'w'), indent=1)
cols = ['scale_ft_in', 'tint', 'polygons', 'editor_len', 'dropped_short_share', 'alley_merges', 'alley_len_est', 'stub_alleys', 'street_merges', 'street_len_est', 'spills', 'water_bodies', 'bank_len_est',
        'rail_lines', 'rail_len', 'building_walls', 'lot_lines', 'key_lines', 'small_or_thin', 'slivers', 'breaks', 'break_gap', 'corner_ends', 'corner_gap', 'dangling_ends', 'ben_minutes_total']
print('plate ' + ' '.join(c[:12] for c in cols))
for n, r in rows.items(): print(f'{n:5s} ' + ' '.join(str(r[c]) for c in cols))
tot = {}
for n, r in rows.items():
    if n == '44': continue
    for k, v in r['ben_seconds'].items(): tot[k] = tot.get(k, 0) + v
print('\nBen time over the 14 audited unplaced plates (min, ESTIMATE):', {k: round(v / 60) for k, v in sorted(tot.items(), key=lambda kv: -kv[1])}, 'total', round(sum(tot.values()) / 60))
print('plate 44 (min):', {k: round(v / 60, 1) for k, v in rows['44']['ben_seconds'].items()}, 'total', rows['44']['ben_minutes_total'])
