#!/bin/bash
# AgiBot v3 GPU stage over several pods: the task list is split into TOTAL parts (task i -> part i % TOTAL); this pod
# runs parts FIRST..FIRST+NGPU-1, one per GPU (all GPUs with < 1000 MiB used, up to NGPU). Each part restarts itself
# after a crash, marking the episode it died on as done + skipped (so one bad episode never stops a card again).
# Earlier outputs (points/agibot_p*) are prior runs: their done episodes are skipped, their rows count toward the cap.
# STOP_UTC (hhmm, optional): stop this pod's parts then (state is saved as it goes).
# usage: agb_parts.sh TOTAL FIRST NGPU [STOP_UTC]
TOTAL=$1; FIRST=$2; NGPU=$3; STOP=${4:-}
R=/data/harvest/data/agibot
X=/data/harvest/out/xemb_proto
L=/data/harvest/logs/agb_parts_$(hostname).log
cd $X/code
SP=/data/harvest/venv_sam3/lib/python3.12/site-packages:/data/harvest/venv_e3st/lib/python3.12/site-packages
PY=/data/juhyoung_pi05/uvpython/cpython-3.12.13-linux-x86_64-gnu/bin/python3.12
if [ -n "$STOP" ]; then
  ( until [ "$(date -u +%H%M)" -ge $STOP ] && [ "$(date -u +%H)" -le 12 ]; do sleep 30; done
    echo "STOP $(date -u +%FT%TZ)" >> $L; touch /tmp/agb_parts_stop
    for p in $(pgrep -f "xemb.agb_objpts"); do kill $p; done ) &
fi
TASKS=($(ls $R/keep/npz | sort -n))
GPUS=($(nvidia-smi --query-gpu=index,memory.used --format=csv,noheader,nounits | awk -F', ' '$2 < 1000 {print $1}' | head -n $NGPU))
echo "START $(date -u +%FT%TZ) parts $FIRST.. gpus ${GPUS[*]}" >> $L
rm -f /tmp/agb_parts_stop
for k in "${!GPUS[@]}"; do
  part=$((FIRST + k)); g=${GPUS[$k]}
  spec=$(for j in "${!TASKS[@]}"; do [ $((j % TOTAL)) -eq $part ] && echo ${TASKS[$j]}; done | paste -sd, -)
  [ -z "$spec" ] && continue
  O=$X/points/agibot_q$part; mkdir -p $O
  (
    for n in $(seq 1 60); do
      [ -f /tmp/agb_parts_stop ] && break
      AGB_PRIOR_DIRS="$X/points/agibot_p*" TORCH_HOME=/data/harvest/cache/torch CUDA_VISIBLE_DEVICES=$g \
        PYTHONPATH=.:/data/harvest/code_open8_b057c5a:/data/harvest/src/sam3:$SP \
        $PY -m xemb.agb_objpts $R/keep $R/meta $O $spec >> $X/points/agibot_q$part.log 2>&1 && break
      [ -f /tmp/agb_parts_stop ] && break
      c=$(cat $O/current.txt 2>/dev/null)
      [ -n "$c" ] && { echo "$c" >> $O/done.txt; printf '%s\tcrash (restart %s)\n' "$c" "$n" >> $O/skipped.txt; }
      echo "part $part restart $n after crash on $c $(date -u +%FT%TZ)" >> $L
    done
    echo "part $part end $(date -u +%FT%TZ)" >> $L
  ) &
  echo "part $part gpu $g tasks $(echo $spec | tr , ' ' | wc -w)" >> $L
done
wait
