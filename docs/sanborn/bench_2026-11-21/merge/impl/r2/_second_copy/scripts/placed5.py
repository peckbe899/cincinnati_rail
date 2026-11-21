"""merge/impl/r2: do the staged ink rules sort the five placed plates exactly as the repo's bins? (21 Nov 2026)

    python -B placed5.py         -> merge/impl/r2/placed5.json, bins in merge/impl/r2/placed5/

The staged ink_bins.py N --save (system python, the shim _ws first), as a plain run sorts the plate (Ben's street map on
44, the old label on 43, 45, 80, 82A; Ben's rail where he drew it), against unet_data/N_bins.png made by the batch with
the repo's ink_bins.py. run_plates.py's LEGACY_RULES skips these plates on that basis. The tracks (rail_tracks.py,
unchanged) are made from N_bins.png alone, so equal bins give equal tracks.
"""
import concurrent.futures as cf, json, os
import cv2
import common as C
O = C.IMPL + 'placed5/'; os.makedirs(O, exist_ok=True)


def one(n):
    out, js = C.ink_bins(n, O + f'{n}_bins.png')
    a = cv2.imread(O + f'{n}_bins.png', 0); b = cv2.imread(C.U + f'{n}_bins.png', 0)
    return n, dict(px_differ=int((a != b).sum()), identical=bool((a == b).all()), ground_from=js.get('ground_from'), repo_bins_made=os.path.getmtime(C.U + f'{n}_bins.png'))


with cf.ThreadPoolExecutor(3) as ex: res = dict(ex.map(one, ['43', '44', '45', '80', '82A']))
res['all_identical'] = all(v['identical'] for v in res.values())
json.dump(res, open(C.IMPL + 'placed5.json', 'w'), indent=1); print(json.dumps(res, indent=1))
