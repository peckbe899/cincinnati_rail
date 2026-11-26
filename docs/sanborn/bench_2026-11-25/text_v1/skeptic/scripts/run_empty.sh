#!/bin/sh
# Skeptic (26 Nov 2026): the hand-off's ink sorting with an EMPTY text mask. With --text the old 'text by itself' rules of
# ink_bins are switched off; an empty mask masks nothing. So this splits the step-4 rail change into (a) the old rules off
# and (b) the mask itself. Copies of the hand-off code in skeptic/hcode (byte-identical; they write only inside skeptic/).
# Run from data/sanborn. Grounds as handoff/code/run_bins.py: 44_map (--no-ben), 5_now (--no-ben), 5_none.
S=bench_2026-11-25/text_v1/skeptic; R5=bench_2026-11-25/diag/rail5/inputs/
run() { name=$1; N=$2; shift 2
  python -B $S/hcode/ink_bins_text.py $N "$@" --save $S/runs/empty/${name}_empty.png --json $S/runs/empty/${name}_empty.json --text $S/out/empty/${N}_text.png --text-codes 2,3 > $S/runs/empty/${name}_empty.log 2>&1
  python -B $S/hcode/rail_tracks_text.py $N $S/runs/empty/${name}_empty.png $S/runs/empty/${name}_empty_tracks.json --text $S/out/empty/${N}_text.png >> $S/runs/empty/${name}_empty.log 2>&1
  echo "$name done $?"; }
run 44_map 44 --no-ben &
run 5_now 5 --no-ben &
run 5_none 5 --no-ben --edges ${R5}no_such_file.json &
wait
