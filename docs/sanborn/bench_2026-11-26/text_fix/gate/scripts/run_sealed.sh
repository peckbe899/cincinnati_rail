#!/bin/sh
# Gate runs on the 16 sealed plates (whole plates, from the scan). Run from data/sanborn.
# finder4: the exact frozen command from integrate/FROZEN.txt plus --sealed-ok (final gate only).
# finder3: text_v1/code/finder3.py, defaults (CNN2 model + combiner), --out in the gate folder.
G=bench_2026-11-26/text_fix/gate
mkdir -p $G/out/finder3 $G/out/finder4 $G/logs
printf "41\n46\n88\n92\n52\n58\n63\n56\n84\n76\n71\n38\n66\n9\n6\n35\n" | xargs -P 5 -I{} sh -c "python -B bench_2026-11-26/text_fix/integrate/code/finder4.py {} --out $G/out/finder4 --sealed-ok > $G/logs/f4_{}.log 2>&1; echo f4 done {} \$(date +%T)" &
printf "41\n46\n88\n92\n52\n58\n63\n56\n84\n76\n71\n38\n66\n9\n6\n35\n" | xargs -P 3 -I{} sh -c "python -B bench_2026-11-25/text_v1/code/finder3.py {} --out $G/out/finder3 > $G/logs/f3_{}.log 2>&1; echo f3 done {} \$(date +%T)" &
wait
echo ALL DONE $(date +%T)
