#!/bin/sh
# Skeptic (26 Nov 2026): refit the classifier without the 200 rail rows taken from Ben's rail_ben.json, then finder3 on 44 and 5.
# Writes only into text_v1/skeptic. Run from data/sanborn.
set -e
S=bench_2026-11-25/text_v1/skeptic
VPY="C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/tools/sanborn/unet/.venv/Scripts/python.exe"
mkdir -p $S/logs $S/out/v3norail
"$VPY" -B $S/refit/scripts/train.py cnn --train train_norail --out $S/refit/out/model_norail.npz > $S/logs/train_norail.log 2>&1
python -B $S/refit/scripts/stack.py $S/refit/out/model_norail.npz --out $S/refit/out/combiner_norail.npz > $S/logs/stack_norail.log 2>&1
for N in 44 5; do
  python -B bench_2026-11-25/text_v1/code/finder3.py $N --model $S/refit/out/model_norail.npz --combiner $S/refit/out/combiner_norail.npz --out $S/out/v3norail > $S/logs/f3norail_$N.log 2>&1
done
echo done
