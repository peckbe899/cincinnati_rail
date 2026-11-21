"""outline-quality variant b_gate: (b) green only where the line network agrees (outlines.py:108).
Run by the bench (bench44_copy.py --outlines variants/v_b_gate.py) as  PYTHON v_b_gate.py N AREA_PNG LINES_PNG OUTDIR"""
import os, sys
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import outlines_oq  # noqa: E402
P = dict(gate=True)
if __name__ == '__main__':
    outlines_oq.main(P)
