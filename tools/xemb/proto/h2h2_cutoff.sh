#!/bin/bash
# fe08 / e9f3 return at 00:30 KST: at 00:25 KST (15:25 UTC) stop every E-H2H-T2 process on this pod and write what is
# left to redo on 7a2a. usage: h2h2_cutoff.sh <pod tag>
TAG=$1
L=/data/harvest/logs/h2h2
K=/data/harvest/out/xemb_proto/scratch/killsh.py
PY=/data/harvest/venv_train/bin/python
while [ "$(date -u +%H%M)" -lt 1525 ]; do
  pgrep -f "h2h2_lane.sh|h2h_run.sh|h2h_eval_l8x.sh" > /dev/null || break  # all done early
  sleep 30
done
for pat in h2h2_lane.sh h2h_run.sh h2h_eval_l8x.sh "h2h_add_cp_s1" "run_add_cp_s1"; do $PY $K "$pat" >> $L/cutoff_$TAG.log 2>&1; done
E=/data/harvest/out/xemb/h2h/eval
{
  echo "CUTOFF $TAG $(date -u +%FT%TZ)"
  for s in dev ood_h xdev_x xood_h xood_hl xood_d xood_s xood_o xood_t; do
    [ -f $E/${s}_add_cp_s1/summary.json ] || echo "REDO add_cp_s1 eval $s (merged model: /data/harvest/out/xemb/h2h/merged_add_cp_s1)"
  done
  [ -f /data/harvest/out/xemb/h2h/merged_add_cp_s1/config.json ] || echo "REDO add_cp_s1 train (1,066 steps, seed 1)"
} >> $L/redo_7a2a.txt
