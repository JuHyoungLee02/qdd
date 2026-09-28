#!/bin/bash
# Resumable driver of gate_containers (pod): restarts the gate until CONT_DONE; a container whose trials make no
# progress for STALL s (PhysX hang in a narrow triangle-mesh holder) has its Isaac process killed, and the next run
# records it as a failure (current.txt) and goes on. usage: gate_containers_loop.sh CODE_DIR OUT_DIR [STALL]
C=$1; OUT=$2; STALL=${3:-900}
M="tools.l8x_assets.gate_"; M="${M}containers"
L=/data/harvest/logs/l8x_assets
for i in $(seq 1 60); do
  cd "$C" && bash /data/harvest/code_l8x_assets_dev/tools/l8x_assets/isaac.sh "$C" 1 xn_cont3_$i $M \
    --containers /data/harvest/assets_x/containers.json --items /data/harvest/assets_x/task_items.json \
    --objects "$C/harvest/sim/assets_x/objects_real.json" --products /data/harvest/assets_x/products.json \
    --pass-ids /data/harvest/out/teach_l8d/realgate_tally.json --out "$OUT" &
  W=$!
  last=$(date +%s); prev=""
  while kill -0 $W 2>/dev/null; do
    sleep 30
    n=$(grep -cE "^(TRY|CONT )" $L/xn_cont3_$i.log 2>/dev/null)
    if [ "$n" != "$prev" ]; then prev=$n; last=$(date +%s); fi
    lim=$STALL; [ "${n:-0}" = "0" ] && lim=$((STALL + 600))
    if [ $(( $(date +%s) - last )) -gt $lim ]; then
      for p in $(pgrep -f "$M"); do grep -qz "xn_cont3_$i\|$OUT" /proc/$p/environ /proc/$p/cmdline 2>/dev/null && kill -9 $p; done
      pkill -9 -P $W 2>/dev/null; kill -9 $W 2>/dev/null
    fi
  done
  grep -q CONT_DONE $L/xn_cont3_$i.log 2>/dev/null && { echo "LOOP_DONE $i"; break; }
done
