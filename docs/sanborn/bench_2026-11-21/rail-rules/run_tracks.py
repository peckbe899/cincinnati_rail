"""Turn a bins PNG into rule tracks with rail_tracks.py (orig/ = the repo's, or proposed/), writing only into this folder
(rail-rules, 21 Nov 2026).
    cd data/sanborn
    python bench_2026-11-21/rail-rules/run_tracks.py N BINS.png OUT.json [--orig] [--set '{"car_reach": 300, ...}']
--orig uses orig/rail_tracks.py (the repo's, byte-identical) with its own railroad_tracks / streetcar_tracks, exactly
as its run() does. Otherwise proposed/rail_tracks.py's tracks(), with TRACKS overridden by --set."""
import sys, os, json, time, importlib.util
import numpy as np, cv2

HERE = os.path.dirname(os.path.abspath(__file__))


def load(which):
    src = os.path.join(HERE, which, 'rail_tracks.py')
    spec = importlib.util.spec_from_file_location(f'rail_tracks_{which}', src); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def orig_tracks(rt, B):
    """orig/rail_tracks.py's run(), minus its write"""
    rr = rt.railroad_tracks((B == 4).astype(np.uint8)); car = rt.streetcar_tracks((B == 5).astype(np.uint8))
    return [dict(kind=k, src='rule', pts=[[round(float(x), 1), round(float(y), 1)] for x, y in p]) for k, P in (('railroad', rr), ('streetcar', car)) for p in P]


def main():
    N, bp, out = sys.argv[1:4]
    assert os.path.normcase(os.path.abspath(out)).startswith(os.path.normcase(HERE) + os.sep), out
    B = cv2.imread(bp, 0); t0 = time.time()
    if '--orig' in sys.argv: rt = load('orig'); tr = orig_tracks(rt, B); settings = 'orig'
    else:
        rt = load('proposed')
        if '--set' in sys.argv: rt.TRACKS.update(json.loads(sys.argv[sys.argv.index('--set') + 1]))
        tr = rt.tracks(B); settings = dict(rt.TRACKS)
    json.dump(dict(plate=N, bins=bp, settings=settings, note='rail-rules bench run, not ground truth', tracks=tr), open(out, 'w', encoding='utf8'), separators=(',', ':'))
    pl = lambda k: sum(rt.plen(t['pts']) for t in tr if t['kind'] == k)
    print(f"plate {N} {settings}: railroad {sum(t['kind'] == 'railroad' for t in tr)} tracks {pl('railroad'):.0f} px | streetcar {sum(t['kind'] == 'streetcar' for t in tr)} tracks {pl('streetcar'):.0f} px | {time.time() - t0:.0f} s", flush=True)


if __name__ == '__main__':
    main()
