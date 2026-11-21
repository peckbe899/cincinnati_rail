"""Group totals and the QA flag, before (the batch) and after (each variant), from measure.json.

    python summarize.py [VARIANT ...]   (default: final new mask_only nest_only)  -> summary.json, printed tables

Groups: PDF sheets at 200 ft (24), PDF sheets at 400 ft (8), the census's suspect cut plates (8B 15B 93A 93B) plus 55B
(bad by eye, missed by the census flag), and every other cut plate (regression check; 44 and the four training plates
included, their 'batch' being the legacy run here). Counts only: there is no truth on any of these plates but 44.
"""
import json, os, statistics as st, sys
HERE = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/') + '/'
M = json.load(open(HERE + 'measure.json'))
variants = sys.argv[1:] or ['final', 'new', 'mask_only', 'nest_only']
SUSP = ['8B', '15B', '93A', '93B', '55B']
groups = {'pdf200': [n for n, r in M.items() if r['source'] == 'pdf sheet' and r['ft_per_inch'] == 200],
          'pdf400': [n for n, r in M.items() if r['source'] == 'pdf sheet' and r['ft_per_inch'] == 400],
          'cut_suspect': SUSP,
          'cut_other': [n for n, r in M.items() if r['source'] != 'pdf sheet' and n not in SUSP]}


def agg(ns, run):
    rows = [M[n][run] for n in ns if run in M[n]]
    if not rows: return None
    med = lambda k: round(st.median([r[k] for r in rows if r.get(k) is not None]), 3) if any(r.get(k) is not None for r in rows) else None
    return dict(plates=len(rows), blocks=sum(r['blocks'] for r in rows), holes=sum(r.get('holes', 0) for r in rows), exported=sum(r['exported'] for r in rows),
                exported_len=sum(r['exported_len'] for r in rows), editor_lines=sum(r['editor_lines'] for r in rows), green_share_median=med('green_share'),
                largest_map_median=med('largest_map'), plates_le5_blocks=sum(r['blocks'] <= 5 for r in rows), plates_largest_over_half_map=sum(r['largest_map'] > 0.5 for r in rows),
                edge_lines=sum(r['edge_lines'] for r in rows), suspect=sum(bool(r.get('suspect')) for r in rows), editor_per_line_median=med('editor_per_line'))


out = dict(groups={g: ns for g, ns in groups.items()}, totals={})
for g, ns in groups.items():
    out['totals'][g] = {run: agg(ns, run) for run in ['batch'] + variants}
# QA flag before/after with the census's eye label
qa = {}
for n, r in M.items():
    if 'final' not in r: continue
    qa[n] = dict(eye=r['eye'], before=r['batch'].get('why') if r['batch'].get('suspect') else '', after=r['final'].get('why') if r['final'].get('suspect') else '',
                 largest_map_after=r['final']['largest_map'])
out['qa'] = qa
out['qa_counts'] = dict(before=sum(bool(v['before']) for v in qa.values()), after=sum(bool(v['after']) for v in qa.values()),
                        after_list=sorted([n for n, v in qa.items() if v['after']], key=lambda s: (int(''.join(c for c in s if c.isdigit())), s)),
                        cleared=sorted([n for n, v in qa.items() if v['before'] and not v['after']], key=lambda s: (int(''.join(c for c in s if c.isdigit())), s)),
                        new_flags=sorted([n for n, v in qa.items() if v['after'] and not v['before']], key=lambda s: (int(''.join(c for c in s if c.isdigit())), s)))
# cut plates: how many changed at all, and how
chg = []
for n in groups['cut_other'] + SUSP:
    r = M[n]
    if 'final' not in r or 'batch' not in r: continue
    b, f = r['batch'], r['final']
    if (b['blocks'], b['exported'], b.get('holes', 0)) != (f['blocks'], f['exported'], f.get('holes', 0)):
        chg.append(dict(plate=n, blocks=(b['blocks'], f['blocks']), holes=f.get('holes', 0), exported=(b['exported'], f['exported']), editor_lines=(b['editor_lines'], f['editor_lines']),
                        same_outlines_as_batch=r['final'].get('same_as_batch')))
out['cut_changed'] = chg
json.dump(out, open(HERE + 'summary.json', 'w'), indent=1)
for g in groups:
    print('==', g, len(groups[g]))
    for run, a in out['totals'][g].items():
        if a: print(f'  {run:10s}', a)
print('QA', out['qa_counts'])
print('cut plates changed by final:', len(chg))
for c in chg: print('  ', c)
