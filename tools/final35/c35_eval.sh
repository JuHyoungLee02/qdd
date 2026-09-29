#!/bin/bash
# E-C35 offline evaluation of one merged 35B model on one GPU (prereg_c35.md): vLLM BF16 (tools/teach_35b/vllm.sh),
# then the requested sets, then stop. Output layout matches ni_judge (<out>/x_<set>_d-min_clean/scores.jsonl, <out>/g).
# sets: full = G + L8-X dev / OOD-H / OOD-O + new OOD-O 58 ; val = L8S validation episodes + open-pool validation rows
# usage: c35_eval.sh <code dir> <gpu> <merged dir> <served name> <port> <out dir> <full|val>
C=$1; G=$2; M=$3; N=$4; PORT=$5; OUT=$6; KIND=$7
L=/data/harvest/logs/c35; D=/data/harvest/out/c35/data; X=/data/harvest/out/dist8/data_x
mkdir -p $L $OUT
until [ -f $M/config.json ]; do sleep 60; done
setsid nohup bash $C/tools/teach_35b/vllm.sh $G $M $N $PORT 0.85 < /dev/null > /dev/null 2>&1 &
for i in $(seq 1 120); do curl -s 127.0.0.1:$PORT/v1/models | grep -q $N && break; sleep 10; done
curl -s 127.0.0.1:$PORT/v1/models | grep -q $N || { echo "EVAL_FAIL $N server $(date -u +%FT%TZ)" >> $L/c35.log;
  bash $C/tools/teach_35b/stop.sh $N; exit 1; }
ev() {  # <data jsonl> <out name>
  [ -f $OUT/$2/scores.jsonl ] && return
  bash $C/tools/teach_35b/py.sh vllm - ev_${N}_$2 $C harvest.teach_pt.evaluate --data $1 --arm pt \
    --url http://127.0.0.1:$PORT --name $N --out $OUT/$2 --kinds control
}
gv() {  # <data jsonl> <out name>
  [ -f $OUT/$2/scores.jsonl ] && return
  bash $C/tools/teach_35b/py.sh vllm - gv_${N}_$2 $C tools/teach_pt/geval.py --data $1 --url http://127.0.0.1:$PORT \
    --name $N --out $OUT/$2
}
if [ "$KIND" = full ]; then
  gv /data/harvest/out/opratio/g_eval.jsonl g
  for s in dev ood_h ood_o; do ev $X/x_${s}_d-min_clean.jsonl x_${s}_d-min_clean; done
  ev $D/x_ood_o58_d-min_clean.jsonl x_ood_o58_d-min_clean
else
  ev $D/x_val_l8s_d-min_clean.jsonl x_val_l8s_d-min_clean
  gv $D/val_open.jsonl g_val_open
fi
bash $C/tools/teach_35b/stop.sh $N >> $L/c35.log 2>&1
echo "EVAL_DONE $N $KIND $(date -u +%FT%TZ)" >> $L/c35.log
