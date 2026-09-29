#!/bin/bash
# E-POOLV8 arm (docs/stage3/prereg_poolv.md): train one pool arm / seed on one GPU (resume if a state exists), merge,
# vLLM on the same GPU, then G (geval.py) and L8-X dev + OOD-O (evaluate.py, d-min). Auto-retries training 3x.
# usage: poolv.sh <code dir> <old|new> <gpu> <port> <seed>
C=$1; ARM=$2; G=$3; PORT=$4; SEED=$5
O=/data/harvest/out/poolv; L=/data/harvest/logs/poolv; mkdir -p $O $L
cd $C; export PYTHONPATH=$C
case $ARM in
  old) D=/data/harvest/out/final35/dryrun2/train_open.jsonl; S=2602;;
  new) D=$O/train_new.jsonl; S=2165;;
  *) echo "arm?"; exit 1;;
esac
A=pv_${ARM}_s$SEED
for n in 1 2 3; do
  RES=""; [ -d $O/run_$A/state ] && RES="--resume"
  bash $C/tools/teach_pt/py.sh train $G train_$A $C harvest.teach_l8.train --data $D --out $O/run_$A \
    --epochs 3 --max-steps $S --micro 8 --accum 2 --log-every 10 --save-every 200 --seed $SEED $RES
  E=$(ls -d $O/run_$A/epoch* 2>/dev/null | sort -V | tail -1)
  [ -n "$E" ] && break
  echo "TRAIN_RETRY $A $n $(date -u +%FT%TZ)" >> $L/poolv.log
done
[ -z "$E" ] && { echo "TRAIN_FAIL $A $(date -u +%FT%TZ)" >> $L/poolv.log; exit 1; }
bash $C/tools/teach_pt/py.sh train $G merge_$A $C harvest.teach_l8.merge --adapter $E --out $O/merged_$A
echo "TRAIN_DONE $A $E $(date -u +%FT%TZ)" >> $L/poolv.log
N=${A}_srv
setsid nohup bash $C/tools/teach_pt/vllm.sh $G $O/merged_$A $N $PORT 0.60 < /dev/null > /dev/null 2>&1 &
for i in $(seq 1 90); do curl -s 127.0.0.1:$PORT/v1/models | grep -q $N && break; sleep 10; done
bash $C/tools/teach_pt/py.sh vllm - geval_$A $C tools/teach_pt/geval.py --data /data/harvest/out/opratio/g_eval.jsonl \
  --url http://127.0.0.1:$PORT --name $N --out $O/eval/$A/g
for b in x_dev_d-min_clean x_ood_o_d-min_clean; do
  bash $C/tools/teach_pt/py.sh vllm - ev_${A}_$b $C harvest.teach_pt.evaluate --data /data/harvest/out/dist8/data_x/$b.jsonl \
    --arm pt --url http://127.0.0.1:$PORT --name $N --out $O/eval/$A/$b --kinds control
done
bash $C/tools/teach_pt/stop.sh $N >> $L/poolv.log 2>&1
echo "EVAL_DONE $A $(date -u +%FT%TZ)" >> $L/poolv.log
