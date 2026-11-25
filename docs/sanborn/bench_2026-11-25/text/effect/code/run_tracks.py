"""run_tracks.py (text/effect, 25 Nov 2026): rule tracks from a bins PNG with the byte copy of rail_tracks.py
(code/orig, sha256 16a4c4ed..., as tools/sanborn/unet), exactly as its run() makes them, minus the write to unet_data
(same as diag/rail5 run_tracks5.py --which orig). Writes only inside text/effect.
    cd data/sanborn; python -B bench_2026-11-25/text/effect/code/run_tracks.py N BINS.png OUT.json"""
import sys, os, json, importlib.util
sys.dont_write_bytecode = True
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
N, bp, out = sys.argv[1:4]
assert os.path.normcase(os.path.abspath(out)).startswith(os.path.normcase(ROOT) + os.sep), out
spec = importlib.util.spec_from_file_location('rail_tracks_orig', os.path.join(HERE, 'orig', 'rail_tracks.py')); rt = importlib.util.module_from_spec(spec); spec.loader.exec_module(rt)
B = cv2.imread(bp, 0)
rr = rt.railroad_tracks((B == 4).astype(np.uint8)); car = rt.streetcar_tracks((B == 5).astype(np.uint8))
tr = [dict(kind=k, src='rule', pts=[[round(float(x), 1), round(float(y), 1)] for x, y in p]) for k, P in (('railroad', rr), ('streetcar', car)) for p in P]
json.dump(dict(plate=N, bins=bp, note='text/effect run, not ground truth', tracks=tr), open(out, 'w', encoding='utf8'), separators=(',', ':'))
pl = lambda k: sum(rt.plen(t['pts']) for t in tr if t['kind'] == k)
print(f"plate {N} {os.path.basename(bp)}: railroad {sum(t['kind'] == 'railroad' for t in tr)} tracks {pl('railroad'):.0f} px | streetcar {sum(t['kind'] == 'streetcar' for t in tr)} tracks {pl('streetcar'):.0f} px", flush=True)
