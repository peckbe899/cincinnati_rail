"""Cut each method's plate mask to every crop window, so score_text.py can read them with one {crop} pattern
(dev_ditto, 26 Nov 2026). Run only AFTER the truth is final (it reads finder outputs and bins).

    cd data/sanborn; python -B bench_2026-11-26/text_fix/dev_ditto/scripts/cut_masks.py TRUTHDIR [TRUTHDIR ...]

Sources (read only), per plate:
  bin8     unet_data/N_bins.png (value 8 = text bin)
  finder2  text_v1/finder2/out/final/N_text.png if it exists, else dev_ditto/runs/finder2/N_text.png (run here, unchanged code)
  finder3  text_v1/classifier/out/finder3/N_text.png if it exists, else dev_ditto/runs/finder3/N_text.png
Writes dev_ditto/runs/cut/<method>/<crop>.png (crop-sized, values unchanged) and runs/cut/sources.json."""
import json, os, sys
sys.dont_write_bytecode = True
import cv2
HERE = os.path.dirname(os.path.abspath(__file__)); DD = os.path.normpath(os.path.join(HERE, '..'))
V1 = 'bench_2026-11-25/text_v1'


def src(method, p):
    if method == 'bin8': return f'unet_data/{p}_bins.png'
    a = f'{V1}/finder2/out/final/{p}_text.png' if method == 'finder2' else f'{V1}/classifier/out/finder3/{p}_text.png'
    return a if os.path.exists(a) else os.path.join(DD, 'runs', method, f'{p}_text.png')


def main():
    srcs = {}; cache = {}
    for TD in sys.argv[1:]:
        C = json.load(open(os.path.join(TD, 'crops.json')))
        for cid, c in sorted(C.items()):
            for m in ('bin8', 'finder2', 'finder3'):
                f = src(m, c['plate']); srcs.setdefault(m, {})[c['plate']] = f.replace('\\', '/')
                if f not in cache:
                    if len(cache) > 6: cache.clear()
                    cache[f] = cv2.imread(f, cv2.IMREAD_UNCHANGED)
                M = cache[f]; M = M[..., 0] if M.ndim == 3 else M
                x0, y0, x1, y1 = c['win']; o = os.path.join(DD, 'runs', 'cut', m); os.makedirs(o, exist_ok=True)
                cv2.imwrite(os.path.join(o, f'{cid}.png'), M[y0:y1, x0:x1])
    json.dump(srcs, open(os.path.join(DD, 'runs', 'cut', 'sources.json'), 'w'), indent=1); print({m: len(v) for m, v in srcs.items()})


if __name__ == '__main__':
    main()
