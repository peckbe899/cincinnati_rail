#!/bin/sh
# merge/impl: the staged bench44.py (tools/sanborn/unet/bench44.py) with the shim _ws and runs in merge/impl/bench44_runs
I="C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-21/merge/impl"
cd "C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn" || exit 1
PYTHONPATH="$I/shim;C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/tools/sanborn/unet" PYTHONDONTWRITEBYTECODE=1 \
  python -B "$I/../staged/tools/sanborn/unet/bench44.py" --runs "$I/bench44_runs" --python "C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/tools/sanborn/unet/.venv/Scripts/python.exe" "$@"
