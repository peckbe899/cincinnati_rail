#!/bin/sh
# run blockfix on whole plates, 4 at a time. Usage (from data/sanborn): sh .../code/run_plates.sh IN_DIR OUT_DIR N1 N2 ...
F=bench_2026-11-26/text_fix/fix_block_a; IN=$1; OUT=$2; shift 2; mkdir -p $OUT
printf '%s\n' "$@" | xargs -P 4 -I{} sh -c "python -B $F/code/blockfix.py {} --in $IN --out $OUT > $OUT/{}.log 2>&1"
cat $OUT/*.log
