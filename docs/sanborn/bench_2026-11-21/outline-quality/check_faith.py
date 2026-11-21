"""outline-quality: outlines_oq.py with no switches must be outlines.py exactly.
    python check_faith.py [PYTHON]
Runs outlines_oq.py (default params) on plate 44 with the batch maps (area_ng1 + lines_ng1) and with the guided maps
(edge_v1 + lines_v2) into runs/_faith_*/, and compares outlines.json byte for byte with bench44/runs/batch/outlines.json
(made by the bench's exact copy of outlines.py) and with the stored picks22_guided/22-44/outlines.json; the block masks
are compared too. Writes faith.json here."""
import hashlib, json, os, subprocess, sys, time
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/') + '/'
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; U = SP + 'unet_data/'
PY = sys.argv[1] if len(sys.argv) > 1 else 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/tools/sanborn/unet/.venv/Scripts/python.exe'
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()[:16]
res = dict(python=PY)
for tag, area, lines, ref, refmask in (('batch', U + '44_pred_area_ng1.png', U + '44_lines_lines_ng1.png', HERE + '../bench44/runs/batch/outlines.json', HERE + '../bench44/runs/batch/44_blockmask.png'),
                                        ('guided', U + '44_pred_edge_v1.png', U + '44_lines_lines_v2.png', SP + 'picks22_guided/22-44/outlines.json', U + '44_blockmask.png')):
    out = HERE + f'runs/_faith_{tag}_{"venv" if "venv" in PY else "sys"}/'
    t0 = time.time(); r = subprocess.run([PY, HERE + 'outlines_oq.py', '44', area, lines, out], cwd=SP, capture_output=True, text=True)
    if r.returncode: print(r.stderr[-3000:]); sys.exit(1)
    same = open(out + 'outlines.json', 'rb').read() == open(ref, 'rb').read()
    msame = bool((cv2.imread(out + '44_blockmask.png', 0) == cv2.imread(refmask, 0)).all())
    res[tag] = dict(identical=same, sha=sha(out + 'outlines.json'), ref_sha=sha(ref), blockmask_identical=msame, seconds=round(time.time() - t0, 1), counts=json.loads(r.stdout.strip().splitlines()[-1]))
    print(tag, res[tag], flush=True)
json.dump(res, open(HERE + f'faith_{"venv" if "venv" in PY else "sys"}.json', 'w'), indent=1)
sys.exit(0 if all(res[t]['identical'] and res[t]['blockmask_identical'] for t in ('batch', 'guided')) else 1)
