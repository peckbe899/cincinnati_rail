"""Skeptic (26 Nov 2026): Ben's line ink called text (finder2's check_lines_rail.py output) for each finder2 version it
was run on during development, and for the two classifier pairs, with the files' times. Reads only; writes
skeptic/out/line_ink_by_version.json.   cd data/sanborn; python -B .../sk_versions.py"""
import json, os, time
B = 'bench_2026-11-25/text_v1'; out = {}
rows = [(f'{B}/finder2/out/checks/{v}.json', f'finder2 {v}') for v in ('v1', 'a', 'b', 'c', 'final')] + \
       [(f'{B}/classifier/out/checks/finder3_cnn2.json', 'finder3 cnn2 (shipped)'), (f'{B}/classifier/out/checks/finder3_mlp2.json', 'finder3 mlp2 (not chosen)')]
for f, name in rows:
    d = json.load(open(f)); t = time.strftime('%d %H:%M', time.localtime(os.path.getmtime(f)))
    r = {N: dict(px1=round(100 * d[N]['a_line_ink_1px']['share'], 3), px3=round(100 * d[N]['a_line_ink_3px']['share'], 3)) for N in ('44', '1A', '5')}
    out[name] = dict(file=f, time=t, **r)
    print(f'{name:26s} {t}  ' + ' | '.join(f"{N} {v['px1']:.3f}% / {v['px3']:.3f}%" for N, v in r.items()))
json.dump(out, open(f'{B}/skeptic/out/line_ink_by_version.json', 'w'), indent=1)
