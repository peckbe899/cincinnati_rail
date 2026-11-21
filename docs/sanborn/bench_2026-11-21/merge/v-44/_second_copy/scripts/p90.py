"""v-44: the map-edge handling switched off, on plate 90 (a 200-ft sheet taken whole from a PDF; no truth for its
streets, so counts only). Plate 44 is a cut plate: the map-edge code never runs there (N_outlines.json map_ground 'paper').

    python -B p90.py  -> v-44/p90/<variant>/ (outlines.py --out) and v-44/p90.json

Variants (all on the batch's saved maps unet_data/90_pred_area_ng1.png and 90_lines_lines_ng1.png, venv, -B):
  staged           the staged outlines.py
  edge_as_nesting  abl/edge_as_nesting/outlines.py: every side along the map edge paper_edge (outline-nesting's way)
  no_mapmask       abl/no_mapmask/outlines.py: no map mask at all (margin, KEY and title can be block, as in the batch)
Each: step 4 = the staged blocks_noguide.step4; editor lines = the repo's edit_server.clean + sheet; lines within 40 px
inside the map ground's edge (staged run's 90_mapground.png) and in the margin."""
import json, os, subprocess, sys
import numpy as np
import cv2
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'hooks'))
from common import V, DATA, U, STAGED, SHIM, RU, VPY, mine, env  # noqa: E402
O = V + 'p90/'; N = '90'
VAR = dict(staged=STAGED + 'outlines.py', edge_as_nesting=V + 'abl/edge_as_nesting/outlines.py', no_mapmask=V + 'abl/no_mapmask/outlines.py')


def run(name, code):
    d = mine(O + name) + '/'
    if os.path.exists(d + 'outlines.json'): return json.load(open(d + f'{N}_outlines.json'))
    cmd = [VPY, '-B', code, N, 'area_ng1', 'lines_ng1', '--out', d]
    r = subprocess.run(cmd, cwd=DATA, capture_output=True, text=True, encoding='utf8', errors='replace', env=env([STAGED.rstrip('/')]))
    os.makedirs(d, exist_ok=True); open(d + 'log.txt', 'w', encoding='utf8').write(' '.join(cmd) + '\n' + r.stdout + r.stderr)
    if r.returncode: raise SystemExit(name + ' failed: ' + r.stderr[-2000:])
    return json.loads(r.stdout.strip().splitlines()[-1])


if __name__ == '__main__':
    os.makedirs(O, exist_ok=True)
    reps = {k: run(k, c) for k, c in VAR.items()}
    sys.path.insert(0, SHIM); import _ws  # noqa: F401,E402
    sys.path.insert(1, STAGED.rstrip('/')); sys.path.append(RU)
    import blocks_noguide as BN, edit_server as ES  # noqa: E402
    assert os.path.abspath(BN.__file__).replace('\\', '/').startswith(STAGED.rstrip('/')) and os.path.abspath(ES.__file__).replace('\\', '/').startswith(RU)
    im = cv2.imread(DATA + f'cufp/22-{N}.jpg', 0); H, W = im.shape[:2]; del im
    mg = cv2.resize(cv2.imread(O + f'staged/{N}_mapground.png', 0), (W, H), interpolation=cv2.INTER_NEAREST) > 127
    din = cv2.distanceTransform(mg.astype(np.uint8), cv2.DIST_L2, 5)           # inside the map: distance to its edge
    def where(e):
        m = ((np.array(e['a']) + np.array(e['b'])) / 2).round().astype(int); x, y = np.clip(m[0], 0, W - 1), np.clip(m[1], 0, H - 1)
        return 'margin' if not mg[y, x] else ('edge40' if din[y, x] <= 40 else 'map')
    L = lambda e: float(np.hypot(e['b'][0] - e['a'][0], e['b'][1] - e['a'][1]))
    out = dict(note='plate 90, counts only (no truth for its streets)', variants={})
    batch = json.load(open(U + f'{N}_edges.json', encoding='utf8'))
    for name, ed in [('batch (unet_data/90_edges.json)', batch)] + [(k, None) for k in VAR]:
        if ed is None:
            polys = json.load(open(O + f'{name}/outlines.json', encoding='utf8')); ed = BN.step4(polys)
            sides = [s for p in polys for s in p]
            st = {}
            for s in sides:
                if s['state'] == 'short': continue
                k = ('paper_edge ' if s.get('paper_edge') else '') + s['state']; st.setdefault(k, [0, 0.0]); st[k][0] += 1; st[k][1] += L(s)
        else: st = None
        shown = ES.clean(ed)
        g = {}
        for e in ed:
            k = where(e); g.setdefault(k, [0, 0.0, 0]); g[k][0] += 1; g[k][1] += L(e); g[k][2] += e['state'] == 'green'
        v = dict(step4_lines=len(ed), step4_len=round(sum(L(e) for e in ed)), green=sum(e['state'] == 'green' for e in ed), editor_lines=len(shown),
                 by_place={k: dict(n=a, len=round(b), green=c) for k, (a, b, c) in sorted(g.items())})
        if st is not None:
            r = reps[name]; v.update(blocks=r['blocks'], holes=r.get('holes'), on_rail=r.get('on_rail'), rail=r.get('rail'), suspect_why=r.get('suspect_why'), map_ground=r.get('map_ground'),
                                     sides_by_state={k: dict(n=a, len=round(b)) for k, (a, b) in sorted(st.items())})
        out['variants'][name] = v; print(name, json.dumps({k: v[k] for k in v if k != 'sides_by_state'}), flush=True)
    json.dump(out, open(V + 'p90.json', 'w'), indent=1)
