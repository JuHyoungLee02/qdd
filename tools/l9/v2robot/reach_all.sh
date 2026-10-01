#!/bin/bash
# Run the remaining reach maps one after another (each waits for the l9v2robot GPU-1 lock). usage: reach_all.sh p:a ...
C=/data/harvest/l9v2robot/code
for pa in "$@"; do
  p=${pa%%:*}; a=${pa##*:}
  until L9V2R_TIMEOUT=5400 bash $C/tools/l9/v2robot/run.sh reach_${p}_${a} $C/tools/l9/v2robot/reach_v2.py $p $a; [ $? -ne 3 ]; do sleep 30; done
done
echo "REACH_ALL_DONE $(date -u +%FT%TZ)" >> /data/harvest/l9v2robot/logs/reach_all.log
