#!/bin/bash
# E-VB1 chain on 78dc (docs/stage3/prereg_vb1.md change 1): conversion (CPU) + pi0.5 training (GPU 0-3).
#  1. after SMOKE_OK (render smoke group g0000): convert it to vb1_smoke + exact stats (CPU, nice 19)
#  2. main35 finished (MAIN35_DONE, or JUDGE_FAIL / EVAL_INCOMPLETE / TRAIN_FAIL in main35.log), E-FUT1 stage 2
#     finished (/data/harvest/out/fut1/summary/summary_fut1.json; main decision 10-01: E-FUT1 takes 78dc first) and
#     all 4 GPUs empty (< 1 GB each): 20-step smoke training on vb1_smoke (failure -> ALERT_train_smoke, stop)
#  3. render finished (eps.py status: left 0): 16 conversion shards in parallel (CPU, nice 19) -> merge -> exact stats
#  4. E-FUT1 finished and 4 GPUs empty -> full training (train.sh, 30k steps, save 5k) -> TRAIN_DONE
# The main35 run is never touched: its files are only read, the chain waits until the GPUs are empty.
# Every milestone -> /data/harvest/out/vb1/events.log.  usage (78dc): nohup bash chain_train.sh <code dir> > /dev/null 2>&1 &
C=$1
Q=/data/harvest; R=$Q/out/vb1; PV=$Q/venv_train/bin/python; PG=/data/GARO_pi/lerobot/.venv/bin/python
L=$Q/logs/vb1; M35=$Q/out/main35; M35L=$Q/logs/main35/main35.log; K=16
mkdir -p $L $R/lerobot
ev() { echo "$(TZ=Asia/Seoul date '+%F %H:%M') KST | VB1 | $*" >> $R/events.log; }
st() { CODE=$C PYTHONPATH=$C $PV -m tools.vb1.eps status; }
free4() { [ "$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | awk '$1 < 1000' | wc -l)" -ge 4 ]; }
m35_over() { [ -f $M35/MAIN35_DONE ] || grep -qE "^(JUDGE_FAIL|EVAL_INCOMPLETE|TRAIN_FAIL)" $M35L 2> /dev/null; }
FUT1=$Q/out/fut1/summary/summary_fut1.json
fut1_over() { [ -f $FUT1 ]; }
conv() { (cd $C && HF_HUB_OFFLINE=1 nice -n 19 $PG tools/vb1/convert.py "$@"); }
# the GARO venv's python is a symlink into /home/irteam/.local/share/uv/python (pod-local): link it to the shared
# interpreter under /data first (= train.sh / Task C recipe pitfall 4), then check that lerobot imports
UV_DIR=/home/irteam/.local/share/uv/python; mkdir -p $UV_DIR
ln -sfn /data/juhyoung_pi05/uvpython/cpython-3.12.13-linux-x86_64-gnu $UV_DIR/cpython-3.12.13-linux-x86_64-gnu
ev "chain_train start code=$C"
$PG -c "import lerobot" 2>> $L/convert_smoke.log || { echo venv > $R/ALERT_convert; ev "ALERT GARO lerobot venv does not start on $(hostname)"; exit 1; }
# 1. smoke conversion
until [ -f $R/SMOKE_OK ] || [ -f $R/SMOKE_FAIL ]; do sleep 300; done
[ -f $R/SMOKE_FAIL ] && { ev "chain_train stops: render smoke failed"; exit 1; }
if [ ! -f $R/lerobot/vb1_smoke/meta/stats_lerobot_backup.json ]; then
  rm -rf $R/lerobot/vb1_smoke $R/lerobot/vb1_smoke.done.txt
  conv smoke >> $L/convert_smoke.log 2>&1 && conv stats vb1_smoke >> $L/convert_smoke.log 2>&1 \
    || { echo convert_smoke > $R/ALERT_convert; ev "ALERT smoke conversion failed ($L/convert_smoke.log)"; exit 1; }
  ev "smoke dataset vb1_smoke ready ($(grep -o 'SHARD_DONE.*' $L/convert_smoke.log | tail -1))"
fi
# 2. smoke training once main35 is over and the cards are empty
until m35_over && fut1_over && free4; do sleep 300; done
ev "main35 over, E-FUT1 stage 2 over and 78dc GPU 0-3 empty -> smoke training"
if ! grep -q "train end .* rc=0" $L/train_smoke.log 2> /dev/null; then
  SMOKE=1 DATASET_ID=vb1_smoke RUN=smoke_vb1 bash $C/tools/vb1/train.sh $C > $L/train_smoke.log 2>&1
  grep -q "train end .* rc=0" $L/train_smoke.log || { echo train_smoke > $R/ALERT_train_smoke; ev "ALERT smoke training failed ($L/train_smoke.log)"; exit 1; }
  ev "smoke training OK ($(grep -oE 'loss[:=] ?[0-9.]+' $L/train_smoke.log | tail -1))"
fi
# 3. full conversion once the render is finished
last=""
while true; do
  s=$(st); left=$(echo "$s" | grep -o '"left": [0-9]*' | grep -o '[0-9]*$')
  [ "$s" != "$last" ] && [ $(( ${left:-1} % 500 )) = 0 ] && ev "render status $s"
  last=$s
  [ "$left" = 0 ] && break
  sleep 900
done
ev "render finished: $s -> conversion ($K shards)"
if [ ! -f $R/lerobot/vb1_l8s_train/meta/stats_lerobot_backup.json ]; then
  for k in $(seq 0 $((K - 1))); do conv shard $k $K > $L/convert_s$k.log 2>&1 & done
  wait
  n=$(grep -l SHARD_DONE $L/convert_s*.log | wc -l)
  [ "$n" = $K ] || { echo "shards $n/$K" > $R/ALERT_convert; ev "ALERT conversion: $n/$K shards"; exit 1; }
  conv merge $K > $L/convert_merge.log 2>&1 && conv stats > $L/convert_stats.log 2>&1 \
    || { echo merge_stats > $R/ALERT_convert; ev "ALERT merge/stats failed"; exit 1; }
  ev "dataset ready: $(grep -o 'MERGE_DONE.*' $L/convert_merge.log)"
fi
# 4. full training
until m35_over && fut1_over && free4; do sleep 300; done
ev "training start (78dc GPU 0-3, 30k steps)"
bash $C/tools/vb1/train.sh $C > $L/train.log 2>&1
if grep -q "train end .* rc=0" $L/train.log; then touch $R/TRAIN_DONE; ev "TRAIN_DONE ($(tail -1 $L/train.log))"
else echo train > $R/ALERT_train; ev "ALERT training failed ($L/train.log)"; fi
