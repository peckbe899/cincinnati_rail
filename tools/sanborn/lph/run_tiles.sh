T="$(cd "$(dirname "$0")/.." && pwd)"; D="$(cd "$T" && python3 -c 'import _ws; print(_ws.DATA)')"   # T = tools/sanborn (scripts), D = data/sanborn (was the workspace root): configs/sanborn_paths.json
cd "$D/lph" && python3 "$T/lph/tiles_n.py" > tiles_n3.log 2>&1
cd "$D/sbg/fit" && python3 "$T/sbg/fit/tiles.py" > tiles_b.log 2>&1
echo ALLDONE >> "$D/lph/tiles_n3.log"
