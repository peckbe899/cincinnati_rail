"""v-final: plate 44's ink bins sorted from the merged block step (bins44/gK: --no-map --edges/--outlines of the staged
bench44 run on grid K) and with no lines or ground (bins44/none), against the sorting with Ben's street map
(bins44/ref, the applied ink_bins.py as a plain run would sort 44). Also: ref against the repo's unet_data/44_bins.png.
Decided ground: the original harness's cache (v-final/orig/cache/decided_half.png, made fresh in this check).
    python -B bins44_cmp.py -> v-final/bins44_cmp.json"""
import json
import numpy as np, cv2
V = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-21/merge/v-final/'
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
NAMES = {1: 'block line', 2: 'lot line', 3: 'building outline', 4: 'railroad', 5: 'streetcar', 6: 'water pipe', 7: 'sewer', 8: 'text and numbers', 9: 'not sorted'}
rd = lambda p: cv2.imread(p, cv2.IMREAD_UNCHANGED)
ref = rd(V + 'bins44/ref/44_bins.png'); repo = rd(SP + 'unet_data/44_bins.png'); H, W = ref.shape
dec = cv2.resize(cv2.imread(V + 'orig/cache/decided_half.png', 0), (W, H), interpolation=cv2.INTER_NEAREST) > 0
out = dict(ref_vs_repo_px_differ=int((ref != repo).sum()), ink_px=int((ref > 0).sum()), ink_on_decided=int(((ref > 0) & dec).sum()))
def cmp(f):
    m = (ref > 0)      # the reference's ink (a few hundred px of ink are left unlabelled by one sorting or the other)
    r = dict(ink_label_mismatch_px=int(((f > 0) != m).sum()), all_ink=round(float((f[m] == ref[m]).mean()), 4), all_ink_decided=round(float((f[m & dec] == ref[m & dec]).mean()), 4), bins={})
    for k, nm in NAMES.items():
        a = ref == k; b = f == k
        r['bins'][nm] = dict(ref_px=int(a.sum()), px=int(b.sum()), ref_in_same=round(float((f[a] == k).mean()), 4) if a.any() else None, same_in_ref=round(float((ref[b] == k).mean()), 4) if b.any() else None,
                             ref_in_same_decided=round(float((f[a & dec] == k).mean()), 4) if (a & dec).any() else None)
    return r
out['none'] = cmp(rd(V + 'bins44/none/44_bins.png'))
for k in range(6): out[f'grid{k}'] = cmp(rd(V + f'bins44/g{k}/44_bins.png'))
G = [out[f'grid{k}'] for k in range(6)]
st = lambda v: dict(mean=round(float(np.mean(v)), 4), sd=round(float(np.std(v, ddof=1)), 4), min=round(float(np.min(v)), 4), max=round(float(np.max(v)), 4))
out['over_grids'] = dict(all_ink=st([g['all_ink'] for g in G]), **{nm: st([g['bins'][nm]['ref_in_same'] for g in G]) for nm in ('block line', 'lot line', 'building outline', 'water pipe', 'sewer')})
json.dump(out, open(V + 'bins44_cmp.json', 'w'), indent=1)
print('ref vs repo px differ', out['ref_vs_repo_px_differ'], '| none all ink', out['none']['all_ink'])
for k in range(6):
    g = out[f'grid{k}']; print(f'grid{k}', g['all_ink'], g['all_ink_decided'], {nm: (g['bins'][nm]['ref_in_same'], g['bins'][nm]['same_in_ref']) for nm in ('block line', 'lot line', 'building outline', 'water pipe', 'sewer')}, 'not sorted', g['bins']['not sorted']['px'])
print(json.dumps(out['over_grids']))
