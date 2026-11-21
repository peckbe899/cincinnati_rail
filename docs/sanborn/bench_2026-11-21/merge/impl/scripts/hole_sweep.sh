#!/bin/sh
# merge/impl: HOLE_PARENT sweep on plate 44 (batch maps), the staged outline step through the staged bench44.py
cd "$(dirname "$0")"
for hp in 0 1.5 2 2.5 4 6 10; do  # (3 is merged_batch)
  ./run_bench.sh --tag hp_$hp --no-pic "--outline-args=--hole-parent $hp" > /dev/null 2> ../logs_hp_$hp.err &
  while [ "$(jobs -r | wc -l)" -ge 4 ]; do sleep 2; done
done
wait
