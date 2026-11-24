#!/bin/sh
# review-labels (24 Nov 2026): pseudo labels for 1A and 44 with the final staged make_labels_v2.py, into review-labels/pseudo/ (a test folder, never train_v2/).
# 1A: its batch outputs (picks22_guided/22-1A/outlines.json, unet_data/1A_*). 44: the integrator's baseline run of the merged outline step on the batch grid (base__grid0).
set -e
SP="$(cd "$(dirname "$0")/../../../.." && pwd)"; cd "$SP"
VPY="../../tools/sanborn/unet/.venv/Scripts/python.exe"
ML="bench_2026-11-23/train/staged/tools/sanborn/unet/make_labels_v2.py"
OUT="bench_2026-11-23/train/review-labels/pseudo"
G0="bench_2026-11-23/train/integrate/baseline_ng1/runs_baseline44/base__grid0"
echo "== $(date '+%F %T') make_labels_v2 $(sha256sum "$ML" | cut -c1-16)"
$VPY -B "$ML" pseudo 1A --out "$OUT"
$VPY -B "$ML" pseudo 44 --out "$OUT" --outlines "$G0/outlines.json" --edges "$G0/44_edges.json"
echo "== $(date '+%F %T') done"
