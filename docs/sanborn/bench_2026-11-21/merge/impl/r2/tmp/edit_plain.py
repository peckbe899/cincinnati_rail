import sys
p = sys.argv[1]; s = open(p, encoding='utf8', newline='').read()
R = [
("""   a bridging side. Short pieces are dropped. A block whose ring cannot be closed (fewer than two fitted sides, or a ring
   of fewer than three sides) is kept as its plain outline, as before the merge: its fitted sides as they are and its
   short pieces as 'short' sides (step 4 leaves those out); 'open_outlines' counts them. A block with no fitted side at
   all is left out, as before.""",
 """   a bridging side. Short pieces are dropped. A block (or hole) whose ring cannot be closed (fewer than two fitted
   sides, or a ring of fewer than three) is left out (PLAIN_KEEP = False). Checked 21 Nov 2026 (merge/v-batch found
   326 such blocks on 81 of the 104 unplaced plates, some with a real street side, e.g. at the sheet edge of 18B):
   kept as plain outlines (PLAIN_KEEP = True: the fitted sides as they are, the short pieces as 'short' sides, which
   step 4 leaves out; 'open_outlines' counts them) they add 280 outlines (195 blocks, 85 holes) on 83 plates and 226
   editor lines (26k px); by eye 5 of 30 sampled lines are street sides, 5 unsure, 20 lot lines, pipes and tracks (all
   14 hole lines wrong or unsure), and on 44 1 of their 5 lines is on Ben's map while 3 of them are false blocks: over
   the 6 tile grids PQ -0.007 (lower on 4, same on 2), precision -0.0014 (lower on 6), recall +0.0004 (merge/impl/r2
   open_sample.py, open_verdicts.json, paired44.py keep). --plain keep runs it for the bench."""),
("""PLAIN_KEEP = True if ARG.plain is None else ARG.plain == 'keep'     # a block whose ring cannot be closed: its plain outline (True) or nothing (False)""",
 """PLAIN_KEEP = False if ARG.plain is None else ARG.plain == 'keep'    # a block whose ring cannot be closed: its plain outline (True) or nothing (False; see 3)"""),
("""its length on the rail), and 'short' (a short piece of a plain outline, see 3). Every side has paper_edge; bridging sides""",
 """its length on the rail), and 'short' (a short piece of a plain outline, only with PLAIN_KEEP, see 3). Every side has paper_edge; bridging sides"""),
]
for a, b in R:
    assert s.count(a) == 1, a[:120]
    s = s.replace(a, b)
open(p, 'w', encoding='utf8', newline='').write(s)
print('ok')
