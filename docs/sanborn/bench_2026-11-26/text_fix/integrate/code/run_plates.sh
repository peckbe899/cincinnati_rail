#!/bin/sh
# finder4 on the 10 check plates, whole plates, from the scan (finder3 included), 5 at a time. Run from data/sanborn.
I=bench_2026-11-26/text_fix/integrate
printf "44\n5\n54A\n90\n30\n60B\n47\n49\n93A\n1A\n" | xargs -P 5 -I{} sh -c "python -B $I/code/finder4.py {} --out $I/out/finder4 > $I/work/logs/f4full_{}.log 2>&1; echo done {}"
