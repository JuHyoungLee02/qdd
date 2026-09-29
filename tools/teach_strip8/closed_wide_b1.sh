#!/bin/bash
# E-STRIP8b wide OOD-H closed loop (0.78 / 0.92 x s0, s1) for b1 S-drop then b1 S-full on one GPU: the S-drop server
# (port 8396, already up) is used first, then stopped and the S-full server started on 8397.
# usage: closed_wide_b1.sh <code dir> <gpu>
C=$1; G=$2
O=/data/harvest/out/strip8/closed
R="bash $C/tools/teach_strip8/isaac.sh $C $G"
run() {  # arm iface port name
  M="harvest.teach_strip8.run_closed --iface $2 --model qwen8b --qwen-url http://127.0.0.1:$3 --qwen-name $4 --arm $1 --seeds 0,1 --out $O"
  T=${1//-/_}
  $R clw_${T}_tz078 $M --table-z 0.78
  $R clw_${T}_tz092 $M --table-z 0.92
}
run b1_s-drop s-min 8396 b1_drop
bash $C/tools/teach_strip8/stop.sh b1_drop
(bash $C/tools/teach_strip8/vllm.sh $G /data/harvest/out/strip8/merged_b1_s-full b1_full 8397 0.30 &)
for i in $(seq 90); do curl -s -m 5 http://127.0.0.1:8397/v1/models | grep -q b1_full && break; sleep 10; done
run b1_s-full v2 8397 b1_full
bash $C/tools/teach_strip8/stop.sh b1_full
echo "CLOSED_WIDE_B1_DONE $(date -u +%FT%TZ)" >> /data/harvest/logs/strip8/lanes.log
