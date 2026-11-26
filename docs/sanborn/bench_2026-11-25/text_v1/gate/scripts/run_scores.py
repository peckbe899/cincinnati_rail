"""Gate scorer (26 Nov 2026): run the shared scorer text_v1/code/score_text.py for every method on every truth set.
    cd data/sanborn; python -B bench_2026-11-25/text_v1/gate/scripts/run_scores.py [tag=pattern:codes ...]
Writes gate/out/scores/<method>__<truthset>.txt and .json. Reads masks only; writes only into gate/out/scores."""
import os, subprocess, sys
B = 'bench_2026-11-25'
METHODS = {
    'bin8': ('unet_data/{plate}_bins.png', '8'),
    'v1': (f'{B}/text/finder/out/{{plate}}_finder.png', '2,3,4'),
    'v2': (f'{B}/text_v1/finder2/out/final/{{plate}}_text.png', '2,3'),
    'v2c4': (f'{B}/text_v1/finder2/out/final/{{plate}}_text.png', '2,3,4'),
    'v3': (f'{B}/text_v1/classifier/out/finder3/{{plate}}_text.png', '2,3'),
    'v3c4': (f'{B}/text_v1/classifier/out/finder3/{{plate}}_text.png', '2,3,4'),
}
TRUTH = {
    'heldfix': f'{B}/text_v1/truth-check/heldout_fixed',
    'helddeliv': f'{B}/text_v1/gate/truth_delivered',
    'v2': f'{B}/text_v1/truth',
    'v2fix': f'{B}/text_v1/truth-check/truth_v2_fixed',
}
for s in sys.argv[1:]:
    t, rest = s.split('='); p, c = rest.rsplit(':', 1); METHODS = {t: (p, c)} if not METHODS.get('_keep') else METHODS
OUT = f'{B}/text_v1/gate/out/scores'
for m, (pat, codes) in METHODS.items():
    for tn, td in TRUTH.items():
        grp = ['--group', 'T1T3_44=T1,T2,T3', '--group', 'T4T6T7=T4,T6,T7'] if tn.startswith('v2') else ['--group', 'H1H2_90=H1,H2', '--group', 'H124=H1,H2,H4']
        r = subprocess.run([sys.executable, '-B', f'{B}/text_v1/code/score_text.py', pat, '--codes', codes, '--truth', td,
                            '--out', f'{OUT}/{m}__{tn}.json'] + grp, capture_output=True, text=True)
        open(f'{OUT}/{m}__{tn}.txt', 'w').write(r.stdout + r.stderr)
        print(f'== {m} on {tn}  (exit {r.returncode})'); print(r.stdout[-2500:], r.stderr[-800:])
