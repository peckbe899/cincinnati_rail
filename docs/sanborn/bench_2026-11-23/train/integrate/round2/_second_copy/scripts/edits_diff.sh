#!/bin/sh
# Integrator, round 2 (24 Nov 2026): integrate/round2/integrator_edits_round2.diff = this round's changes to the staged
# files (round 1's staged files are kept in integrate/round2/orig_staged/).   sh edits_diff.sh
T="$(cd "$(dirname "$0")/../../.." && pwd)"; cd "$T"
W=integrate/round2; rm -rf "$W/_ed" && mkdir -p "$W/_ed/a/tools/sanborn/unet" "$W/_ed/b/tools/sanborn/unet"
cp "$W"/orig_staged/*.py "$W/_ed/a/tools/sanborn/unet/"; cp staged/tools/sanborn/unet/*.py "$W/_ed/b/tools/sanborn/unet/"
(cd "$W/_ed" && git -c core.autocrlf=false diff --no-index --no-prefix a b > ../integrator_edits_round2.diff); rm -rf "$W/_ed"
sed -i 's#^diff --git b/tools/#diff --git a/tools/#' "$W/integrator_edits_round2.diff"
echo "wrote $W/integrator_edits_round2.diff ($(grep -c '' "$W/integrator_edits_round2.diff") lines)"
