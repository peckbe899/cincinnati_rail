#!/bin/sh
# Experiment E1 (bench_2026-11-21/rail): the rail rules with blocks taken from the area network's P(block) map, on plates
# without a street map. Writes only into bench_2026-11-21/rail/exp/area. Run from data/sanborn.
B=bench_2026-11-21/rail; O=$B/exp/area
run() {  # plate, extra args, tag
  python $B/ink_bins_copy.py $1 --no-ben --nomap $2 --save $O/$1_$3_bins.png --json $O/$1_$3_bins.json > $O/$1_$3.log 2>&1 && python $B/rail_tracks_copy.py $1 $O/$1_$3_bins.png $O/$1_$3_rail_rule.json >> $O/$1_$3.log 2>&1
}
for N in "$@"; do
  run $N "" base &
  run $N "--area unet_data/${N}_pred_area_ng1.png" area &
  wait
done
