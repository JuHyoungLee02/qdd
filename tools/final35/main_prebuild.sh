#!/bin/bash
# Main 35B pre-build (controller 09-30): build the finished L8S production episodes now, in chunks, in parallel, and add
# new episodes as they finish (build.py is single-threaded, ~27 s/episode). Main root only: drawer b3d is out of the
# main 35B (user-log 213); ring V waits for L8D's BUILD_CHECK_C29. The skewed first 481 episodes stay in (stats only).
# Drop rules (dq > 0.04, overexposed, occluded, tipped, failed-episode done rows) are applied by teach_l8d.dataset.
# Every chunk: build.py train pt -> convert_min d-min, done list appended only after both succeed.
# usage: main_prebuild.sh <code dir> [parallel 16] [chunk 30]   stop: touch /data/harvest/out/main35/prebuild/STOP
C=$1; J=${2:-16}; K=${3:-30}
P=/data/harvest/venv_train/bin/python
ROOT=/data/harvest/out/teach_l8d/l8s_prod
O=/data/harvest/out/main35/prebuild; L=$O/log; mkdir -p $O/chunks $L
DONE=$O/built_episodes.txt; touch $DONE
cd $C; export PYTHONPATH=$C OMP_NUM_THREADS=1
log() { echo "$1 $(date -u +%FT%TZ)" >> $L/prebuild.log; }
chunk() {  # <n> <manifest>
  local n=$1 m=$2 d=$O/chunks/c$1
  nice -n 10 $P tools/teach_l8d/build.py $ROOT $d train pt --manifest $m > $d.build.log 2>&1 && \
  nice -n 10 $P tools/teach_pt/convert_min.py $d/train_pt.jsonl $d d-min train_d-min.jsonl > $d.convert.log 2>&1 && \
  [ -s $d/train_d-min.jsonl ] && { grep -o '"[^"]*_s[0-9]*"' $m | tr -d '"' >> $DONE; log "CHUNK_OK c$n"; return 0; }
  log "CHUNK_FAIL c$n"; return 1
}
log "START code $C parallel $J chunk $K"
while [ ! -f $O/STOP ]; do
  # finished episodes (meta.json) not yet built, oldest first
  ls -tr $ROOT/train/*/*/meta.json 2>/dev/null | sed "s#$ROOT/train/##; s#/meta.json##" | grep -vxF -f $DONE > $O/todo.txt
  N=$(wc -l < $O/todo.txt)
  if [ "$N" -lt "$K" ]; then sleep 1800; continue; fi
  nc=$(ls -d $O/chunks/c* 2>/dev/null | grep -c '/c[0-9]*$')
  split -l $K -d -a 5 $O/todo.txt $O/todo_part_
  for f in $O/todo_part_*; do
    [ $(wc -l < $f) -lt $K ] && { rm $f; continue; }  # a short tail waits for the next round
    n=$nc; nc=$((nc + 1))
    printf '{"episodes": [%s]}\n' "$(sed 's/.*/"&"/' $f | paste -sd,)" > $O/chunks/c$n.json
    rm $f
    while [ "$(jobs -rp | wc -l)" -ge $J ]; do sleep 5; done
    chunk $n $O/chunks/c$n.json &
    [ -f $O/STOP ] && break
  done
  wait
  log "ROUND built=$(wc -l < $DONE) todo_left=$(( N - N / K * K ))"
done
wait
log STOPPED
