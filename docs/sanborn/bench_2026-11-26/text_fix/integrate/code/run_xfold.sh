#!/bin/sh
# DEV ONLY: finder4 as shipped but with fix_block_b's cross-fold models (a fold-A plate gets the models fitted on fold B's
# plates and the other way round), on the 12 dev block plates, from stored finder3 masks. Run from data/sanborn.
I=bench_2026-11-26/text_fix/integrate; M=$I/models
{ for N in 3 54A 30 26A 74 49; do echo "$N B"; done; for N in 12 19 64A 60B 93A 48; do echo "$N A"; done; } | \
xargs -P 6 -L 1 sh -c 'N=$0; O=$1; python -B '"$I"'/code/devfinal.py '"$I"'/out/dev/F4x "{\"b_tmpl\": \"'"$M"'/tmpl_real_$O.npz\", \"b_model\": \"'"$M"'/cls_$O.npz\", \"b_num\": \"'"$M"'/num_$O.npz\"}" $N > '"$I"'/work/logs/f4x_$N.log 2>&1; echo done $N'
