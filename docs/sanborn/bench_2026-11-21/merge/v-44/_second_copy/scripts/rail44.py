"""v-44: the rail rules on plate 44 against Ben's 28 tracks (picks22_guided/22-44/rail_ben.page_2026-11-21.json; the
rail_ben.json beside it still has 26), for every bins image of bins44.py.

    python -B rail44.py      -> v-44/rail/NAME_tracks.json, NAME_score.json/.jpg and v-44/rail44.json

For each v-44/bins/NAME.png: the rail agent's rail_tracks_copy.py (bench rail/, the repo's rail_tracks.py with its input
and output redirected; diff-checked) traces the tracks, then the rail agent's score_rail_bench.py scores them (railroad
and streetcar, 10 and 30 px; with --bins, the bin-level recall and the bin ink far from his tracks). Read-only on the
repo; both scripts run with cwd data/sanborn and write only into v-44/rail/."""
import json, os, subprocess, sys, concurrent.futures as cf
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'hooks'))
from common import V, DATA, BENCH, mine  # noqa: E402
RT, SC = BENCH + 'rail/rail_tracks_copy.py', BENCH + 'rail/score_rail_bench.py'
TRUTH = DATA + 'picks22_guided/22-44/rail_ben.page_2026-11-21.json'; O = V + 'rail/'


def one(name):
    b = V + f'bins/{name}.png'; t = mine(O + f'{name}_tracks.json'); s = O + f'{name}_score'
    e = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    if not os.path.exists(t):
        r = subprocess.run(['python', '-B', RT, '44', b, t], cwd=DATA, capture_output=True, text=True, env=e)
        if r.returncode: return name, 'tracks failed ' + r.stderr[-500:]
    r = subprocess.run(['python', '-B', SC, '44', t, TRUTH, s, '--bins', b, '--label', name], cwd=DATA, capture_output=True, text=True, env=e)
    if r.returncode: return name, 'score failed ' + r.stderr[-500:]
    return name, r.stdout


if __name__ == '__main__':
    os.makedirs(O, exist_ok=True)
    names = sorted(f[:-4] for f in os.listdir(V + 'bins') if f.endswith('.png'))
    out = {}
    with cf.ThreadPoolExecutor(4) as ex:
        for n, txt in ex.map(one, names):
            print('==', n); print(txt, flush=True)
            if os.path.exists(O + f'{n}_score.json'):
                d = json.load(open(O + f'{n}_score.json'))
                out[n] = {k: dict(bin=d['kinds'][k].get('bin'), **{f'tol{t}': {q: d['kinds'][k][f'tol{t}'][q] for q in ('recall', 'precision', 'false_len', 'cross_kind_len', 'found', 'partial', 'missed', 'false_tracks', 'false_tracks_len')} for t in (10, 30)})
                          for k in ('railroad', 'streetcar')}
                out[n]['n_rule'] = d['n_rule']; out[n]['rule_px'] = d['rule_px']
    json.dump(dict(truth=TRUTH, scorer=SC, tracer=RT, runs=out), open(V + 'rail44.json', 'w'), indent=1)
