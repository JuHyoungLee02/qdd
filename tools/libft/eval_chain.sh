#!/bin/bash
# E-LIBFT evaluation chain on 78dc (prereg_libft.md §3-4), after tools/libft/chain.sh wrote MERGE_DONE:
#  1) serve merged_e1 (GPU0 :8690) and merged_e2 (GPU1 :8691) with vLLM, 2) selection: demo_49 start states, 40 tasks x
#  both checkpoints (harvest.libft.select_run), pick the higher (tie -> e2), 3) the chosen one on the 200 E-LIB0 episodes
#  (arm F, lanes from tools/lib0/lane.sh) and the 140 LIBERO-Plus tasks (arm F), 4) summaries, servers down.
# Yields: if /data/harvest/out/vla/GPU_WANTED names 78dc (not LIBFT), stops between phases and leaves ALERT_yield.
# usage: eval_chain.sh <code dir>
C=$1; O=/data/harvest/out/libft; L=/data/harvest/logs/libft; mkdir -p $L
ev() { echo "$(TZ=Asia/Seoul date '+%F %H:%M') KST | LIBFT | $*" >> $O/events.log; }
want() { grep -v "LIBFT" /data/harvest/out/vla/GPU_WANTED 2>/dev/null | grep -q "78dc"; }
stopall() { for n in libft_e1 libft_e2; do bash $C/tools/teach_35b/stop.sh $n >> $L/stop.log 2>&1; done; }
until [ -f $O/MERGE_DONE ]; do sleep 300; done
ev "eval chain start code=$C"
want && { ev "yield before serving"; touch $O/ALERT_yield; exit 0; }
setsid -f bash $C/tools/teach_35b/vllm.sh 0 $O/merged_e1 libft_e1 8690 0.85 < /dev/null > /dev/null 2>&1
setsid -f bash $C/tools/teach_35b/vllm.sh 1 $O/merged_e2 libft_e2 8691 0.85 < /dev/null > /dev/null 2>&1
for i in $(seq 1 120); do
  curl -s 127.0.0.1:8690/v1/models | grep -q libft_e1 && curl -s 127.0.0.1:8691/v1/models | grep -q libft_e2 && break; sleep 15
done
curl -s 127.0.0.1:8691/v1/models | grep -q libft_e2 || { ev "ALERT servers did not come up"; stopall; exit 1; }
ev "servers up (e1 :8690, e2 :8691)"
# 2) selection
source $C/tools/lib0/env_lib.sh $C
run_sel() {  # arm port name
  for s in libero_spatial libero_object libero_goal libero_10; do for t in 0 1 2 3 4 5 6 7 8 9; do
    while [ $(ps -eo args | grep -c "[h]arvest.libft.select_run") -ge 30 ]; do sleep 20; done
    LIB0_JOB=libftsel_$1 setsid -f bash -c "nice -n 10 $PY -m harvest.libft.select_run --suite $s --task $t --qwen-url http://127.0.0.1:$2 \
      --qwen-name $3 --arm $1 --out $O/select >> $L/select_$1.log 2>&1" < /dev/null
  done; done
}
run_sel E1 8690 libft_e1; run_sel E2 8691 libft_e2
sleep 60; while [ $(ps -eo args | grep -c "[h]arvest.libft.select_run") -gt 0 ]; do sleep 60; done
k1=$(grep -l '"success": true' $O/select/E1/*/*/row.json 2>/dev/null | wc -l)
k2=$(grep -l '"success": true' $O/select/E2/*/*/row.json 2>/dev/null | wc -l)
n1=$(ls $O/select/E1/*/*/row.json 2>/dev/null | wc -l); n2=$(ls $O/select/E2/*/*/row.json 2>/dev/null | wc -l)
if [ $k1 -gt $k2 ]; then CH=1; PORT=8690; else CH=2; PORT=8691; fi
echo "e$CH" > $O/CHOSEN
ev "selection: e1 $k1/$n1, e2 $k2/$n2 -> chosen e$CH"
bash $C/tools/teach_35b/stop.sh libft_e$((3 - CH)) >> $L/stop.log 2>&1
want && { ev "yield after selection"; touch $O/ALERT_yield; stopall; exit 0; }
# 3) evaluation: 200 LIBERO episodes (arm F) then 140 LIBERO-Plus tasks (arm F)
export LIB0_QURL=http://127.0.0.1:$PORT LIB0_QNAME=libft_e$CH
for i in $(seq 1 14); do setsid -f bash $C/tools/lib0/lane.sh $C F lf$i /data/harvest/out/lib0/jobs_all.txt < /dev/null > /dev/null 2>&1; sleep 1; done
sleep 120; while ls /data/harvest/out/lib0/lanes/lf*.alive > /dev/null 2>&1; do sleep 120; done
ev "LIBERO 200: F $(grep -l '"success": true' /data/harvest/out/lib0/F/*/*/row.json | wc -l)/$(ls /data/harvest/out/lib0/F/*/*/row.json | wc -l)"
for i in $(seq 1 14); do LIB0_BENCH=plus LIB0_OUT=/data/harvest/out/libp LIB0_VID=/data/harvest/videos/libp \
  setsid -f bash $C/tools/lib0/lane.sh $C F lpf$i /data/harvest/out/libp/jobs.txt < /dev/null > /dev/null 2>&1; sleep 1; done
sleep 120; while ls /data/harvest/out/libp/lanes/lpf*.alive > /dev/null 2>&1; do sleep 120; done
ev "LIBERO-Plus 140: F $(grep -l '"success": true' /data/harvest/out/libp/F/*/*/row.json | wc -l)/$(ls /data/harvest/out/libp/F/*/*/row.json | wc -l)"
stopall
$PY $C/tools/lib0/summary.py /data/harvest/out/lib0 > $L/summary_lib0.txt 2>&1
LIB0_BENCH=plus $PY $C/tools/lib0/libp_summary.py /data/harvest/out/libp > $L/summary_libp.txt 2>&1
ev "EVAL_DONE (summaries in $L)"
touch $O/EVAL_DONE
