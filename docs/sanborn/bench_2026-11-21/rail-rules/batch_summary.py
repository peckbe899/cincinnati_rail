"""Totals of batch_tracks.py's comparison (rail-rules, 21 Nov 2026). Reads batch/tracks_compare.json and
batch/bins_compare.json; writes batch/summary.json and prints it.
    cd data/sanborn
    python bench_2026-11-21/rail-rules/batch_summary.py"""
import os, json
HERE = os.path.dirname(os.path.abspath(__file__))
D = json.load(open(os.path.join(HERE, 'batch', 'tracks_compare.json'))); R = D['plates']
src = lambda N: 'pdf' if os.path.exists(f'cufp/{N}/source.json') else 'cut'
s = dict(plates=len(R), orig_equals_batch=sum(r['orig_equals_batch'] for r in R), key_plates=sum(r['key_run'] for r in R))
for st in ('batch', 'key', 'full'):
    s[st] = {k: dict(n=sum(r[st][k]['n'] for r in R), px=sum(r[st][k]['px'] for r in R)) for k in ('railroad', 'streetcar')}
s['batch_tracks_in_key'] = {k: sum(1 for r in R for t in r.get('batch_tracks_in_key', []) if t['kind'] == k) for k in ('railroad', 'streetcar')}
s['batch_px_in_key'] = {k: sum(t['len'] for r in R for t in r.get('batch_tracks_in_key', []) if t['kind'] == k) for k in ('railroad', 'streetcar')}
s['key_tracks_in_key_after'] = sum(len(r.get('key_tracks_in_key', [])) for r in R)
s['plates_with_batch_tracks_in_key'] = sorted(r['plate'] for r in R if r.get('batch_tracks_in_key'))
s['key_change_other_tracks'] = {k: dict(dn=sum(r['key'][k]['n'] - r['batch'][k]['n'] for r in R), dpx=sum(r['key'][k]['px'] - r['batch'][k]['px'] for r in R)) for k in ('railroad', 'streetcar')}
s['filters'] = {}
for f in D['filters']:
    dr = [d for r in R for d in r['filters'][f]['dropped']]
    s['filters'][f] = dict(dropped=len(dr), dropped_px=sum(d['len'] for d in dr), plates=len({d['plate'] for d in dr}),
                           left_n=sum(r['filters'][f]['n'] for r in R), left_px=sum(r['filters'][f]['px'] for r in R),
                           plates_losing_all_railroad=sorted(r['plate'] for r in R if r['key']['railroad']['n'] > 0 and r['filters'][f]['n'] == 0),
                           top=sorted(((sum(1 for d in r['filters'][f]['dropped']), r['plate']) for r in R), reverse=True)[:12])
s['reach'] = {}
for q in ('300', '350', '500'):
    s['reach'][q] = dict(n=sum(r['reach'][q]['n'] for r in R), px=sum(r['reach'][q]['px'] for r in R), added_px=sum(r['reach'][q]['added_px'] for r in R),
                         plates_fewer_pieces=sum(r['reach'][q]['n'] < r['key']['streetcar']['n'] for r in R))
s['no_railroad'] = {st: sorted(r['plate'] for r in R if r[st]['railroad']['n'] == 0) for st in ('batch', 'key', 'full')}
s['no_rail'] = {st: sorted(r['plate'] for r in R if r[st]['railroad']['n'] + r[st]['streetcar']['n'] == 0) for st in ('batch', 'key', 'full')}
s['no_railroad_by_filter'] = {f: sorted(r['plate'] for r in R if r['filters'][f]['n'] == 0) for f in D['filters']}
s['full_settings'] = D['full_settings']
for g in ('pdf', 'cut'):
    G = [r for r in R if src(r['plate']) == g]
    s[f'by_source_{g}'] = dict(plates=len(G), **{st: {k: dict(n=sum(r[st][k]['n'] for r in G), px=sum(r[st][k]['px'] for r in G)) for k in ('railroad', 'streetcar')} for st in ('batch', 'full')})
json.dump(s, open(os.path.join(HERE, 'batch', 'summary.json'), 'w'), indent=1); print(json.dumps(s, indent=1))
