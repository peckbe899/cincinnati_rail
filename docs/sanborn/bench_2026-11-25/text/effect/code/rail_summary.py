"""rail_summary.py (text/effect, 25 Nov 2026): one table of the rail scores (score_rail_bench.py JSON in scores/).
    cd data/sanborn; python -B bench_2026-11-25/text/effect/code/rail_summary.py      -> scores/rail_summary.json"""
import json, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); SC = os.path.join(ROOT, 'scores'); out = {}
RUNS = ['5_nets_base', '5_nets_tS0', '5_nets_tS1', '5_nets_tS1g2', '5_nets_tI', '5_nets_tInp', '5_nets_tI2', '5_none_base', '5_none_tS1', '5_none_tI', '5_none_tI2',
        '44_map_base', '44_map_tS0', '44_map_tS1', '44_map_tS1g2', '44_map_tI', '44_map_tInp', '44_map_tI2r', '44_nomap_base', '44_nomap_tS0', '44_nomap_tI2r']
for r in RUNS:
    s = json.load(open(os.path.join(SC, r + '.json'))); rr = s['kinds']['railroad']['tol10']; sc = s['kinds']['streetcar']['tol10']
    out[r] = dict(railroad_tracks=s['n_rule']['railroad'], railroad_px=s['rule_px']['railroad'], railroad_false_tracks=rr['false_tracks'], railroad_false_px=rr['false_len'],
                  railroad_recall10=rr['recall'] if s['n_truth']['railroad'] else None, railroad_found_partial_missed=[rr['found'], rr['partial'], rr['missed']] if s['n_truth']['railroad'] else None,
                  railroad_bin_px=s['kinds']['railroad']['bin']['bin_px'], streetcar_recall10=sc['recall'], streetcar_precision10=sc['precision'], streetcar_found_partial_missed=[sc['found'], sc['partial'], sc['missed']], streetcar_false_px=sc['false_len'])
    print(f"{r:14s} rr {out[r]['railroad_tracks']:3d} tr {out[r]['railroad_px']:6d} px false {out[r]['railroad_false_tracks']:3d} | rr recall {out[r]['railroad_recall10']} f/p/m {out[r]['railroad_found_partial_missed']} | car R {100*sc['recall']:.1f} P {100*sc['precision']:.1f} f/p/m {out[r]['streetcar_found_partial_missed']}")
json.dump(out, open(os.path.join(SC, 'rail_summary.json'), 'w'), indent=1)
