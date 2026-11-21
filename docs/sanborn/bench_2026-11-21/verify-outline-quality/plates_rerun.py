"""verify-outline-quality: run MY redirected copy of the patched outlines.py (patched/outlines_redirected.py, from
outline-quality/diffs/outlines.py.diff applied to a copy of tools/sanborn/unet/outlines.py) on other batch plates, with
the batch's own maps, and compare its outlines.json with what outline-quality reported (plates/final/N_variant_outlines.json,
plates/pdf_probe/90_variant_outlines.json). Also runs my redirected copy of the CURRENT outlines.py and compares with the
batch's stored picks22_guided/22-N/outlines.json. Outputs only into plates_rerun/N_{cur,pat}/.
    python plates_rerun.py N [N ...]       (outline step run under the networks' venv, as the batch does)"""
import json, os, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/') + '/'
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; U = SP + 'unet_data/'
VPY = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/tools/sanborn/unet/.venv/Scripts/python.exe'
OQ = HERE + '../outline-quality/'
res = json.load(open(HERE + 'plates_rerun.json')) if os.path.exists(HERE + 'plates_rerun.json') else {}


def same_json(p, q):
    if not os.path.exists(q): return None
    a, b = json.load(open(p, encoding='utf8')), json.load(open(q, encoding='utf8'))
    return a == b


def step4(polys):
    out = []
    for poly in polys:
        for s in poly:
            if s['state'] in ('short', 'not on a line') or s.get('paper_edge'): continue
            out.append(dict(a=s['a'], b=s['b'], state='green' if s['state'] == 'on print' else 'orange'))
    return out


for N in sys.argv[1:]:
    row = {}
    for tag, py in (('cur', HERE + 'current_outlines_redirected.py'), ('pat', HERE + 'patched/outlines_redirected.py')):
        out = HERE + f'plates_rerun/{N}_{tag}/'; t0 = time.time()
        r = subprocess.run([VPY, py, N, U + f'{N}_pred_area_ng1.png', U + f'{N}_lines_lines_ng1.png', out], cwd=HERE, capture_output=True, text=True)
        if r.returncode: print(N, tag, 'FAILED', r.stderr[-1500:], flush=True); row[tag] = dict(failed=True); continue
        rep = json.loads(r.stdout.strip().splitlines()[-1]); polys = json.load(open(out + 'outlines.json', encoding='utf8'))
        e = step4(polys)
        row[tag] = dict(seconds=round(time.time() - t0, 1), blocks=rep['blocks'], bridges=rep.get('bridges'), share_on_printed_line=rep['share_on_printed_line_by_length'],
                        states={s: sum(1 for p in polys for x in p if x['state'] == s) for s in sorted({x['state'] for p in polys for x in p})},
                        step4_patched_lines=len(e), step4_patched_green=sum(x['state'] == 'green' for x in e))
        if tag == 'cur':
            row[tag]['equals_batch_stored'] = same_json(out + 'outlines.json', SP + f'picks22_guided/22-{N}/outlines.json')
        else:
            ref = OQ + (f'plates/pdf_probe/{N}_variant_outlines.json' if N == '90' else f'plates/final/{N}_variant_outlines.json')
            row[tag]['equals_outline_quality_variant'] = same_json(out + 'outlines.json', ref)
    res[N] = row; print(N, json.dumps(row), flush=True)
    json.dump(res, open(HERE + 'plates_rerun.json', 'w'), indent=1)
