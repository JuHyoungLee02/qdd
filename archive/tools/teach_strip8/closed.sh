#!/bin/bash
# E-STRIP8 closed loop of one arm (prereg_strip8.md §5.5): DEV 4 (standard / dr x s0, s1) and / or OOD-H 4
# (s0, s1 x table 0.82 / 0.88), one Isaac process per variant / height, run one after another on one render GPU.
# usage: closed.sh <code dir> <gpu> <arm> <iface s-min|v2> <port> <served name> [sets "dev oodh"]
C=$1; G=$2; A=$3; I=$4; PORT=$5; N=$6; SETS=${7:-"dev oodh"}
O=/data/harvest/out/strip8/closed
R="bash $C/tools/teach_strip8/isaac.sh $C $G"
M="harvest.teach_strip8.run_closed --iface $I --model qwen8b --qwen-url http://127.0.0.1:$PORT --qwen-name $N --arm $A --seeds 0,1 --out $O"
T=${A//-/_}
for s in $SETS; do
  if [ $s = dev ]; then
    $R cl_${T}_std $M --variant standard
    $R cl_${T}_dr $M --variant dr
  else
    $R cl_${T}_tz082 $M --table-z 0.82
    $R cl_${T}_tz088 $M --table-z 0.88
  fi
done
echo "CLOSED_DONE $A $SETS $(date -u +%FT%TZ)" >> /data/harvest/logs/strip8/lanes.log
