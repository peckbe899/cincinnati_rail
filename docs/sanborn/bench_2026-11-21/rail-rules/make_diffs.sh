#!/bin/sh
# Unified diffs of the proposed rail rules against the repo's current files (rail-rules, 21 Nov 2026). NOT applied.
# Run from the repo root (3D):   sh data/sanborn/bench_2026-11-21/rail-rules/make_diffs.sh
# Apply later, if Ben agrees, from the repo root:   git apply data/sanborn/bench_2026-11-21/rail-rules/diffs/rail_rules.diff
R=data/sanborn/bench_2026-11-21/rail-rules; mkdir -p $R/diffs
diff -u --label a/tools/sanborn/unet/ink_bins.py --label b/tools/sanborn/unet/ink_bins.py tools/sanborn/unet/ink_bins.py $R/proposed/ink_bins.py > $R/diffs/ink_bins.diff
diff -u --label a/tools/sanborn/unet/rail_tracks.py --label b/tools/sanborn/unet/rail_tracks.py tools/sanborn/unet/rail_tracks.py $R/proposed/rail_tracks.py > $R/diffs/rail_tracks.diff
cat $R/diffs/ink_bins.diff $R/diffs/rail_tracks.diff > $R/diffs/rail_rules.diff
sha256sum tools/sanborn/unet/ink_bins.py tools/sanborn/unet/rail_tracks.py > $R/diffs/base_sha256.txt
wc -l $R/diffs/*.diff
