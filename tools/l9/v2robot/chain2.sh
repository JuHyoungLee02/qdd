#!/bin/bash
# Float-gripper import smokes then the remaining reach maps, one job at a time on the l9v2robot GPU-1 lock.
C=/data/harvest/l9v2robot/code
run() { until L9V2R_TIMEOUT=${TO:-5400} bash $C/tools/l9/v2robot/run.sh "$@"; [ $? -ne 3 ]; do sleep 30; done; }
for g in franka_hand r1pro_right g1_right; do TO=1200 run float_$g $C/tools/l9/v2robot/float_smoke.py $g /data/harvest/l9v2robot/out/float; done
for pa in r1pro:right r1pro:left g1:right g1:left; do run reach_${pa%%:*}_${pa##*:} $C/tools/l9/v2robot/reach_v2.py ${pa%%:*} ${pa##*:}; done
echo "CHAIN2_DONE $(date -u +%FT%TZ)" >> /data/harvest/l9v2robot/logs/chain2.log
