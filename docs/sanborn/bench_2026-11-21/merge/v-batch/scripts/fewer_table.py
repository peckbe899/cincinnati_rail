"""merge/v-batch: fewer.json + lostcheck.json as one table, one row per plate with fewer editor lines or blocks than the
batch or B, with a reason code.   python -B fewer_table.py -> v-batch/fewer_table.csv
Line reason (per comparison): D = all of the shortfall is step 4's two new drops ('not on a line', 'on rail'): with
those sides kept the merged step has at least as many editor lines; J = fewer lines even with them kept, but at least as
much line length (collinear pieces joined into one line by the rings); '-' = shown length lower than the other run's.
Block reason: lost blocks of the other run, each 'T' = the merged step had the block (N_blockinst.png) but its outline
was traced to under 3 sides and dropped, 'N' = no merged block there (no marker of 2,000 px)."""
import csv, json
import common as C
F = json.load(open(C.ME + 'fewer.json')); LC = json.load(open(C.ME + 'lostcheck.json'))
rows = []
for n, x in F.items():
    L = x['lines']; m, a = L['merged'], L['kept_all']; code = {}
    for X in ('batch', 'B'):
        if f'editor lines vs {X}' in x['fewer']:
            e = L[X]; code[X] = ('D' if a[0] >= e[0] else ('J' if a[1] >= e[1] else 'L')) + ('' if m[1] >= e[1] else '-')
    bl = {}
    for k in ('vs batch', 'vs B'):
        if n in LC and k in LC[n]: bl[k] = ''.join('T' if l['verdict'].startswith('instance') else 'N' for l in LC[n][k])
    d = L['dropped']
    rows.append(dict(plate=n, group=x['group'], fewer='; '.join(x['fewer']), lines_merged=m[0], len_merged=m[1], lines_kept_all=a[0], len_kept_all=a[1], lines_batch=L['batch'][0], len_batch=L['batch'][1],
                     lines_B=L['B'][0], len_B=L['B'][1], not_on_a_line=f"{d.get('not on a line', [0, 0])[0]} / {d.get('not on a line', [0, 0])[1]}", on_rail=f"{d.get('on rail', [0, 0])[0]} / {d.get('on rail', [0, 0])[1]}",
                     line_reason_vs_batch=code.get('batch', ''), line_reason_vs_B=code.get('B', ''), blocks_merged=x['blocks']['merged'], blocks_batch=x['blocks']['batch'], blocks_B=x['blocks']['B'],
                     lost_blocks_vs_batch=bl.get('vs batch', ''), lost_blocks_vs_B=bl.get('vs B', ''),
                     new_blocks_vs_batch=x['blocks'].get('vs batch', {}).get('new', ''), new_blocks_vs_B=x['blocks'].get('vs B', {}).get('new', '')))
with open(C.mine(C.ME + 'fewer_table.csv'), 'w', newline='', encoding='utf8') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(sorted(rows, key=lambda r: C.order(r['plate'])))
print(len(rows), 'rows')
for r in rows:
    if r['line_reason_vs_batch'].endswith('-') or r['line_reason_vs_B'].endswith('-') or r['lost_blocks_vs_batch'] or r['lost_blocks_vs_B']: print(r)
