"""Run blockfix.apply on dev plates with cached proposals (tuning harness; the shipped CLI makes its own proposals).
    python -B .../scripts/run_fold.py OUT_DIR MODEL_FOLD TMPL_NAME plates... [--opt k=v,...] [--fresh]
MODEL_FOLD: A, B or all (models/cls_<fold>.npz); TMPL_NAME: real_A, real_B, real_all (models/tmpl_<name>.npz and the
proposals models/props/N_<name>.npz). --fresh makes proposals afresh (as the CLI does).
Writes OUT_DIR/N_text.png, N_text.json, N_blocks.json."""
import sys, os, json, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'code'))
import numpy as np, cv2
import bfcommon as C, blockfix as B

a = sys.argv[1:]; opts = {}; fresh = '--fresh' in a; a = [x for x in a if x != '--fresh']
if '--opt' in a:
    i = a.index('--opt')
    for kv in a[i + 1].split(','):
        k, v = kv.split('='); opts[k] = (v in ('1', 'True', 'true')) if isinstance(B.P[k], bool) else (tuple(float(x) for x in v.split('/')) if isinstance(B.P[k], tuple) else type(B.P[k])(v))
    a = a[:i] + a[i + 2:]
od, mf, tn, plates = a[0], a[1], a[2], a[3:]
os.makedirs(od, exist_ok=True)
for N in plates:
    C.guard(N); t0 = time.time(); codes = cv2.imread(C.f3_path(N), 0)
    props = None
    if not fresh:
        z = np.load(os.path.join(B.MOD, 'props', f'{N}_{tn}.npz'))
        props = []
        KN0 = B.Kern(B.load_templates(os.path.join(B.MOD, f'tmpl_{tn}.npz')), dict(B.P, **opts))
        for cx, cy, h, d, s in zip(z['cx'], z['cy'], z['h'], z['d'], z['s']):
            k = KN0.get(str(d), int(h))
            props.append(dict(d=str(d), s=float(s), h=int(h), cx=float(cx), cy=float(cy), box=[cx - k['ww'] / 2, cy - k['hh'] / 2, cx + k['ww'] / 2, cy + k['hh'] / 2]))
        props += B.blobs(B.thick((codes > 0).astype(np.uint8), 5), dict(B.P, **opts))
    out, info, nums, rej = B.apply(N, codes, None, C.scale_of(N), tmpl=os.path.join(B.MOD, f'tmpl_{tn}.npz'), model=os.path.join(B.MOD, f'cls_{mf}.npz'),
                                   return_info=True, props=props, **opts)
    cv2.imwrite(os.path.join(od, f'{N}_text.png'), out)
    json.dump(info, open(os.path.join(od, f'{N}_text.json'), 'w'), indent=1, default=str)
    json.dump(dict(plate=N, numbers=nums, rejected=rej), open(os.path.join(od, f'{N}_blocks.json'), 'w'), indent=1, default=str)
    print(f"{N}: {len(nums)} numbers, {len(rej)} rejected, {info['px_to_text']} px to text, {time.time() - t0:.0f} s", flush=True)
