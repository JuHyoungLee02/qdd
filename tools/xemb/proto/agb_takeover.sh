#!/bin/bash
# Chain on the pod that keeps running (78dc): when one of its own parts ends, that card takes over the next part of
# the pod that stops (78dc2 at 12:50 KST), once that part's runner there has ended ("part k end" in its log).
# Resume is done-based: the takeover runs in the same output dir agibot_q$k with the same task list, so every episode
# in its done.txt is skipped and its rows_live counts toward the per-task cap. Claims are mkdir locks on /data.
# usage: agb_takeover.sh TOTAL "MINE" "TAKE" OTHER_HOST   e.g. agb_takeover.sh 8 "0 1 2 3" "4 5 6 7" juhyoung-q-78dc2
TOTAL=$1; MINE=($2); TAKE=($3); OTHER=$4
R=/data/harvest/data/agibot
X=/data/harvest/out/xemb_proto
L=/data/harvest/logs/agb_parts_$(hostname).log
LO=/data/harvest/logs/agb_parts_$OTHER.log
cd $X/code
SP=/data/harvest/venv_sam3/lib/python3.12/site-packages:/data/harvest/venv_e3st/lib/python3.12/site-packages
PY=/data/juhyoung_pi05/uvpython/cpython-3.12.13-linux-x86_64-gnu/bin/python3.12
TASKS=($(ls $R/keep/npz | sort -n))
ended() { grep -q "^part $2 end" "$1"; }   # part runners write "part N end" once their loop is over
echo "TAKEOVER-ARMED $(date -u +%FT%TZ) mine ${MINE[*]} take ${TAKE[*]} from $OTHER" >> $L
for m in "${MINE[@]}"; do
  g=$(grep "^part $m gpu " $L | tail -n 1 | awk '{print $4}')
  (
    until ended $L $m; do sleep 60; done
    for k in "${TAKE[@]}"; do
      mkdir $X/points/agibot_q$k.takeover 2>/dev/null || continue
      echo "takeover part $k by card $g (own part $m ended) $(date -u +%FT%TZ); waiting for $OTHER" >> $L
      until ended $LO $k; do sleep 60; done
      sleep 60
      spec=$(for j in "${!TASKS[@]}"; do [ $((j % TOTAL)) -eq $k ] && echo ${TASKS[$j]}; done | paste -sd, -)
      O=$X/points/agibot_q$k
      echo "takeover part $k start gpu $g $(date -u +%FT%TZ) done=$(wc -l < $O/done.txt 2>/dev/null)" >> $L
      for n in $(seq 1 60); do
        AGB_PRIOR_DIRS="$X/points/agibot_p*" TORCH_HOME=/data/harvest/cache/torch CUDA_VISIBLE_DEVICES=$g \
          PYTHONPATH=.:/data/harvest/code_open8_b057c5a:/data/harvest/src/sam3:$SP \
          $PY -m xemb.agb_objpts $R/keep $R/meta $O $spec >> $X/points/agibot_q$k.log 2>&1 && break
        c=$(cat $O/current.txt 2>/dev/null)
        [ -n "$c" ] && { echo "$c" >> $O/done.txt; printf '%s\tcrash (takeover restart %s)\n' "$c" "$n" >> $O/skipped.txt; }
        echo "takeover part $k restart $n after crash on $c $(date -u +%FT%TZ)" >> $L
      done
      echo "takeover part $k end $(date -u +%FT%TZ)" >> $L
    done
  ) &
done
wait
