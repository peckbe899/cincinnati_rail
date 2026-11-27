#!/bin/sh
# DEV ONLY: finder4 (block Upix) on the 21 dev plates from stored finder3 masks, in both step orders. Run from data/sanborn.
I=bench_2026-11-26/text_fix/integrate
for N in 3 54A 12 30 19 26A 64A 74 60B 49 93A 48 44 1A 5 2 4 57 86 90 47; do
  echo "$N block_then_ditto"; echo "$N ditto_then_block"
done | xargs -P 8 -L 1 sh -c 'N=$0; O=$1; python -B '"$I"'/code/devfinal.py '"$I"'/out/dev/F4_$O "{\"block\": \"Upix\", \"order\": \"$O\"}" $N > '"$I"'/work/logs/f4_${O}_$N.log 2>&1; echo done $N $O'
