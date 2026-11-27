#!/bin/sh
# DEV ONLY: all dev variants on the dev plates, 7 at a time. Run from data/sanborn.
I=bench_2026-11-26/text_fix/integrate
one() {
  N=$1; V=$2
  python -B $I/code/devrun.py $I/out/dev $V $N > $I/work/logs/dev_$N.log 2>&1
  echo "done $N"
}
export -f one 2>/dev/null
{
for N in 3 54A 12 30 19 26A 64A 74 60B 49 48; do echo "$N A,Bf,Bx,BfA,BxA,ABf,ABx,D"; done
echo "93A A,Bf,Bx,BfA,BxA,ABf,ABx,D"
for N in 44 1A 5 2 4 57 86 90 47; do echo "$N A,Bf,BfA,ABf,D"; done
} | xargs -P 7 -L 1 sh -c 'N=$0; V=$1; python -B '"$I"'/code/devrun.py '"$I"'/out/dev $V $N > '"$I"'/work/logs/dev_$N.log 2>&1; echo done $N'
