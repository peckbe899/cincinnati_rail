#!/bin/sh
# Integrator, round 2 (24 Nov 2026): rebuild data/sanborn/train_v2 with the final staged make_labels_v2.py (the
# networks' venv, -B): the 15 plates of round 1 plus pseudo plate 58. Run from anywhere: sh build_train_v2.sh
set -e
SP="$(cd "$(dirname "$0")/../../../../.." && pwd)"          # data/sanborn
cd "$SP"
VPY="../../tools/sanborn/unet/.venv/Scripts/python.exe"
ML="${ML:-bench_2026-11-23/train/staged/tools/sanborn/unet/make_labels_v2.py}"
MASK="bench_2026-11-23/train/integrate/hand_masks.json"
OUT="${OUT:-train_v2/}"
echo "== $(date '+%F %T') make_labels_v2 $(sha256sum "$ML" | cut -c1-16) -> $OUT"
$VPY -B "$ML" label 43 45 80 82A --out "$OUT"
$VPY -B "$ML" map 1A --val-x 1420 --out "$OUT"
$VPY -B "$ML" pseudo 5 54A 53 7 51 58 66 68 76 79 89 --mask "$MASK" --out "$OUT"
$VPY -B "$ML" verify 43 45 80 82A --out "$OUT" --json bench_2026-11-23/train/integrate/round2/verify_train_v2.json
echo "== $(date '+%F %T') done"
