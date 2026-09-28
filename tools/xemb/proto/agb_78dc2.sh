#!/bin/bash
# AgiBot v3 GPU stage on juhyoung-q-78dc2 (4 GPUs until 13:00 KST): waits for free cards (E-STAGE8 ends ~04:00),
# splits the task list over the free cards (one agb_objpts process per card, own out dir, resumable), and a watchdog
# stops everything at 12:50 KST (03:50 UTC) -- rows / done lists are written as they go, so nothing is lost.
# usage: agb_78dc2.sh
R=/data/harvest/data/agibot
X=/data/harvest/out/xemb_proto
L=/data/harvest/logs/agb_78dc2.log
STOP=0350  # UTC hhmm
cd $X/code
SP=/data/harvest/venv_sam3/lib/python3.12/site-packages:/data/harvest/venv_e3st/lib/python3.12/site-packages
PY=/data/juhyoung_pi05/uvpython/cpython-3.12.13-linux-x86_64-gnu/bin/python3.12
( while [ "$(date -u +%H%M)" -lt $STOP ] || [ "$(date -u +%H)" -gt 12 ]; do sleep 30; done
  echo "WATCHDOG stop $(date -u +%FT%TZ)" >> $L
  for p in $(pgrep -f "xemb.agb_objpts"); do kill $p; done ) &
GPUS=""
until [ -n "$GPUS" ]; do
  GPUS=$(nvidia-smi --query-gpu=index,memory.used --format=csv,noheader,nounits | awk -F', ' '$2 < 1000 {print $1}' | paste -sd' ')
  [ -z "$GPUS" ] && sleep 60
  [ "$(date -u +%H%M)" -ge $STOP ] && [ "$(date -u +%H)" -le 12 ] && exit 0
done
N=$(echo $GPUS | wc -w)
TASKS=($(ls $R/keep/npz | sort -n))
echo "START $(date -u +%FT%TZ) gpus [$GPUS] tasks ${#TASKS[@]}" >> $L
i=0
for g in $GPUS; do
  part=$(for j in "${!TASKS[@]}"; do [ $((j % N)) -eq $i ] && echo ${TASKS[$j]}; done | paste -sd, -)
  O=$X/points/agibot_p$i
  mkdir -p $O
  TORCH_HOME=/data/harvest/cache/torch CUDA_VISIBLE_DEVICES=$g PYTHONPATH=.:/data/harvest/code_open8_b057c5a:/data/harvest/src/sam3:$SP \
    nohup $PY -m xemb.agb_objpts $R/keep $R/meta $O $part > $X/points/agibot_p$i.log 2>&1 &
  echo "part $i gpu $g pid $! tasks $(echo $part | tr , ' ' | wc -w)" >> $L
  i=$((i + 1))
done
wait
echo "END $(date -u +%FT%TZ)" >> $L
