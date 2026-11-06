#!/bin/bash
# run I4 for every tile in tiles.json, skipping finished ones; log to tile_run.log
T="$(cd "$(dirname "$0")/.." && pwd)"; D="$(cd "$T" && python3 -c 'import _ws; print(_ws.DATA)')"   # T = tools/sanborn (scripts), D = data/sanborn (was the workspace root): configs/sanborn_paths.json
cd "$D/topo"
for t in $(python3 -c "import json;print(' '.join(sorted(json.load(open('tiles.json')))))"); do
  [ -f iter_${t}_I4.npy ] && continue
  echo "== $t $(date +%H:%M:%S)" >> tile_run.log
  ( python3 "$T/topo/pilot_label2.py" $t && NIT=7 python3 "$T/topo/pilot_surface2.py" $t ) >> tile_$t.log 2>&1 || { echo "  $t: no usable contours, fallback" >> tile_run.log; python3 "$T/topo/tile_fallback.py" $t >> tile_$t.log 2>&1; }
  python3 "$T/topo/tile_masks.py" $t >> tile_$t.log 2>&1 && python3 "$T/topo/pilot_pads.py" $t >> tile_$t.log 2>&1 && \
  python3 "$T/topo/pilot_iter.py" $t I4 30 8 4 mix_m 30 >> tile_$t.log 2>&1
  grep -h "I4:" tile_$t.log | tail -1 >> tile_run.log
  rm -f pilot_${t}_labels.npz
done
echo "ALL DONE $(date +%H:%M:%S)" >> tile_run.log
