set -e
T="$(cd "$(dirname "$0")/.." && pwd)"; D="$(cd "$T" && python3 -c 'import _ws; print(_ws.DATA)')"   # T = tools/sanborn (scripts), D = data/sanborn (was the workspace root): configs/sanborn_paths.json
cd "$D"
python3 "$T/bathy/b2_grid.py"
python3 "$T/bathy/b7_apply.py"
python3 "$T/bathy/b7s_smooth.py"
python3 "$T/bathy/b11_riffle.py"
python3 "$T/bathy/b7s_smooth.py" export
python3 "$T/bathy/b12_merge.py"
python3 "$T/bathy/b9_lines.py"
cd topo && python3 "$T/topo/rw_maps.py" && cd ..
echo ALL DONE
