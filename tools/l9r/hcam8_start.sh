#!/bin/bash
# E-HCAM8 arm start (78dc): train_<arm>.jsonl = E-VIEW8 A0 rows + the arm's L9 rows (combine), steps.txt line, queue
# lines "<arm> <seed>" for seeds 0-3, and the workers on 78dc GPU0-2 (started only when none is running).
# usage: hcam8_start.sh <code dir> <arm H0|H1|H2> <l9 rows jsonl> [--camera-line-base]
C=$1; ARM=$2; L9=$3; CL=$4
O=/data/harvest/out/hcam8; P=/data/harvest/venv_train/bin/python; L=/data/harvest/logs/hcam8
mkdir -p $L
cd $C
PYTHONPATH=$C $P tools/l9r/hcam8_build.py combine /data/harvest/out/view8/train_A0.jsonl $L9 $O/train_$ARM.jsonl $CL \
  --steps-out $O/steps_$ARM.txt > $O/combine_$ARM.json 2>> $L/start.log || { echo "COMBINE_FAIL $ARM" >> $L/hcam8.log; exit 1; }
S=$(cat $O/steps_$ARM.txt)
echo "$ARM $S" >> $O/steps.txt
flock $O/queue.lock bash -c "printf '$ARM 0\n$ARM 1\n$ARM 2\n$ARM 3\n' >> $O/queue.txt"
echo "$(date -u +%FT%TZ) QUEUED $ARM steps=$S $(cat $O/combine_$ARM.json)" >> $L/hcam8.log
for g in 0 1 2; do
  running=0
  for p in /proc/[0-9]*; do
    cmd=$(tr '\0' ' ' < $p/cmdline 2>/dev/null) || continue
    case "$cmd" in *hcam8_worker.sh*" $g "*) running=1;; esac
  done
  [ $running = 1 ] && continue
  nohup setsid bash $C/tools/l9r/hcam8_worker.sh $C $g >> $L/worker_g$g.log 2>&1 < /dev/null &
  sleep 5
done
