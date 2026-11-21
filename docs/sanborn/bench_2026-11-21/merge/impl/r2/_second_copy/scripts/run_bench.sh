#!/bin/sh
# merge/impl/r2: the staged bench44.py (tools/sanborn/unet/bench44.py) with the shim _ws and runs in merge/impl/r2/bench44_runs
R="C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-21/merge/impl/r2"
S="C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-21/merge/impl/shim"
cd "C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn" || exit 1
PYTHONPATH="$S;C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/tools/sanborn/unet" PYTHONDONTWRITEBYTECODE=1 \
  python -B "$R/../../staged/tools/sanborn/unet/bench44.py" --runs "$R/bench44_runs" --python "C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/tools/sanborn/unet/.venv/Scripts/python.exe" "$@"
