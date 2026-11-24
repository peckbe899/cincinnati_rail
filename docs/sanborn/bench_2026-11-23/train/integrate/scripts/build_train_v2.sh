#!/bin/sh
# Integrator (23-24 Nov 2026): build data/sanborn/train_v2 with the staged make_labels_v2.py (the networks' venv, -B).
# Run from anywhere:  sh build_train_v2.sh   -> log in integrate/build_train_v2.log
set -e
SP="$(cd "$(dirname "$0")/../../../.." && pwd)"          # data/sanborn
cd "$SP"
VPY="../../tools/sanborn/unet/.venv/Scripts/python.exe"
ML="${ML:-bench_2026-11-23/train/staged/tools/sanborn/unet/make_labels_v2.py}"
MASK="bench_2026-11-23/train/integrate/hand_masks.json"
echo "== $(date '+%F %T') make_labels_v2 $(sha256sum "$ML" | cut -c1-16)"
$VPY -B "$ML" label 43 45 80 82A
$VPY -B "$ML" map 1A --val-x 1420
$VPY -B "$ML" pseudo 5 54A 53 7 51 66 68 76 79 89 --mask "$MASK"
$VPY -B "$ML" verify 43 45 80 82A --json bench_2026-11-23/train/integrate/verify_train_v2.json
echo "== $(date '+%F %T') done"
