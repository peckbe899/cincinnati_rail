"""lines_table.py (text/effect, 25 Nov 2026): the plate-44 line results of lines_score.py as one table (6-grid means;
paired gains against each chain's stored run, with the number of grids that gain).
    cd data/sanborn; python -B bench_2026-11-25/text/effect/code/lines_table.py      -> scores/lines_table.json"""
import json, os
E = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/'
S = json.load(open(E + 'scores/lines_score.json')); out = {}
print('STORED (no mask): false length, false lines, false lines mostly on text (Sref / I2), share of false length on text (Sref / I2 / boxes B2), near-street text px')
for c, m in S['stored_mean'].items():
    print(f"  {c:5s} false {m['false_len']:8.0f} px  lines {m['false_lines']:6.1f}  mostly-on-text {m['Sref_false_lines_mostly_on_text']:5.1f} / {m['I2_false_lines_mostly_on_text']:5.1f} ({m['Sref_their_len']:.0f} px)"
          f"  share {100 * m['Sref_share_false_len_on_text']:4.1f}% / {100 * m['I2_share_false_len_on_text']:4.1f}% / {100 * m['B2_share_false_len_on_text']:4.1f}%  near-street {m['Sref_near_street']:.0f}")
print('MASKED: paired mean (grids gaining of 6): PQ, PQ_decided, precision, recall_interior, delete_len, draw_len | false lines mostly on text (I2) | Ben lines lost / gained per grid (lost touched by text)')
for mm in ('I2__lines', 'I2p__lines', 'Sref__lines', 'B2__lines', 'B2L__lines', 'I2__ink', 'Sref__ink', 'B2L__ink'):
    for c in ('base', 'V1S1', 'V1S2', 'V2S1', 'V2S2'):
        n = f'{c}__{mm}'
        if n not in S['masked']: continue
        r = S['masked'][n]; p = r['bench_paired']; m = r['mean']; st = S['stored_mean'][c]
        f = lambda k, d=4: f"{p[k]['mean']:+.{d}f}({p[k]['gains']})"
        out[n] = dict(PQ=p['PQ']['mean'], PQ_gains=p['PQ']['gains'], PQ_decided=p['PQ_decided']['mean'], precision=p['precision']['mean'], precision_gains=p['precision']['gains'], recall_interior=p['recall_interior']['mean'],
                      recall_gains=p['recall_interior']['gains'], delete_len=p['delete_len']['mean'], draw_len=p['draw_len']['mean'], false_len=m['false_len'], false_len_stored=st['false_len'],
                      mostly_on_text=m['I2_false_lines_mostly_on_text'], mostly_on_text_stored=st['I2_false_lines_mostly_on_text'], ben_lost=m['lost'], ben_gained=m['gained'], lost_touched=m['lost_touched_I2'])
        print(f"  {n:18s} PQ {f('PQ')} PQd {f('PQ_decided')} prec {f('precision')} rec {f('recall_interior')} delete {p['delete_len']['mean']:+7.0f} draw {p['draw_len']['mean']:+7.0f}"
              f" | on-text lines {st['I2_false_lines_mostly_on_text']:.1f}->{m['I2_false_lines_mostly_on_text']:.1f} | Ben lost {m['lost']:.1f} gained {m['gained']:.1f} (touched {m['lost_touched_I2']:.1f})")
json.dump(out, open(E + 'scores/lines_table.json', 'w'), indent=1)
