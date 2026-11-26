"""Print a compact table from gate/out/scores/*.json (score_text.py outputs). python -B table.py [truthset ...]"""
import json, os, sys, glob
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'out', 'scores')
sets = sys.argv[1:] or ['heldfix', 'helddeliv', 'v2', 'v2fix']
KINDS = ('street', 'block', 'house', 'adjoin', 'lot', 'lotdim', 'story', 'ditto', 'owner', 'pipe', 'sewer', 'rr', 'bldg', 'other')
for ts in sets:
    print(f'\n##### truth = {ts}')
    for f in sorted(glob.glob(os.path.join(D, f'*__{ts}.json'))):
        m = os.path.basename(f).split('__')[0]; d = json.load(open(f))
        for pn, p in d['pools'].items():
            if pn.startswith('plate_'): continue
            x = p['pix']; k = p['by_kind']
            ks = '  '.join(f"{kk} {k[kk]['recall']:.3f}({k[kk]['words_found']}/{k[kk]['words']})" for kk in KINDS if kk in k)
            print(f"{m:6s} {pn:8s} P {x['precision']:.4f} R {x['recall']:.4f} F1 {x['f1']:.4f} nt {p['nontext_called_text']['share']:.4f} | {ks if pn=='ALL' else ''}")
        for c, r in d['crops'].items():
            x = r['pix']; print(f"{m:6s}   {c:6s} P {x['precision']:.4f} R {x['recall']:.4f} F1 {x['f1']:.4f} nt {r['nontext_called_text']['share']:.4f}")
