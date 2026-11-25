"""Put the final measurements side by side: candidates from ink_bins bin 8 against the finder's, per truth crop.

    cd data/sanborn
    python -B bench_2026-11-25/text/words/scripts/summarize.py

Reads out/measure_final_bins.json and out/measure_final_finder.json (measure.py --name final_bins, and
--name final_finder --wtag {N}_finder), and out/rail_check_5.json. Writes out/summary_final.json and prints a table."""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(os.path.dirname(HERE), 'out')
DEV = {'T1': 'development crop (rules tuned on it)', 'T2': 'aggregate seen during development', 'T3': 'aggregate seen during development',
       'T4': 'error breakdown seen once (two-piece check)', 'T5': 'not seen before the final run', 'T6': 'not seen before the final run', 'T7': 'not seen before the final run'}


def pct(a, b): return round(100.0 * a / b, 1) if b else None


def main():
    S = {}
    for src in ('bins', 'finder'):
        f = os.path.join(OUT, f'measure_final_{src}.json')
        if not os.path.exists(f): continue
        for s in json.load(open(f, encoding='utf8'))['summaries']:
            t = s['truth_words']; f_ = t - s['missed']; om = s['orient_multi_piece_words']; oa = s['orient_all']
            S.setdefault(s['crop'], dict(plate=s['plate'], status=DEV.get(s['crop'], '')))[src] = dict(
                truth_words=t, exact=s['exact'], exact_pct=pct(s['exact'], t), merged=s['merged'], split=s['split'], split_merged=s['split+merged'],
                missed=s['missed'], kind_right=s['kind_right'], kind_scored=s['kind_scored'], kind_pct=pct(s['kind_right'], s['kind_scored']),
                orient_multi=om, orient_multi_right_pct=pct(om['right'], sum(om.values())), orient_single_right=oa['right'] - om['right'],
                orient_single_n=sum(oa.values()) - sum(om.values()), false_words=s['false_words'], our_words=s['our_words_in_window'],
                text_px_recall=s['pixels']['recall'], text_px_precision=s['pixels']['precision'], by_truth_kind=s['by_truth_kind'])
    rc = os.path.join(OUT, 'rail_check_5.json')
    out = dict(crops=S, rail_check_5=json.load(open(rc))['results'] if os.path.exists(rc) else None)
    json.dump(out, open(os.path.join(OUT, 'summary_final.json'), 'w', encoding='utf8'), indent=1)
    for T, d in sorted(S.items()):
        for src in ('bins', 'finder'):
            if src not in d: continue
            x = d[src]
            print(f"{T} {d['plate']:>2} {src:6s} words {x['truth_words']:3d} exact {x['exact']:3d} ({x['exact_pct']}%) merged {x['merged']:2d} split {x['split']:2d} "
                  f"s+m {x['split_merged']:2d} missed {x['missed']:2d} | kind {x['kind_right']}/{x['kind_scored']} ({x['kind_pct']}%) | way up, 2+ pieces "
                  f"{x['orient_multi']['right']}/{sum(x['orient_multi'].values())} turned {x['orient_multi']['turned']} | 1 piece {x['orient_single_right']}/{x['orient_single_n']} "
                  f"| false words {x['false_words']}/{x['our_words']} | text px R {x['text_px_recall']} P {x['text_px_precision']}  [{d['status']}]")


if __name__ == '__main__':
    main()
