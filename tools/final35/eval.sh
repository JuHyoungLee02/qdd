#!/bin/bash
# Final 35B offline evaluation of one merged arm (prereg_final35.md): serve it with tools/teach_35b/vllm.sh (BF16,
# thinking off), score the L8-X sets (dev_x + OOD-H/HL/D/O/S/T from /data/harvest/out/dist8/data_x) in the track's depth
# modes with the E-DIST8 scorer, stop the server. Same file layout as tools/teach_pt/dist8_eval.sh, so the 8B arms and
# the 35B arms compare with tools/teach_pt/dist8_compare.py.
# usage: eval.sh <code dir> <gpu> <tag> <merged dir> <track d-min|h-min> <port> [mem 0.85]
C=$1; G=$2; TAG=$3; M=$4; T=$5; PORT=$6; U=${7:-0.85}
L=/data/harvest/logs/final35; O=/data/harvest/out/dist8/eval
mkdir -p $L $O
N=f35_${TAG//-/_}
case $T in d-min) ARM=pt; MODES="clean noisy";; h-min) ARM=h; MODES="clean noisy off";; esac
until [ -f $M/config.json ]; do sleep 60; done
setsid nohup bash $C/tools/teach_35b/vllm.sh $G $M $N $PORT $U < /dev/null > /dev/null 2>&1 &
for i in $(seq 1 90); do curl -s 127.0.0.1:$PORT/v1/models | grep -q $N && break; sleep 10; done
if ! curl -s 127.0.0.1:$PORT/v1/models | grep -q $N; then
  echo "EVAL_FAIL $TAG server_not_up $(date -u +%FT%TZ)" >> $L/chain.log
  bash $C/tools/teach_35b/stop.sh $N >> $L/eval.log 2>&1
  exit 1
fi
echo "EVAL_START $TAG $(date -u +%FT%TZ)" >> $L/chain.log
for f in /data/harvest/out/dist8/data_x/x_*_${T}_*.jsonl; do
  b=$(basename $f .jsonl); m=${b##*_}
  case " $MODES " in *" $m "*) ;; *) continue;; esac
  bash $C/tools/teach_35b/py.sh vllm - ev_${N}_$b $C harvest.teach_pt.evaluate --data $f --arm $ARM \
    --url http://127.0.0.1:$PORT --name $N --out $O/${TAG}/$b --kinds control
done
bash $C/tools/teach_35b/stop.sh $N >> $L/eval.log 2>&1
echo "EVAL_DONE $TAG $(date -u +%FT%TZ)" >> $L/chain.log
