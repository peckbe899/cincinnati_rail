"""Score finder3 and dittofix with text_v1/code/score_text.py on every dev truth set, with fold groups (DEV/CHECK ONLY).

    cd data/sanborn
    python -B bench_2026-11-26/text_fix/fix_ditto/code/score_all.py F3_DIR FIX_DIR OUT_DIR
"""
import os, sys, json, subprocess
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import devdata as D
f3, fix, out = sys.argv[1:4]
SETS = {'ditto': D.DD, 'neg': D.NEG, 't17': D.TV2, 'block': os.path.join(D.TF, 'dev_block', 'truth')}
ST = os.path.join('bench_2026-11-25', 'text_v1', 'code', 'score_text.py')
os.makedirs(out, exist_ok=True)
for nm, tdir in SETS.items():
    crops = json.load(open(os.path.join(tdir, 'crops.json')))
    ids = sorted(k for k in crops if os.path.exists(os.path.join(tdir, f'{k}_mask.png')))
    gA = [k for k in ids if D.fold(crops[k]['plate']) == 'A']; gB = [k for k in ids if D.fold(crops[k]['plate']) == 'B']
    sc = {}
    for k in ids: sc.setdefault(str(crops[k].get('scale_ft_per_inch') or json.load(open('scale_table.json'))[crops[k]['plate']]['ft_per_inch']), []).append(k)
    groups = [f'foldA={",".join(gA)}', f'foldB={",".join(gB)}'] + [f'ft{s}={",".join(v)}' for s, v in sc.items()]
    for meth, d in (('finder3', f3), ('dittofix', fix)):
        cmd = [sys.executable, '-B', ST, os.path.join(d, '{plate}_text.png'), '--codes', '2,3', '--truth', tdir, '--quiet', '--out', os.path.join(out, f'{nm}_{meth}.json')]
        for g in groups:
            if g.split('=')[1]: cmd += ['--group', g]
        r = subprocess.run(cmd, capture_output=True, text=True)
        open(os.path.join(out, f'{nm}_{meth}.txt'), 'w').write(' '.join(cmd) + '\n' + r.stdout + r.stderr)
        print(nm, meth, '\n' + r.stdout[-1500:], flush=True)
