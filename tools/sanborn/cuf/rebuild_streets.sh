# full street rebuild after any change to the 1904 frames or the 1922 plates (2026-10-20)
set -e
T="$(cd "$(dirname "$0")/.." && pwd)"; SP="$(cd "$T" && python3 -c 'import _ws; print(_ws.DATA)')"   # T = tools/sanborn (scripts), SP = data/sanborn (was the workspace root): configs/sanborn_paths.json
cd "$SP" && python3 "$T/cuf/undo_sets.py"
cd "$SP/sbg/fit" && SBG_SUFFIX=_v3 SBG_TF_EXTRA=../../lph/tf_all_v3.json python3 "$T/sbg/fit/run_build_safe.py" | tail -2
S=$(python3 -c "print(','.join(str(x) for x in list(range(228,233))+list(range(237,245))+list(range(248,253))+list(range(256,272))+[276,277,278]+list(range(283,287))+[290,291,292]+list(range(296,301))))")
python3 "$T/sbg/fit/add_ext.py" _v3 v3 SV $S --install | grep -v "named streets" | tail -3
cd "$SP" && python3 "$T/cuf/build22.py" --install | grep -v "named streets" | tail -3
python3 "$T/cuf38/build38.py" --install | grep -v "named streets" | tail -4
for n in 66 68 67 69 70 82A 83A 75 76; do python3 "$T/cufp/build.py" $n --install | grep -v "named streets" | tail -3; done   # plates 66-70 (2026-10-21), 82A/83A Norwood (2026-10-23), in cufp/build.py PLATE_ORDER
python3 "$T/millvale/build_mv.py" --install | tail -2
python3 "$T/wh/build_osm.py" --install | tail -1   # OSM primary and secondary streets (2026-10-25); after the other sets, it fills only what they leave
for n in 29 26A 26B 31 33; do python3 "$T/cufp/build.py" $n --install | grep -v "named streets" | tail -3; done   # Price Hill plates (2026-10-25): fill in around the OSM streets
echo REBUILD DONE
