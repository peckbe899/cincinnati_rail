"""DEV ONLY (integrate, 26 Nov 2026): run finder4.run() on whole plates from finder3's stored masks (work/f3), with given
settings, so a setting (block mode, order) is scored exactly as finder4 runs it. Reads no truth.

    cd data/sanborn
    python -B bench_2026-11-26/text_fix/integrate/code/devfinal.py OUT_DIR '{"block": "Gbox", "order": "ditto_then_block"}' N [N ...]
"""
import json, os, sys
sys.dont_write_bytecode = True
import cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import finder4  # noqa: E402

out, s, plates = sys.argv[1], json.loads(sys.argv[2]), sys.argv[3:]
for N in plates:
    f3 = cv2.imread(os.path.join(HERE, '..', 'work', 'f3', f'{N}_text.png'), cv2.IMREAD_UNCHANGED)
    finder4.run(N, None, out, f3, s)
