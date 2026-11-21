"""outline-quality: headline table of finished full bench runs (runs/TAG/bench44.json from bench44_copy.py).
    python compare_runs.py TAG [TAG ...]
Prints all / fold A / fold B per run and writes compare_runs.json."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/') + '/'
K = ['PQ', 'matched', 'fp', 'merges', 'PQ_decided', 'recall_interior', 'precision', 'precision_green', 'precision_orange', 'ben_blocks_closed', 'intact_rings', 'delete_len', 'draw_len']
out = {}
print(f"{'run':22s} {'fold':4s} " + ' '.join(f'{k[:9]:>9s}' for k in K) + f" {'cl1.5':>6s} {'onprint':>7s} {'s':>5s}")
for tag in sys.argv[1:]:
    b = json.load(open(HERE + f'runs/{tag}/bench44.json')); out[tag] = dict(headline=b['headline'], closed_snap1_5={f: b['closure']['faces']['4_editor_shows_snap1.5']['closure'][f]['ben_blocks_closed_iou80'] for f in ('all', 'A', 'B')},
                                                                   batch_share_on_printed_line=b['on_print']['batch_share_on_printed_line_by_length'], seconds=b['meta']['outline_step_seconds'], python=b['meta']['python'],
                                                                   stages={k: dict(PQ=v.get('blocks', {}).get('all', {}).get('PQ'), recall=v['lines']['all']['recall_interior'], precision=v['lines']['all']['precision']) for k, v in b['stages'].items()})
    for f in ('all', 'A', 'B'):
        h = b['headline'][f]
        print(f'{tag:22s} {f:4s} ' + ' '.join(f'{(h[k] if h[k] is not None else float("nan")):9.4g}' for k in K) + f" {out[tag]['closed_snap1_5'][f]:6d} {out[tag]['batch_share_on_printed_line'] or 0:7.3f} {b['meta']['outline_step_seconds']:5.1f}")
json.dump(out, open(HERE + 'compare_runs.json', 'w'), indent=1)
