#!/bin/sh
# Skeptic: stack + finder3 for the no-rail-rows model (train step done by run_norail.sh). Uses the classifier's own stack.py
# read-only (the copied one cannot find text_v1/code); every output goes to text_v1/skeptic. Run from data/sanborn.
set -e
S=bench_2026-11-25/text_v1/skeptic
python -B bench_2026-11-25/text_v1/classifier/scripts/stack.py $S/refit/out/model_norail.npz --out $S/refit/out/combiner_norail.npz > $S/logs/stack_norail.log 2>&1
for N in 44 5; do
  python -B bench_2026-11-25/text_v1/code/finder3.py $N --model $S/refit/out/model_norail.npz --combiner $S/refit/out/combiner_norail.npz --out $S/out/v3norail > $S/logs/f3norail_$N.log 2>&1
done
python -B $S/scripts/sk_railrows.py
