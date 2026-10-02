#!/bin/bash
# E-LIBFT chain (docs/stage3/prereg_libft.md), run on 78dc: 1) data: 40 task lanes of harvest.libft.collect (CPU),
# demos 0-48 (demo_49 = the selection split) 2) rows: tools/libft/build_rows.py 3) base copy 4) train (GPU 0-3,
# yields to /data/harvest/out/vla/GPU_WANTED naming 78dc) 5) merge epoch1 / epoch2. Milestones -> out/libft/events.log.
# usage: chain.sh <code dir>
C=$1; O=/data/harvest/out/libft; L=/data/harvest/logs/libft; mkdir -p $O $L
ev() { echo "$(TZ=Asia/Seoul date '+%F %H:%M') KST | LIBFT | $*" >> $O/events.log; }
ev "chain start code=$C"
# 1) data
source $C/tools/lib0/env_lib.sh $C
for s in libero_spatial libero_object libero_goal libero_10; do for t in 0 1 2 3 4 5 6 7 8 9; do
  LIB0_JOB=libft_$s$t setsid -f bash -c "nice -n 10 $PY -m harvest.libft.collect --suite $s --task $t --out $O/data --max-demos 49 > $L/collect_${s}_$t.log 2>&1" < /dev/null
done; done
sleep 120
while [ $(ps -eo args | grep -c "[h]arvest.libft.collect") -gt 0 ]; do sleep 120; done
ev "data done: $(ls $O/data/*/*/*/row.json | wc -l) demos, $(grep -l '"success": true' $O/data/*/*/*/row.json | wc -l) successful"
# 2) rows
$PY $C/tools/libft/build_rows.py $O/data $O/train_libft.jsonl >> $L/rows.log 2>&1 || { ev "ALERT rows failed"; exit 1; }
ev "rows: $(wc -l < $O/train_libft.jsonl) ($(tail -1 $L/rows.log))"
# 3) base copy (read-only use of main35 merged ep2.5; main35 files untouched)
[ -f $O/base_ep2.5/.copied ] || { cp -r /data/harvest/out/main35/merged_ep2.5 $O/base_ep2.5 && touch $O/base_ep2.5/.copied; }
ev "base copy ready"
# 4) train, yielding to GPU_WANTED
want() { grep -v "LIBFT" /data/harvest/out/vla/GPU_WANTED 2>/dev/null | grep -q "78dc"; }
RES=""
while true; do
  until ! want; do sleep 300; done
  until [ "$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | awk '$1 < 1000' | wc -l)" -ge 4 ]; do sleep 300; done
  ev "train start (78dc 0-3) $RES"
  setsid -f bash $C/tools/teach_35b/train.sh $C 0,1,2,3 $O/train_libft.jsonl $O/libft_run --model $O/base_ep2.5 --epochs 2 \
    --save-half-epoch $RES < /dev/null > /dev/null 2>&1
  sleep 120
  while pgrep -f "[h]arvest.teach_35b.train --data $O/train_libft.jsonl" > /dev/null; do
    if want; then ev "GPU_WANTED names 78dc -> stop training (resume later)"; bash $C/tools/teach_35b/stop.sh libft_run >> $L/stop.log 2>&1; RES=--resume; break; fi
    sleep 120
  done
  grep -q "EXIT 0" /data/harvest/logs/teach_35b/libft_run.log 2>/dev/null && [ -d $O/libft_run/epoch2 ] && break
  [ "$RES" = "--resume" ] && continue
  ev "ALERT training ended without epoch2 (see /data/harvest/logs/teach_35b/libft_run.log)"; exit 1
done
ev "TRAIN_DONE"
# 5) merge
for e in 1 2; do
  [ -d $O/merged_e$e ] || PYTHONPATH=$C /data/harvest/venv_train/bin/python -m harvest.teach_35b.merge --adapter $O/libft_run/epoch$e \
    --out $O/merged_e$e --model $O/base_ep2.5 >> $L/merge.log 2>&1
done
ev "MERGED e1 e2 -> selection on demo_49 next"
touch $O/MERGE_DONE
