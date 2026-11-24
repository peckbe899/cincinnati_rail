#!/bin/sh
# Integrator (24 Nov 2026): bench_2026-11-23/train/staged.diff = the staged tools/sanborn/unet files against the repo's
# HEAD (a/ b/ paths), then a check that it applies to fresh copies (git apply and patch, in a temporary folder) and to
# the repo itself (git apply --check only: nothing in the repo is written). Usage: sh make_diff.sh TMPDIR
set -e
R="$(cd "$(dirname "$0")/../../../../../.." && pwd)"; T="$R/data/sanborn/bench_2026-11-23/train"; W="$1"
[ -n "$W" ] || { echo "usage: make_diff.sh TMPDIR"; exit 2; }
rm -rf "$W/diff" && mkdir -p "$W/diff/a/tools/sanborn/unet" "$W/diff/b/tools/sanborn/unet" && cd "$W/diff"
for f in $(cd "$T/staged/tools/sanborn/unet" && ls *.py); do
  if git -C "$R" cat-file -e "HEAD:tools/sanborn/unet/$f" 2>/dev/null; then git -C "$R" show "HEAD:tools/sanborn/unet/$f" > "a/tools/sanborn/unet/$f"; fi
  cp "$T/staged/tools/sanborn/unet/$f" "b/tools/sanborn/unet/$f"
done
git -c core.autocrlf=false diff --no-index --no-prefix a b > staged.diff || true
sed -i 's#^diff --git b/tools/#diff --git a/tools/#' staged.diff
cp staged.diff "$T/staged.diff"; echo "wrote $T/staged.diff ($(grep -c '' staged.diff) lines, sha256 $(sha256sum staged.diff | cut -c1-16))"
# 1. fresh copies of the repo's files (HEAD), git apply
mkdir -p fresh1/tools/sanborn/unet fresh2/tools/sanborn/unet
for f in $(ls a/tools/sanborn/unet); do cp "a/tools/sanborn/unet/$f" fresh1/tools/sanborn/unet/; cp "a/tools/sanborn/unet/$f" fresh2/tools/sanborn/unet/; done
(cd fresh1 && git -c core.autocrlf=false apply --check -p1 ../staged.diff && git -c core.autocrlf=false apply -p1 ../staged.diff) && echo "git apply on fresh copies: ok"
(cd fresh2 && patch -p1 --dry-run -s < ../staged.diff && patch -p1 -s < ../staged.diff) && echo "patch on fresh copies: ok"
bad=0; for f in $(ls b/tools/sanborn/unet); do cmp "b/tools/sanborn/unet/$f" "fresh1/tools/sanborn/unet/$f" || bad=1; cmp "b/tools/sanborn/unet/$f" "fresh2/tools/sanborn/unet/$f" || bad=1; done
[ $bad = 0 ] && echo "both results equal the staged files byte for byte ($(ls b/tools/sanborn/unet | wc -l) files)" || { echo "MISMATCH after applying"; exit 1; }
# 2. the repo's working tree, check only
git -C "$R" apply --check -p1 "$T/staged.diff" && echo "git apply --check on the repo: ok (not applied)"
