#!/bin/bash
# L8X-assets: unpack the MolmoSpaces THOR (CC BY 4.0) Isaac USD shard: every tar.zst -> objects_thor/usd/<name>/
# usage: extract_thor.sh [shard dir]   (default /data/harvest/assets_x/molmospaces/objects_thor)
set -euo pipefail
D=${1:-/data/harvest/assets_x/molmospaces/objects_thor}
cd $D
mkdir -p zst usd
tar xf 00000.tar -C zst
n=0
for f in zst/*.tar.zst; do
  b=$(basename $f .tar.zst)
  [ -d usd/$b ] && continue
  mkdir -p usd/$b
  zstd -dc $f | tar xf - -C usd/$b
  n=$((n+1))
done
echo "unpacked $n"; du -sh usd
