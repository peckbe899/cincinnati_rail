"""merge/v-batch: the staged outline step (blocks_noguide.py --outlines-only --out) on 8 plates ONE AT A TIME, for seconds per
plate without this check's own parallel jobs (other work on the machine is not controlled; its CPU load is logged).
    python -B timing.py  -> v-batch/timing/N/ (outputs) and v-batch/timing.json
"""
import json, os, subprocess, time
import common as C
PL = ['5', '1B', '60B', '66', '90', '79', '47', '93A']; out = {}
for n in PL:
    d = C.mine(C.ME + f'timing/{n}') + '/'; os.makedirs(d, exist_ok=True)
    load = subprocess.run(['C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe', '-NoProfile', '-Command', '(Get-CimInstance Win32_Processor | Measure-Object -Property LoadPercentage -Average).Average'], capture_output=True, text=True).stdout.strip()
    t = time.time(); r = subprocess.run([C.VPY, '-B', C.SU + 'blocks_noguide.py', n, '--outlines-only', '--out', d], cwd=C.DATA, capture_output=True, text=True, encoding='utf8', errors='replace', env=C.env())
    w = round(time.time() - t, 1); rep = json.load(open(d + f'{n}_outlines.json'))
    same = open(d + 'outlines.json', 'rb').read() == open(C.ME + f'plates/{n}/outlines.json', 'rb').read()
    out[n] = dict(group=C.group(n), exit=r.returncode, wall_s=w, outlines_s=rep.get('seconds'), cpu_load_before=load, same_outlines_as_batch_run=same, rail=rep.get('rail'))
    print(n, out[n], flush=True)
json.dump(out, open(C.mine(C.ME + 'timing.json'), 'w'), indent=1)
