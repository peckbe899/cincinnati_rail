"""outline-quality variant a_markers: (a) one watershed marker per block seed, nothing else changed.
Run by the bench (bench44_copy.py --outlines variants/v_a_markers.py) as  PYTHON v_a_markers.py N AREA_PNG LINES_PNG OUTDIR"""
import os, sys
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import outlines_oq  # noqa: E402
P = dict(markers=True)
if __name__ == '__main__':
    outlines_oq.main(P)
