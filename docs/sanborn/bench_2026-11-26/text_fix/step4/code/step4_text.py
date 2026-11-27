"""step4_text.py (text_v1/handoff, 26 Nov 2026): the --step4 hook for bench44.py / bench_plate_text.py. The repo's step 4
(blocks_noguide.step4, imported read only, its own KEEP_UNLINED and RAIL_DROP) with one more rule: a side the hand-off
outline step marked 'on text' (outlines_text.py: not on line ink, and mostly over text) is left out, as an 'on rail' one
is. With no 'on text' sides (the control run) it is blocks_noguide.step4 exactly."""
import os, sys
TOOLS = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..', '..', '..', 'tools', 'sanborn', 'unet'))
sys.path.insert(0, os.path.join(TOOLS, '..')); sys.path.insert(0, TOOLS)
import blocks_noguide as BN  # noqa: E402


def step4(polys):
    return BN.step4([[s for s in p if s.get('state') != 'on text'] for p in polys])
