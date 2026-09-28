#!/bin/bash
# E-VIEW8 chain (prereg_view8.md; run view8.sh prep first): workers on 78dc GPU 2 / 3 now and GPU 0 / 1 after the E-OPRATIO8-S1 chain
# (S1_DONE), then the verdicts. usage: view8_chain.sh <code dir>
C=$1; L=/data/harvest/logs/view8; mkdir -p $L
bash $C/tools/teach_pt/view8.sh $C worker 2 8522 > $L/worker2.log 2>&1 &
bash $C/tools/teach_pt/view8.sh $C worker 3 8523 > $L/worker3.log 2>&1 &
bash $C/tools/teach_pt/view8.sh $C worker 0 8520 /data/harvest/logs/opratio/opratio.log > $L/worker0.log 2>&1 &
bash $C/tools/teach_pt/view8.sh $C worker 1 8521 /data/harvest/logs/opratio/opratio.log > $L/worker1.log 2>&1 &
wait
bash $C/tools/teach_pt/view8.sh $C judge
