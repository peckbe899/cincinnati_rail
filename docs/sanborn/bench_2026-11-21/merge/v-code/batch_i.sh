#!/bin/bash
# v-code: staged ink_bins.py (system python, -B, review shim), outputs only into v-code/runs/<tag>/ via --save/--json
# usage: batch_i.sh TAG N [extra args...]
ME="C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-21/merge/v-code"
SU="C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-21/merge/staged/tools/sanborn/unet"
cd "C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn"
export PYTHONPATH="$ME/shim;C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/tools/sanborn/unet" PYTHONDONTWRITEBYTECODE=1 V_PEAK_FILE="$ME/peak.jsonl"
T=$1; N=$2; shift 2; mkdir -p "$ME/runs/$T"
python -B "$SU/ink_bins.py" $N --save "$ME/runs/$T/${N}_bins.png" --json "$ME/runs/$T/${N}_bins.json" "$@" > "$ME/runs/$T.out" 2> "$ME/runs/$T.err"
