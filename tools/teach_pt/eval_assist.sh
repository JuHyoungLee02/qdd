#!/bin/bash
# Help a running eval: serve the same merged model on a free GPU and run some L8-X sets into the same eval dir
# (evaluate.py caches replies by id, so the main loop skips what is done here).
# usage: eval_assist.sh <code dir> <merged model> <eval dir> <gpu> <port> <set> [set ...]
C=$1; M=$2; E=$3; G=$4; PORT=$5; shift 5; N=assist_$(basename $M)_g$G
setsid nohup bash $C/tools/teach_pt/vllm.sh $G $M $N $PORT 0.60 < /dev/null > /dev/null 2>&1 &
for i in $(seq 1 90); do curl -s 127.0.0.1:$PORT/v1/models | grep -q $N && break; sleep 10; done
for s in "$@"; do
  bash $C/tools/teach_pt/py.sh vllm - ev_$N_$s $C harvest.teach_pt.evaluate --data /data/harvest/out/dist8/data_x/x_${s}_d-min_clean.jsonl \
    --arm pt --url http://127.0.0.1:$PORT --name $N --out $E/x_${s}_d-min_clean --kinds control
done
bash $C/tools/teach_pt/stop.sh $N
echo "ASSIST_DONE $N $* $(date -u +%FT%TZ)"
