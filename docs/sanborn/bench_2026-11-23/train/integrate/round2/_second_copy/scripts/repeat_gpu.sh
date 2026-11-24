#!/bin/sh
# Integrator, round 2 (24 Nov 2026): is a training repeatable on the GPU (DirectML) with the same seed? (review-leak 8,
# review-code "untested, needs the GPU"). Each network twice with seed 1 and once with seed 2, 30 iterations, checks
# every 10, on plates 1A (with its validation ground) and 43, staged trainers, into integrate/round2/repeat/. About
# 3-4 minutes of GPU in all. Then repeat_compare.py.   sh repeat_gpu.sh
set -e
SP="$(cd "$(dirname "$0")/../../../../.." && pwd)"; cd "$SP"
VPY="../../tools/sanborn/unet/.venv/Scripts/python.exe"; ST="bench_2026-11-23/train/staged/tools/sanborn/unet"
O="bench_2026-11-23/train/integrate/round2/repeat"; mkdir -p "$O"
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$(cd ../../tools/sanborn && pwd -W);$(cd ../../tools/sanborn/unet && pwd -W)"
for tag in s1a s1b s2; do
  seed=1; [ $tag = s2 ] && seed=2
  $VPY -B -W ignore $ST/unet.py train area_$tag --data train_v2 1A 43 --seed $seed --iters 30 --val-every 10 --out $O > $O/area_$tag.log 2>&1
  $VPY -B -W ignore $ST/edgenet.py train lines_$tag --data train_v2 1A 43 --seed $seed --iters 30 --val-every 10 --out $O > $O/lines_$tag.log 2>&1
  echo "$(date '+%T') $tag done"
done
