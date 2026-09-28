#!/bin/bash
# E-STAGE8 chain on juhyoung-q-78dc2 (prereg_stage8.md; run stage8.sh prep first): M_s0 / M_s1 / S_s0 / S_s1 on
# GPU 0-3, then the verdict. usage: stage8_chain.sh <code dir>
C=$1; L=/data/harvest/logs/stage8; mkdir -p $L
bash $C/tools/teach_pt/stage8.sh $C arm M 0 0 8550 > $L/arm_M_s0.log 2>&1 &
bash $C/tools/teach_pt/stage8.sh $C arm M 1 1 8551 > $L/arm_M_s1.log 2>&1 &
bash $C/tools/teach_pt/stage8.sh $C arm S 0 2 8552 > $L/arm_S_s0.log 2>&1 &
bash $C/tools/teach_pt/stage8.sh $C arm S 1 3 8553 > $L/arm_S_s1.log 2>&1 &
wait
bash $C/tools/teach_pt/stage8.sh $C judge
