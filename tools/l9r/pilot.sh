#!/bin/bash
# L9R pilot chain on a lent L9 card: wait for the lend (LENT file from lend9.sh START), run <n> borrower lanes over
# <run dir>/jobs.txt, then the pilot summary, then hand the card back (DONE file -> lend9.sh returns it to L9).
# usage: pilot.sh <code dir> <gpu> <run dir> <n lanes> <lent file> <done file>
C=$1; G=$2; R=$3; N=$4; LENT=$5; DONE=$6
E=/data/harvest/out/l9r/events.log
ev() { echo "$(date -u +%FT%TZ) pilot $(basename $R) gpu$G: $*" >> $E; }
ev "waiting for $LENT"
until [ -f "$LENT" ]; do sleep 30; [ -f /data/harvest/out/l9r/STOP ] && { ev "STOP before start"; touch $DONE; exit 0; }; done
bash $C/tools/l9/shm_clean.sh >> $R/pilot.log 2>&1
pids=""
for i in $(seq 1 $N); do
  nohup setsid bash $C/tools/l9r/lane_r.sh $C $G $R r${G}_$i >> $R/lane_r${G}_$i.log 2>&1 < /dev/null &
  pids="$pids $!"; ev "lane r${G}_$i pid $!"; sleep 45
done
watchdog() {  # a job log silent for 15 min = a hung Isaac (smoke 3: 30 min at 260 % CPU, no output): TERM, then KILL
  for i in $(seq 1 $N); do
    f=$(ls -t /data/harvest/logs/l9/r${G}_${i}_*.log 2>/dev/null | head -1)
    [ -n "$f" ] || continue
    tail -1 "$f" | grep -q '^EXIT' && continue
    [ $(( $(date +%s) - $(stat -c %Y "$f") )) -gt 900 ] || continue
    inst=$(basename $f .log); hp=""
    for p in /proc/[0-9]*; do tr '\0' '\n' < $p/environ 2>/dev/null | grep -q "^IR_INST=l9_${inst}$" && hp="$hp ${p#/proc/}"; done
    [ -n "$hp" ] || continue
    kill $hp 2>/dev/null; sleep 30
    for q in $hp; do [ -d /proc/$q ] && kill -9 $q 2>/dev/null; done
    ev "watchdog: $inst silent > 15 min, Isaac stopped (lane goes on)"
  done
}
for p in $pids; do while kill -0 $p 2>/dev/null; do watchdog; sleep 60; done; done
ev "lanes ended: $(ls $R/done | wc -l)/$(wc -l < $R/jobs.txt) jobs done"
/data/harvest/venv_train/bin/python $C/tools/l9r/pilot_summary.py $R /data/harvest/out/l9/prod1/collect > $R/summary.json 2>> $R/pilot.log
ev "summary $(head -c 400 $R/summary.json)"
touch $DONE
ev "card handed back (DONE)"
