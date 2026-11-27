"""Proposals (blockfix steps 1-2) on a dev plate with a given template set, saved for classifier training and checks.
    python -B .../scripts/dump_props.py N TMPL_NAME OUT_DIR        (TMPL_NAME: real_A, real_B, real_all)
Writes OUT_DIR/N_TMPL_NAME.npz: cx, cy, h, d, s (one row per proposal after overlap thinning)."""
import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'code'))
import numpy as np, cv2
import bfcommon as C, blockfix as B

N, tn, od = sys.argv[1], sys.argv[2], sys.argv[3]; C.guard(N)
t0 = time.time(); codes = cv2.imread(C.f3_path(N), 0); p = dict(B.P)
KN = B.Kern(B.load_templates(os.path.join(B.MOD, f'tmpl_{tn}.npz')), p)
I = (codes > 0).astype(np.uint8); K = B.thick(I, p['k_open'])
props, npk = B.propose(K, KN, p); props = [q for q in props if q['d'] != 'blob']   # blob proposals are added where used
os.makedirs(od, exist_ok=True)
np.savez(os.path.join(od, f'{N}_{tn}.npz'), cx=np.array([q['cx'] for q in props]), cy=np.array([q['cy'] for q in props]),
         h=np.array([q['h'] for q in props]), d=np.array([q['d'] for q in props]), s=np.array([q['s'] for q in props]), s0=np.array([q['s0'] for q in props]))
print(N, tn, 'peaks', npk, 'proposals', len(props), f'{time.time() - t0:.0f} s', flush=True)
