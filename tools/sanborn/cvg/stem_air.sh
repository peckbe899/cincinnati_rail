T="$(cd "$(dirname "$0")/.." && pwd)"   # tools/sanborn (scripts); run from data/sanborn (was the workspace root), as before
for Y in "$@"; do
python3 "$T/cvg/stem.py" '["Terminal 2","Terminal 1B","Terminal 4","Terminal 3","Terminal 1A"]' $Y > /dev/null
cp cvg/_stem_$Y.json cvg/gates_params.json
GATES=cvg/_gs_$Y.json AOUT=cvg/_air_$Y.json python3 "$T/cvg/airside2.py" > /dev/null 2>&1
python3 -c "
import json;A=json.load(open('cvg/_air_$Y.json'))['airside'];print($Y,A['stands'],A['by_terminal'],A['by_airline'],A['removed_for_taxilanes'])"
done
cp cvg/gates_params_v66.json cvg/gates_params.json
