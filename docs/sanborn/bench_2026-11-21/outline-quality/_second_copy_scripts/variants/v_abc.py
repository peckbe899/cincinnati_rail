"""outline-quality variant abc: (a) + (b) + (c) at the untuned settings.
Run by the bench (bench44_copy.py --outlines variants/v_abc.py) as  PYTHON v_abc.py N AREA_PNG LINES_PNG OUTDIR"""
import os, sys
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import outlines_oq  # noqa: E402
P = dict(markers=True, gate=True, rings=True, colin_off=12.0, join_slide=12, ring_corner=400.0)
if __name__ == '__main__':
    outlines_oq.main(P)
