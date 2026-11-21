"""outline-quality variant c_rings: (c) closed rings: join collinear sides, corners up to 400 px, bridges otherwise.
Run by the bench (bench44_copy.py --outlines variants/v_c_rings.py) as  PYTHON v_c_rings.py N AREA_PNG LINES_PNG OUTDIR"""
import os, sys
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import outlines_oq  # noqa: E402
P = dict(rings=True, colin_off=12.0, join_slide=12, ring_corner=400.0)
if __name__ == '__main__':
    outlines_oq.main(P)
