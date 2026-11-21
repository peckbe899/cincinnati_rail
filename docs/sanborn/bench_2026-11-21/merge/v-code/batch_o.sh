#!/bin/bash
# v-code: the staged outline step on a few plates, every output into v-code/runs/oN (venv, -B, review shim)
ME="C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-21/merge/v-code"
VPY="C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/tools/sanborn/unet/.venv/Scripts/python.exe"
SU="C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-21/merge/staged/tools/sanborn/unet"
cd "C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn"
export PYTHONPATH="$ME/shim;C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/tools/sanborn/unet" PYTHONDONTWRITEBYTECODE=1 V_PEAK_FILE="$ME/peak.jsonl"
for n in "$@"; do
  "$VPY" -B "$SU/outlines.py" $n area_ng1 lines_ng1 --out "$ME/runs/o$n" > "$ME/runs/o$n.out" 2> "$ME/runs/o$n.err" &
done
wait
