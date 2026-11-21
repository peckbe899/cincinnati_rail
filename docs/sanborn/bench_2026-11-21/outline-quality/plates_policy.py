"""outline-quality: indicators of the checked plates under another step-4 policy, from the variant's saved outlines.
    python plates_policy.py TAG POLICY N [N ...]
Reads plates/TAG/N_variant_outlines.json (written by plates_check.py), applies sweep.STEP4[POLICY] and the editor's
clean(), and computes plates_check.indicators. Adds them to plates/TAG/summary.json as variant_<POLICY>."""
import json, os, sys
import numpy as np, cv2
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/') + '/'
sys.path.insert(0, HERE)
import plates_check as PC  # noqa: E402
S, B, SP, U = PC.S, PC.B, PC.SP, PC.U
tag, pol = sys.argv[1], sys.argv[2]; f = HERE + f'plates/{tag}/summary.json'; summ = json.load(open(f))
for N in sys.argv[3:]:
    hdr = cv2.imread(SP + f'cufp/22-{N}.jpg', cv2.IMREAD_UNCHANGED).shape; H, W = hdr[:2]
    alpha = cv2.resize(np.load(SP + f'cufp/{N}/png_alpha_s4.npy').astype(np.float32), (W, H)) > 0.5
    bins = cv2.imread(U + f'{N}_bins.png', cv2.IMREAD_UNCHANGED)
    rail = (cv2.dilate(np.isin(bins, (4, 5)).astype(np.uint8), np.ones((13, 13), np.uint8)) > 0) if bins is not None else None
    polys = json.load(open(HERE + f'plates/{tag}/{N}_variant_outlines.json')); shown = B.clean(S.STEP4[pol](polys))
    summ[N][f'variant_{pol}'] = PC.indicators(polys, shown, PC.sheet(N, W, H), dict(alpha=alpha), rail)
    print(N, pol, json.dumps(summ[N][f'variant_{pol}']), flush=True)
json.dump(summ, open(f, 'w'), indent=1)
