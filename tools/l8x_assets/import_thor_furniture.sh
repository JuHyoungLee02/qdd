#!/bin/bash
# L8X-assets: static copies + support surfaces of every THOR furniture USD (CC BY 4.0) -> thor_furniture_raw.json
# usage: import_thor_furniture.sh [code dir]
set -euo pipefail
C=${1:-/data/harvest/code_l8x_assets_dev}
A=/data/harvest/assets_x/molmospaces/objects_thor/usd
OUT=/data/harvest/assets_x/thor_furniture_raw.json
source /data/harvest/env.sh
L=$(for d in thor_Countertop thor_Dining_Table thor_Coffee_Table thor_Desk thor_Side_Table_* thor_Shelving_Unit \
             thor_TV_Stand_2 thor_Dresser thor_Cabinet thor_IKEACabinet_1 thor_bin thor_Laundry_Hamper_1 thor_Stool \
             thor_Footstool thor_Ottoman_2 thor_Sink thor_Cart_1; do
      for v in $A/$d/*/; do b=$(basename $v); case $b in *_mesh|*_prim) continue;; esac
        [ -f $v/$b.usda ] && echo $v/$b.usda; done; done)
echo "$(echo "$L" | wc -l) assets"
cd $C
PYTHONPATH=/data/harvest/assets_x/pylib:/data/harvest/pylib:$C python3 -m harvest.sim.assets_x.usd_import $L --out $OUT
