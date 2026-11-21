#!/bin/sh
# Experiment E3 (bench_2026-11-21/rail): a tick's two stroke ends must lie more squarely across the line (|cos| <= A instead of 0.7).
# Hooks on lot lines are slanted S strokes. Rules otherwise as the batch (no map). Writes only into exp/across.
B=bench_2026-11-21/rail; O=$B/exp/across; A=$1; shift
for N in "$@"; do
  python $B/ink_bins_copy.py $N --no-ben --nomap --rail "{\"across\": $A}" --save $O/${N}_a${A}_bins.png --json $O/${N}_a${A}_bins.json > $O/${N}_a${A}.log 2>&1 && python $B/rail_tracks_copy.py $N $O/${N}_a${A}_bins.png $O/${N}_a${A}_rail_rule.json >> $O/${N}_a${A}.log 2>&1 &
done
wait
