#!/bin/bash
# L8X-assets: iTHOR scenes reference their objects at <scenes root>/objects/thor/<asset>/ (MolmoSpaces install layout).
# Link every unpacked THOR asset variant dir there (objects_thor/usd/thor_<pkg>/<asset>/ -> objects/thor/<asset>).
# Also stops a running rooms_table job (bracket pattern: never matches this script's own command line).
set -euo pipefail
M=/data/harvest/assets_x/molmospaces
pkill -f "tools/l8x_assets/rooms_[t]able.py" || true
mkdir -p $M/scenes_ithor/objects/thor
n=0
for d in "$M"/objects_thor/usd/thor_*/*/; do  # names can hold spaces ("Spatula_1 copy")
  b=$(basename "$d")
  t="$M/scenes_ithor/objects/thor/$b"
  { [ -e "$t" ] || [ -L "$t" ]; } || { ln -s "${d%/}" "$t"; n=$((n+1)); }
done
echo "linked $n"; ls $M/scenes_ithor/objects/thor | wc -l
