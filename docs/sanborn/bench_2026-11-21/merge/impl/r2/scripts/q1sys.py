"""merge/impl/r2: the staged outline step under the system python (cv2 4.13, no ximgproc) against the venv (cv2 5.0) (21 Nov 2026).

    python -B q1sys.py [N ...]      -> merge/impl/r2/q1sys.json, runs in merge/impl/r2/q1sys/N/

Each plate: the staged outlines.py --out with the batch's maps under the system python; compared with the venv's run in
r2/plates_final/N (blocks_noguide.py --outlines-only --out): outlines.json byte for byte, the QA numbers and flags.
"""
import json, os, subprocess, sys
import common as C
res = {}
for n in (sys.argv[1:] or ['3', '5', '60B']):
    d = C.IMPL + f'q1sys/{n}/'; os.makedirs(d, exist_ok=True)
    cmd = ['python', '-B', C.SU + 'outlines.py', n, 'area_ng1', 'lines_ng1', '--out', d, '--area-png', C.U + f'{n}_pred_area_ng1.png', '--lines-png', C.U + f'{n}_lines_lines_ng1.png']
    r = subprocess.run(cmd, cwd=C.DATA, capture_output=True, text=True, encoding='utf8', errors='replace', env=C.env())
    if r.returncode: res[n] = dict(error=(r.stdout + r.stderr)[-1500:]); continue
    s, v = json.load(open(d + f'{n}_outlines.json')), json.load(open(C.IMPL + f'plates_final/{n}/{n}_outlines.json'))
    res[n] = dict(outlines_identical=open(d + 'outlines.json', 'rb').read() == open(C.IMPL + f'plates_final/{n}/outlines.json', 'rb').read(),
                  sys=dict(thinning=s['qa'].get('thinning'), skel=s['qa']['line_skel_len_px'], editor_per_line=s['qa']['editor_per_line'], suspect_why=s['suspect_why'], seconds=s['seconds']),
                  venv=dict(thinning=v['qa'].get('thinning'), skel=v['qa']['line_skel_len_px'], editor_per_line=v['qa']['editor_per_line'], suspect_why=v['suspect_why'], seconds=v['seconds']))
    print(n, json.dumps(res[n]), flush=True)
json.dump(res, open(C.IMPL + 'q1sys.json', 'w'), indent=1)
