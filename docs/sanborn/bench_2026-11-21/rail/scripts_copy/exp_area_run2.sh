#!/bin/sh
# Experiment E1b (bench_2026-11-21/rail): as exp_area_run.sh, but blocks only where P(block) > 0.8 (thr 204) and eroded 15 px.
B=bench_2026-11-21/rail; O=$B/exp/area
for N in "$@"; do
  python $B/ink_bins_copy.py $N --no-ben --nomap --area unet_data/${N}_pred_area_ng1.png --area-thr 204 --area-erode 15 --save $O/${N}_area80_bins.png --json $O/${N}_area80_bins.json > $O/${N}_area80.log 2>&1 && python $B/rail_tracks_copy.py $N $O/${N}_area80_bins.png $O/${N}_area80_rail_rule.json >> $O/${N}_area80.log 2>&1 &
done
wait
