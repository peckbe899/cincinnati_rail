#!/bin/sh
# Run finder3 (and finder3 --off, which is finder2's output) on the dev_block plates that have no finder output yet.
# Run from data/sanborn. Outputs only in dev_block/finders/. (dev_block, 26 Nov 2026)
D=bench_2026-11-26/text_fix/dev_block/finders
for N in "$@"; do
  python -B bench_2026-11-25/text_v1/code/finder3.py $N --out $D/finder3 > $D/logs/f3_$N.log 2>&1
  python -B bench_2026-11-25/text_v1/code/finder3.py $N --off --out $D/finder2_off > $D/logs/f2off_$N.log 2>&1
done
