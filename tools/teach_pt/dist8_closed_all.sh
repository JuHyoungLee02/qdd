#!/bin/bash
# E-DIST8 closed loop, both B arms on one pod: serve B-D and B-R (vLLM, one GPU, 0.30 each), run dist8_closed.sh for
# each arm on the render GPU, stop the servers. usage: dist8_closed_all.sh <code dir> <serve gpu> <render gpu>
C=$1; SG=$2; RG=$3
L=/data/harvest/logs/dist8
up() { for i in $(seq 1 90); do curl -s 127.0.0.1:$1/v1/models | grep -q $2 && return 0; sleep 10; done; return 1; }
setsid nohup bash $C/tools/teach_pt/vllm.sh $SG /data/harvest/out/dist8/merged_b_d-min d8_b_d_min 8440 0.30 < /dev/null > /dev/null 2>&1 &
up 8440 d8_b_d_min || { echo "CLOSED_FAIL b_d-min server $(date -u +%FT%TZ)" >> $L/dist8_closed.log; exit 1; }
setsid nohup bash $C/tools/teach_pt/vllm.sh $SG /data/harvest/out/strip8/merged_b1_s-min d8_b_r_min 8441 0.30 < /dev/null > /dev/null 2>&1 &
up 8441 d8_b_r_min || { echo "CLOSED_FAIL b_r-min server $(date -u +%FT%TZ)" >> $L/dist8_closed.log; exit 1; }
bash $C/tools/teach_pt/dist8_closed.sh $C $RG b_d-min d-min d8_b_d_min 8440
bash $C/tools/teach_pt/dist8_closed.sh $C $RG b_r-min r-min d8_b_r_min 8441
bash $C/tools/teach_pt/stop.sh d8_b_d_min >> $L/dist8_closed.log 2>&1
bash $C/tools/teach_pt/stop.sh d8_b_r_min >> $L/dist8_closed.log 2>&1
echo "CLOSED_ALL_DONE $(date -u +%FT%TZ)" >> $L/dist8_closed.log
