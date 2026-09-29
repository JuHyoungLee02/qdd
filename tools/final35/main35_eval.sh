#!/bin/bash
# Main 35B offline evaluation of one merged checkpoint on one GPU (prereg_main35.md): vLLM BF16, then validation
# (L8S held-out episodes + open-point validation rows), G 1,577, L8-X 7 sets (d-min clean), new OOD-O 58. Layout as
# ni_judge expects (<out>/x_<set>_d-min_clean/scores.jsonl, <out>/g). Skips sets already scored.
# usage: main35_eval.sh <code dir> <gpu> <merged dir> <served name> <port> <out dir>
C=$1; G=$2; M=$3; N=$4; PORT=$5; OUT=$6
L=/data/harvest/logs/main35; D=/data/harvest/out/main35/data; X=/data/harvest/out/dist8/data_x
mkdir -p $L $OUT
setsid nohup bash $C/tools/teach_35b/vllm.sh $G $M $N $PORT 0.85 < /dev/null > /dev/null 2>&1 &
for i in $(seq 1 120); do curl -s 127.0.0.1:$PORT/v1/models | grep -q $N && break; sleep 10; done
curl -s 127.0.0.1:$PORT/v1/models | grep -q $N || { echo "EVAL_FAIL $N server $(date -u +%FT%TZ)" >> $L/main35.log;
  bash $C/tools/teach_35b/stop.sh $N; exit 1; }
ev() { [ -f $OUT/$2/scores.jsonl ] || bash $C/tools/teach_35b/py.sh vllm - ev_${N}_$2 $C harvest.teach_pt.evaluate \
  --data $1 --arm pt --url http://127.0.0.1:$PORT --name $N --out $OUT/$2 --kinds control; }
gv() { [ -f $OUT/$2/scores.jsonl ] || bash $C/tools/teach_35b/py.sh vllm - gv_${N}_$2 $C tools/teach_pt/geval.py \
  --data $1 --url http://127.0.0.1:$PORT --name $N --out $OUT/$2; }
ev $D/x_val_l8s_d-min_clean.jsonl x_val_l8s_d-min_clean
gv $D/val_open.jsonl g_val_open
gv /data/harvest/out/opratio/g_eval.jsonl g
for s in dev ood_h ood_d ood_o ood_s ood_t ood_hl; do ev $X/x_${s}_d-min_clean.jsonl x_${s}_d-min_clean; done
ev /data/harvest/out/c35/data/x_ood_o58_d-min_clean.jsonl x_ood_o58_d-min_clean
bash $C/tools/teach_35b/stop.sh $N >> $L/main35.log 2>&1
echo "EVAL_DONE $N $(date -u +%FT%TZ)" >> $L/main35.log
