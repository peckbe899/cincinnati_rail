"""verify-outline-nesting: how sensitive is plate 44 to the hole gate HOLE_PARENT (proposal: 3.0)? (21 Nov 2026)

    python gate_sweep44.py [X ...]       (default 0 1.5 2 2.5 3 4 6 10)  -> gate_sweep44.json + table

For each X: sweeps/outlines_gate{X}.py = benchcopy/outlines_bench_final.py with only 'HOLE_PARENT = 3.0' replaced, then the
harness copy (harness/bench44.py) runs it with --tag gate{X} --no-pic (outline step under the networks' venv, CPU).
X = 0 keeps every hole (the agent's 'new'); X = 3 is the proposal. Headline per fold: is 3.0 a sharp optimum on 44?
"""
import json, os, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/') + '/'
src = open(HERE + 'benchcopy/outlines_bench_final.py', encoding='utf8').read()
OLD = 'HOLE_PARENT = 3.0'
assert src.count(OLD) == 1
xs = sys.argv[1:] or ['0', '1.5', '2', '2.5', '3', '4', '6', '10']
os.makedirs(HERE + 'sweeps', exist_ok=True)


def one(x):
    f = HERE + f'sweeps/outlines_gate{x}.py'
    open(f, 'w', encoding='utf8', newline='\n').write(src.replace(OLD, f'HOLE_PARENT = {float(x)}'))
    tag = f'gate{x}'; rj = HERE + f'harness/runs/{tag}/bench44.json'
    if not os.path.exists(rj):
        r = subprocess.run([sys.executable, HERE + 'harness/bench44.py', '--outlines', f, '--tag', tag, '--no-pic'], cwd=HERE + 'harness', capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
        if r.returncode: return x, dict(error=r.stderr[-1500:])
    j = json.load(open(rj)); rep = json.load(open(HERE + f'harness/runs/{tag}/outline_step.json'))['rep']
    res = {f_: {k: j['headline'][f_][k] for k in ('PQ', 'recall_interior', 'precision', 'precision_green', 'delete_len', 'draw_len')} for f_ in ('all', 'A', 'B')}
    res['holes'] = rep.get('holes'); res['holes_in_open_land'] = rep.get('holes_in_open_land')
    res['decided'] = dict(recall=j['lines_shown']['all'].get('recall_interior_decided'), precision=j['lines_shown']['all'].get('precision_decided'))
    return x, res


with ThreadPoolExecutor(3) as ex:
    out = dict(ex.map(one, xs))
json.dump(out, open(HERE + 'gate_sweep44.json', 'w'), indent=1)
for x in xs:
    r = out[x]
    if 'error' in r: print(x, 'ERROR', r['error']); continue
    print(f"gate {x:>4s} holes {r['holes']:>3} skipped {r['holes_in_open_land']:>3} | " + ' | '.join(
        f"{f_} R {r[f_]['recall_interior']:.4f} P {r[f_]['precision']:.4f} del {r[f_]['delete_len']:>6} draw {r[f_]['draw_len']:>6}" for f_ in ('all', 'A', 'B')) + f" | decided R {r['decided']['recall']} P {r['decided']['precision']}")
