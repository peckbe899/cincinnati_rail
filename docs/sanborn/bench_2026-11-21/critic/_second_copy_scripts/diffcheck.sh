#!/bin/sh
# critic: do the proposed diffs apply together? Works on fresh copies of the repo files inside critic/diffcheck/ only.
#   sh diffcheck.sh > diffcheck_result.txt
R="/c/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D"; B="$R/data/sanborn/bench_2026-11-21"; C="$B/critic/diffcheck"
OQ1="$B/outline-quality/diffs/outlines.py.diff"; OQ2="$B/outline-quality/diffs/blocks_noguide.py.diff"
NE="$B/outline-nesting/outline-nesting.diff"; IN="$B/inference/diffs/blocks_noguide.py.diff"
fresh() { rm -rf "$C/$1"; mkdir -p "$C/$1/tools/sanborn/unet"; cp "$R/tools/sanborn/unet/outlines.py" "$R/tools/sanborn/unet/blocks_noguide.py" "$C/$1/tools/sanborn/unet/"; cd "$C/$1"; }
echo "repo files:"; sha256sum "$R/tools/sanborn/unet/outlines.py" "$R/tools/sanborn/unet/blocks_noguide.py" | cut -c1-16
for d in OQ1 OQ2 NE IN; do eval f=\$$d; fresh solo_$d; printf '%s alone: ' $d; patch -p1 --dry-run -s < "$f" && echo ok || echo FAILS; done
fresh oq_then_nest; patch -p1 -s < "$OQ1"; patch -p1 -s < "$OQ2"; printf 'outline-quality then outline-nesting: '; patch -p1 --dry-run < "$NE" | grep 'out of'
fresh nest_then_oq; patch -p1 -s < "$NE"; printf 'outline-nesting then outline-quality outlines.py: '; patch -p1 --dry-run < "$OQ1" | grep 'out of'
fresh nest_then_inf; patch -p1 -s < "$NE"; printf 'outline-nesting then inference blocks_noguide: '; patch -p1 --dry-run < "$IN" | grep FAILED
fresh oq_then_inf; patch -p1 -s < "$OQ2"; printf 'outline-quality then inference blocks_noguide: '; patch -p1 --dry-run < "$IN" | grep FAILED
