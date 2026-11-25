"""Turn a bins PNG into rule tracks with a copy of rail_tracks.py, writing only into diag/rail5 (25 Nov 2026).

    cd data/sanborn
    python -B bench_2026-11-25/diag/rail5/code/run_tracks5.py N BINS.png OUT.json --which orig|proposed [--set JSON]

orig: code/orig/rail_tracks.py (byte copy of the repo's, sha256 16a4c4ed...) with its own railroad_tracks and
streetcar_tracks, exactly as its run() does, minus the write to unet_data. proposed: code/proposed/rail_tracks.py
(rail_rules.diff applied) and its tracks(), TRACKS overridden by --set (e.g. '{"car_reach": 150}' or '{"rr_alone": null}')."""
import sys, os, json, time, importlib.util
sys.dont_write_bytecode = True
import numpy as np, cv2

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)


def load(which):
    src = os.path.join(HERE, which, 'rail_tracks.py')
    spec = importlib.util.spec_from_file_location(f'rail_tracks_{which}', src); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def orig_tracks(rt, B):
    rr = rt.railroad_tracks((B == 4).astype(np.uint8)); car = rt.streetcar_tracks((B == 5).astype(np.uint8))
    return [dict(kind=k, src='rule', pts=[[round(float(x), 1), round(float(y), 1)] for x, y in p]) for k, P in (('railroad', rr), ('streetcar', car)) for p in P]


def main():
    N, bp, out = sys.argv[1:4]
    assert os.path.normcase(os.path.abspath(out)).startswith(os.path.normcase(ROOT) + os.sep), out
    which = sys.argv[sys.argv.index('--which') + 1] if '--which' in sys.argv else 'orig'
    B = cv2.imread(bp, 0); t0 = time.time()
    if which == 'orig': rt = load('orig'); tr = orig_tracks(rt, B); settings = 'orig'
    else:
        rt = load('proposed')
        if '--set' in sys.argv: rt.TRACKS.update(json.loads(sys.argv[sys.argv.index('--set') + 1]))
        tr = rt.tracks(B); settings = dict(rt.TRACKS)
    json.dump(dict(plate=N, bins=bp, settings=settings, note='diag/rail5 run, not ground truth', tracks=tr), open(out, 'w', encoding='utf8'), separators=(',', ':'))
    pl = lambda k: sum(rt.plen(t['pts']) for t in tr if t['kind'] == k)
    print(f"plate {N} {settings}: railroad {sum(t['kind'] == 'railroad' for t in tr)} tracks {pl('railroad'):.0f} px | streetcar {sum(t['kind'] == 'streetcar' for t in tr)} tracks {pl('streetcar'):.0f} px | {time.time() - t0:.0f} s", flush=True)


if __name__ == '__main__':
    main()
