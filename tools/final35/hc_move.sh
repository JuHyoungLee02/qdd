#!/bin/bash
# Final 35B change 3: move the H+C' arm (hc) from x2 (2 cards) to main 7a2a GPU 0-3 (4 cards) once those four are free.
# There are no mid-epoch checkpoints, so the moved arm starts again (the x2 run is kept as run_hc_x2abort).
#   main pod: hc_move.sh main <code dir> <packs...>  -> waits for GPU 0-3 free, flags go, waits for x2 to stop, starts
#             the hc chain on 0-3 (eval / closed loop on free main cards, render 0,1,3)
#   x2 pod:   hc_move.sh x2 <code dir>               -> waits for the go flag, stops its hc chain + training, flags stopped
F=/data/harvest/out/final35; L=/data/harvest/logs/final35
ROLE=$1; C=$2; shift 2
if [ "$ROLE" = main ]; then
  bash $C/tools/final35/free_gpus.sh 0,1,2,3 4 > /dev/null
  touch $F/hc_move.go; echo "HC_MOVE_GO $(date -u +%FT%TZ)" >> $L/chain.log
  until [ -f $F/hc_move.stopped ]; do sleep 30; done
  [ -d $F/run_hc ] && mv $F/run_hc $F/run_hc_x2abort
  exec bash $C/tools/final35/chain.sh $C hc 0,1,2,3 4 0,1,2,3 0,1,2,3 0,1,3 8480 "$@"
else
  until [ -f $F/hc_move.go ]; do sleep 60; done
  bash $C/tools/teach_35b/stop.sh f35chain_hc >> $L/hc_move.log 2>&1
  bash $C/tools/teach_35b/stop.sh run_hc >> $L/hc_move.log 2>&1
  touch $F/hc_move.stopped; echo "HC_MOVE_STOPPED_X2 $(date -u +%FT%TZ)" >> $L/chain.log
fi
