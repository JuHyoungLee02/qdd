#!/bin/bash
# E-DIST8 offline evaluation of one merged arm (prereg_dist8.md §2-§4): serve it (vLLM, one GPU), score every
# available set in the track's depth modes (old DEV / OOD-H from data_a, L8-X sets from data_x), stop the server.
# usage: dist8_eval.sh <code dir> <gpu> <tag> <merged dir> <track r-min|d-min|h-min> <port> [mem 0.30]
C=$1; G=$2; TAG=$3; M=$4; T=$5; PORT=$6; U=${7:-0.30}
L=/data/harvest/logs/dist8; O=/data/harvest/out/dist8/eval
mkdir -p $L $O
N=d8_${TAG//-/_}
case $T in r-min) ARM=xyz; MODES="clean";; d-min) ARM=pt; MODES="clean noisy";; h-min) ARM=h; MODES="clean noisy off";; esac
until [ -f $M/config.json ]; do sleep 30; done
setsid nohup bash $C/tools/teach_pt/vllm.sh $G $M $N $PORT $U < /dev/null > /dev/null 2>&1 &
for i in $(seq 1 90); do curl -s 127.0.0.1:$PORT/v1/models | grep -q $N && break; sleep 10; done
echo "EVAL_START $TAG $(date -u +%FT%TZ)" >> $L/dist8_eval.log
for f in /data/harvest/out/dist8/data_a/{dev,ood_h}_${T}_*.jsonl /data/harvest/out/dist8/data_x/x_*_${T}_*.jsonl; do
  [ -f "$f" ] || continue
  b=$(basename $f .jsonl); m=${b##*_}
  case " $MODES " in *" $m "*) ;; *) continue;; esac
  bash $C/tools/teach_pt/py.sh vllm - ev_${N}_$b $C harvest.teach_pt.evaluate --data $f --arm $ARM \
    --url http://127.0.0.1:$PORT --name $N --out $O/${TAG}/$b --kinds control
done
bash $C/tools/teach_pt/stop.sh $N >> $L/dist8_eval.log 2>&1
echo "EVAL_DONE $TAG $(date -u +%FT%TZ)" >> $L/dist8_eval.log
