import sys
p = sys.argv[1]; s = open(p, encoding='utf8', newline='').read()
R = [
("""  --outline-args="..."  more options for outlines.py, e.g. --outline-args="--hole-parent 2" (quote a path with spaces)""",
 """  --outline-args="..."  more options for outlines.py, e.g. --outline-args="--hole-parent 2" (split as Windows does: a
              backslash stays a backslash; quote a path with spaces)"""),
("""  --runs      where the run folders go               default data/sanborn/bench44_runs/""",
 """  --runs      where the run folders go               default <the system's temp folder>/sanborn_bench44_runs/ (not in
              the repo: a run is a few hundred MB of pictures and json)"""),
("""          intact rings = exported outline polygons whose every side survives step 4 and whose sides join end to end.""",
 """          intact rings = block outlines (street holes not counted) whose every side survives step 4 (the step 4 in
          use: its rule, or the --step4 hook's) and whose sides join end to end."""),
("""json also goes to stdout; progress goes to stderr. The decided-ground mask is cached in RUNS/cache/.""",
 """json also goes to stdout; progress goes to stderr. The decided-ground mask is cached in RUNS/cache/, under the street
map's sha256 and WMAX (a new street map of 44 makes a new one)."""),
("""import argparse, concurrent.futures as cf, hashlib, importlib.util, json, os, shlex, subprocess, sys, time""",
 """import argparse, concurrent.futures as cf, hashlib, importlib.util, json, os, shlex, subprocess, sys, tempfile, time"""),
("""SP = _ws.DATA; U = SP + 'unet_data/'; RUNS = SP + 'bench44_runs/'""",
 """SP = _ws.DATA; U = SP + 'unet_data/'; RUNS = os.path.join(tempfile.gettempdir(), 'sanborn_bench44_runs').replace('\\\\', '/') + '/'"""),
("""def decided_ground(gt, ng, alpha2):
    \"\"\"Ben's blocks + the street ground between them (half size, cached)\"\"\"
    f = RUNS + 'cache/decided_half.png'
    if os.path.exists(f): return cv2.imread(f, 0) > 0""",
 """def decided_ground(gt, ng, alpha2):
    \"\"\"Ben's blocks + the street ground between them (half size, cached under the street map's sha256 and WMAX)\"\"\"
    f = RUNS + f"cache/decided_half_{sha(SP + 'streetmap/22-44.json')}_{WMAX:g}.png"
    if os.path.exists(f): return cv2.imread(f, 0) > 0"""),
("""    os.makedirs(RUNS + 'cache', exist_ok=True); cv2.imwrite(f, dec.astype(np.uint8) * 255)
    return dec""",
 """    os.makedirs(RUNS + 'cache', exist_ok=True); tmp = f[:-4] + f'.{os.getpid()}.tmp.png'; cv2.imwrite(tmp, dec.astype(np.uint8) * 255); os.replace(tmp, f)   # grid runs may make it at once
    return dec"""),
("""        cmd = [a.python, a.outlines, N, 'area_ng1', 'lines_ng1', '--area-png', a.area, '--lines-png', a.lines, '--out', a.run] + shlex.split(a.outline_args)""",
 """        cmd = [a.python, a.outlines, N, 'area_ng1', 'lines_ng1', '--area-png', a.area, '--lines-png', a.lines, '--out', a.run] + split_args(a.outline_args)"""),
("""def grids(a):""",
 """def split_args(s):
    \"\"\"--outline-args split as on Windows: backslashes kept (C:\\\\Users\\\\...), quotes round a token taken off\"\"\"
    return [t[1:-1] if len(t) >= 2 and t[0] == t[-1] and t[0] in '"\\'' else t for t in shlex.split(s, posix=False)]


def grids(a):"""),
("""    # intact rings
    def ring_state(p):
        kept = all(s['state'] != 'short' and not s.get('paper_edge') for s in p)
        joined = all(np.hypot(*(np.array(p[k]['b']) - np.array(p[(k + 1) % len(p)]['a']))) <= 1.5 for k in range(len(p)))
        return kept, joined
    def area2(r): return abs((r[:, 0] * np.roll(r[:, 1], -1) - np.roll(r[:, 0], -1) * r[:, 1]).sum())
    rs = [ring_state(p) for p in polys]; rc = np.array([poly_centroid(r) if len(r) >= 3 and area2(r) > 1 else r.mean(0) for r in rings]) if rings else np.zeros((0, 2))""",
 """    # intact rings: block outlines (not street holes) whose every side the step 4 in use keeps, joined end to end
    def ring_state(p):
        kept = len(s4([p])) == len(p)
        joined = all(np.hypot(*(np.array(p[k]['b']) - np.array(p[(k + 1) % len(p)]['a']))) <= 1.5 for k in range(len(p)))
        return kept, joined
    def area2(r): return abs((r[:, 0] * np.roll(r[:, 1], -1) - np.roll(r[:, 0], -1) * r[:, 1]).sum())
    bpolys = [p for p in polys if not (p and p[0].get('hole'))]; brings = [np.array([s['a'] for s in p], float) for p in bpolys]
    rs = [ring_state(p) for p in bpolys]; rc = np.array([poly_centroid(r) if len(r) >= 3 and area2(r) > 1 else r.mean(0) for r in brings]) if brings else np.zeros((0, 2))"""),
("""    if a.step4:
        spec = importlib.util.spec_from_file_location('step4mod', a.step4); mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); edges = mod.step4(polys)
    else: edges = BN.step4(polys, keep_unlined=True if a.keep_unlined else None, rail_drop=False if a.rail_show else None)""",
 """    if a.step4:
        spec = importlib.util.spec_from_file_location('step4mod', a.step4); mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); s4 = mod.step4
    else: s4 = lambda ps: BN.step4(ps, keep_unlined=True if a.keep_unlined else None, rail_drop=False if a.rail_show else None)
    edges = s4(polys)"""),
]
for a, b in R:
    assert s.count(a) == 1, a[:120]
    s = s.replace(a, b)
open(p, 'w', encoding='utf8', newline='').write(s)
print('ok')
