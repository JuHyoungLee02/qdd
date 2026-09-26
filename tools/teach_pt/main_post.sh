#!/bin/bash
# E-PT main-pod chain: after the zero-shot closed loop, stop our zero-shot vLLM (pt_zs) to make room on GPU 2, then
# post_arm for nd-est and nd-pt (served on GPU 2, Isaac on GPU 0). usage: main_post.sh <code dir>
C=$1
L=/data/harvest/logs/teach_pt
until grep -q F0C_DONE $L/lanes.log 2>/dev/null; do sleep 30; done
bash $C/tools/teach_pt/stop.sh pt_zs >> $L/stop_pt_zs.log 2>&1
bash $C/tools/teach_pt/post_arm.sh $C nd-est 2 8398 0
bash $C/tools/teach_pt/post_arm.sh $C nd-pt 2 8399 0
