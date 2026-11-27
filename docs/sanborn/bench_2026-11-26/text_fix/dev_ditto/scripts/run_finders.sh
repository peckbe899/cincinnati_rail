#!/bin/sh
# Run finder2 and finder3 (text_v1/code, unchanged) on whole plates that have no stored mask, into dev_ditto/runs/.
# Run from data/sanborn. Usage: sh run_finders.sh PLATE [PLATE ...]   (never a sealed plate)
DD=bench_2026-11-26/text_fix/dev_ditto
mkdir -p $DD/runs/finder2 $DD/runs/finder3
for N in "$@"; do
  case " 6 9 52 56 58 63 35 38 41 66 71 76 84 88 46 92 " in *" $N "*) echo "refusing sealed plate $N"; continue;; esac
  python -B bench_2026-11-25/text_v1/code/finder2.py $N --out $DD/runs/finder2 > $DD/runs/finder2/$N.log 2>&1
  python -B bench_2026-11-25/text_v1/code/finder3.py $N --out $DD/runs/finder3 > $DD/runs/finder3/$N.log 2>&1
  echo "done $N"
done
